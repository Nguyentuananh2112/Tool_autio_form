"""Chuyển giá trị một ô Excel/CSV thành `Answer` hợp lệ cho từng loại câu hỏi Google Form."""

from __future__ import annotations

import math
import re
import unicodedata
from dataclasses import dataclass
from datetime import date, datetime, time
from typing import Any

import pandas as pd

from app.schemas.form_schema import OTHER_OPTION_VALUE, ParsedOption, ParsedQuestion, QuestionType
from app.services.spss_generator import (
    ANSWER_KIND_DATE,
    ANSWER_KIND_TEXT,
    ANSWER_KIND_TIME,
    Answer,
    scale_values_for,
)

SEPARATOR_PATTERN = re.compile(r"^[\s,;|/\n]+|[\s,;|/\n]+$")
TIME_PATTERN = re.compile(r"^(\d{1,2})[:hH.](\d{2})")


class CoercionError(ValueError):
    pass


@dataclass(slots=True)
class Coerced:
    answer: Answer | None
    warning: str | None = None


def is_blank(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, float) and math.isnan(value):
        return True
    return isinstance(value, str) and not value.strip()


def cell_to_text(value: Any) -> str:
    """4.0 → "4", giữ nguyên chuỗi; dùng cho cả lưu JSON lẫn so khớp."""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    if isinstance(value, (datetime, pd.Timestamp)):
        return value.isoformat()
    return str(value).strip()


def normalize(text: str, *, strip_accents: bool = False) -> str:
    cleaned = unicodedata.normalize("NFC", text).casefold()
    if strip_accents:
        cleaned = "".join(
            char for char in unicodedata.normalize("NFD", cleaned) if unicodedata.category(char) != "Mn"
        ).replace("đ", "d")
    return " ".join(cleaned.split()).rstrip(" .")


def _numeric_code(question: ParsedQuestion, raw: str) -> ParsedOption | None:
    """Dữ liệu đã mã hóa SPSS: "3" → lựa chọn thứ 3 (hoặc giá trị thật của thang đo)."""
    if not re.fullmatch(r"-?\d+", raw):
        return None
    number = int(raw)
    options = question.choice_options
    values = scale_values_for(question)
    if number in values:
        return options[values.index(number)]
    return None


def match_option(question: ParsedQuestion, raw: str) -> ParsedOption | None:
    options = question.choice_options
    for option in options:
        if option.value == raw:
            return option
    for strip_accents in (False, True):
        target = normalize(raw, strip_accents=strip_accents)
        for option in options:
            if normalize(option.value, strip_accents=strip_accents) == target:
                return option
    return _numeric_code(question, raw)


def _other_option(question: ParsedQuestion) -> ParsedOption | None:
    return next((option for option in question.options if option.is_other), None)


def _numeric_value(question: ParsedQuestion, option: ParsedOption) -> float | None:
    options = question.choice_options
    if option.is_other:
        return float(len(options) + 1)
    values = scale_values_for(question)
    return float(values[options.index(option)]) if option in options else None


def _coerce_single(question: ParsedQuestion, raw: str) -> Coerced:
    option = match_option(question, raw)
    if option is not None:
        return Coerced(Answer(values=[option.value], numeric_value=_numeric_value(question, option)))
    other = _other_option(question)
    if other is not None:
        return Coerced(
            Answer(values=[OTHER_OPTION_VALUE], other_text=raw, numeric_value=_numeric_value(question, other)),
            warning=f"“{raw}” không có trong danh sách → điền vào Mục khác.",
        )
    raise CoercionError(f"“{raw}” không khớp lựa chọn nào của câu này.")


def _coerce_multi(question: ParsedQuestion, raw: str) -> Coerced:
    """Tách ô kiểu "Giá cả, khuyến mãi; Đa dạng sản phẩm" bằng cách dò lựa chọn dài nhất trước
    (vì bản thân lựa chọn có thể chứa dấu phẩy), phần dư → Mục khác."""
    # Làm việc trên chuỗi gốc (chỉ chuẩn hoá Unicode & khoảng trắng) để phần dư cho "Mục khác"
    # giữ nguyên chữ hoa người dùng đã gõ; so khớp lựa chọn không phân biệt hoa thường (BUG-010)
    remaining = " ".join(unicodedata.normalize("NFC", raw).split())
    chosen: list[ParsedOption] = []
    for option in sorted(question.choice_options, key=lambda o: len(o.value), reverse=True):
        words = unicodedata.normalize("NFC", option.value).rstrip(" .").split()
        if not words:
            continue
        pattern = re.compile(r"\s+".join(re.escape(word) for word in words) + r"\.?", re.IGNORECASE)
        remaining, found = pattern.subn(" ", remaining, count=1)
        if found:
            chosen.append(option)

    leftover_tokens = [token for token in re.split(r"[,;|/\n]", remaining) if token.strip()]
    for token in list(leftover_tokens):
        option = _numeric_code(question, token.strip())
        if option is not None:
            # Mã số trùng lựa chọn đã nhận theo tên ("Giao hàng, 3") chỉ bỏ đi, không thành phần dư
            if option not in chosen:
                chosen.append(option)
            leftover_tokens.remove(token)

    leftover = SEPARATOR_PATTERN.sub("", ", ".join(token.strip() for token in leftover_tokens))
    warning = None
    other_text = None
    if leftover:
        if _other_option(question) is None:
            raise CoercionError(f"Phần “{leftover}” không khớp lựa chọn nào của câu này.")
        other_text = leftover
        warning = f"“{leftover}” → điền vào Mục khác."

    order = {option.value: index for index, option in enumerate(question.options)}
    values = sorted({option.value for option in chosen}, key=order.__getitem__)
    if other_text is not None:
        values.append(OTHER_OPTION_VALUE)
    if not values:
        return Coerced(None)
    return Coerced(Answer(values=values, other_text=other_text), warning=warning)


_ISO_DATE = re.compile(r"^\d{4}-\d{1,2}-\d{1,2}")


def _coerce_date(value: Any) -> Coerced:
    if isinstance(value, (datetime, pd.Timestamp)):
        parsed: date = value.date()
    elif isinstance(value, date):
        parsed = value
    else:
        text = str(value).strip()
        try:
            # yyyy-mm-dd (ISO) không có nghĩa "ngày trước tháng"; các dạng khác ưu tiên dd/mm
            parsed = pd.to_datetime(text, dayfirst=not _ISO_DATE.match(text)).date()
        except (ValueError, OverflowError) as exc:
            raise CoercionError(f"“{value}” không phải ngày hợp lệ (dùng dạng dd/mm/yyyy).") from exc
    return Coerced(Answer(values=[parsed.isoformat()], kind=ANSWER_KIND_DATE))


def _coerce_time(value: Any) -> Coerced:
    if isinstance(value, (datetime, pd.Timestamp)):
        value = value.time()
    if isinstance(value, time):
        return Coerced(Answer(values=[f"{value.hour:02d}:{value.minute:02d}"], kind=ANSWER_KIND_TIME))
    match = TIME_PATTERN.match(str(value).strip())
    if not match or int(match.group(1)) > 23 or int(match.group(2)) > 59:
        raise CoercionError(f"“{value}” không phải giờ hợp lệ (dùng dạng HH:MM).")
    return Coerced(Answer(values=[f"{int(match.group(1)):02d}:{match.group(2)}"], kind=ANSWER_KIND_TIME))


def coerce_cell(question: ParsedQuestion, value: Any) -> Coerced:
    if is_blank(value):
        return Coerced(None)
    if question.type_id == QuestionType.DATE:
        return _coerce_date(value)
    if question.type_id == QuestionType.TIME:
        return _coerce_time(value)
    raw = cell_to_text(value)
    if question.is_text:
        return Coerced(Answer(values=[raw], kind=ANSWER_KIND_TEXT))
    if question.is_multi_select:
        return _coerce_multi(question, raw)
    return _coerce_single(question, raw)
