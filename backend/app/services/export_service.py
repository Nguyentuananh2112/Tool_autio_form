"""Xuất dữ liệu đã gửi (`submission_logs.payload_sent`) ra CSV / Excel để đối chiếu trên SPSS.

Excel có 2 trang: "Dữ liệu" (chữ như đã gửi) và "SPSS (mã số)" (thang đo/trắc nghiệm → số,
Checkbox → các biến 0/1).
"""

from __future__ import annotations

import io
from datetime import UTC, datetime
from collections.abc import Sequence
from typing import Any

import pandas as pd

from app.models import SubmissionLog
from app.schemas.form_schema import OTHER_OPTION_VALUE, ParsedFormStructure, ParsedQuestion, QuestionType
from app.services.spss_generator import numeric_codes

META_COLUMNS = ("STT", "Thời điểm gửi", "Thành công", "Công cụ", "Mã HTTP", "Đường đi", "Lỗi")


def _values(payload: dict[str, Any], key: str) -> list[str]:
    raw = payload.get(key)
    if raw is None:
        return []
    return [str(v) for v in raw] if isinstance(raw, list) else [str(raw)]


def _text_value(question: ParsedQuestion, payload: dict[str, Any]) -> str | None:
    key = f"entry.{question.entry_id}"
    if question.type_id == QuestionType.DATE:
        parts = [_values(payload, f"{key}_{p}") for p in ("year", "month", "day")]
        return "-".join(p[0].zfill(2) for p in parts) if all(parts) else None
    if question.type_id == QuestionType.TIME:
        hour, minute = _values(payload, f"{key}_hour"), _values(payload, f"{key}_minute")
        return f"{hour[0]}:{minute[0]}" if hour and minute else None
    values = _values(payload, key)
    if not values:
        return None
    other = _values(payload, f"{key}.other_option_response")
    rendered = [f"Khác: {other[0]}" if v == OTHER_OPTION_VALUE and other else v for v in values]
    return "; ".join(rendered)


def _unique_titles(structure: ParsedFormStructure) -> dict[str, str]:
    names: dict[str, str] = {}
    used: set[str] = set()
    for question in structure.questions:
        name = question.title if question.title not in used else f"{question.title} ({question.entry_id})"
        used.add(name)
        names[question.entry_id] = name
    return names


def _local_time(value: datetime | None) -> str | None:
    if value is None:
        return None
    aware = value.replace(tzinfo=UTC) if value.tzinfo is None else value
    return aware.astimezone().strftime("%Y-%m-%d %H:%M:%S")


def _meta(log: SubmissionLog, payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "STT": log.sequence_number,
        "Thời điểm gửi": _local_time(log.executed_at),
        "Thành công": "Có" if log.is_success else "Không",
        "Công cụ": log.engine_used,
        "Mã HTTP": log.status_code,
        "Đường đi": payload.get("pageHistory"),
        "Lỗi": log.error_detail,
    }


def build_text_frame(structure: ParsedFormStructure, logs: Sequence[SubmissionLog]) -> pd.DataFrame:
    titles = _unique_titles(structure)
    rows = []
    for log in logs:
        row = _meta(log, log.payload_sent)
        for question in structure.questions:
            row[titles[question.entry_id]] = _text_value(question, log.payload_sent)
        rows.append(row)
    return pd.DataFrame(rows, columns=[*META_COLUMNS, *titles.values()])


def build_numeric_frame(structure: ParsedFormStructure, logs: Sequence[SubmissionLog]) -> pd.DataFrame:
    titles = _unique_titles(structure)
    rows = []
    for log in logs:
        if not log.is_success:
            continue
        payload = log.payload_sent
        row: dict[str, Any] = {"STT": log.sequence_number}
        for question in structure.questions:
            values = _values(payload, f"entry.{question.entry_id}")
            title = titles[question.entry_id]
            if question.is_multi_select:
                for option in question.options:
                    row[f"{title} [{option.label}]"] = (1 if option.value in values else 0) if values else None
            elif question.options:
                row[title] = numeric_codes(question).get(values[0]) if values else None
            else:
                row[title] = _text_value(question, payload)
        rows.append(row)
    return pd.DataFrame(rows)


def to_csv_bytes(frame: pd.DataFrame) -> bytes:
    # utf-8-sig để Excel trên Windows hiển thị đúng tiếng Việt
    return frame.to_csv(index=False).encode("utf-8-sig")


def to_xlsx_bytes(text_frame: pd.DataFrame, numeric_frame: pd.DataFrame) -> bytes:
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        text_frame.to_excel(writer, sheet_name="Dữ liệu", index=False)
        numeric_frame.to_excel(writer, sheet_name="SPSS (mã số)", index=False)
    return buffer.getvalue()
