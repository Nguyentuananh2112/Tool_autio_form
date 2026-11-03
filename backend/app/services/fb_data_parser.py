"""Giải mã mảng `FB_PUBLIC_LOAD_DATA_` thành ParsedFormStructure (Mục 5.1.B–D spec)."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from app.schemas.form_schema import (
    OTHER_OPTION_VALUE,
    PAGE_BREAK_TYPE_ID,
    QUESTION_TYPE_NAMES,
    NavigationAction,
    ParsedFormStructure,
    ParsedOption,
    ParsedQuestion,
    ParsedSection,
    QuestionType,
    decode_jump,
)
from app.services.form_errors import FormRequiresLoginError, FormStructureError

logger = logging.getLogger(__name__)

FB_PUBLIC_LOAD_DATA_PATTERN = re.compile(
    r"var\s+FB_PUBLIC_LOAD_DATA_\s*=\s*(\[.*?\]);\s*</script>", re.DOTALL
)
FB_PUBLIC_LOAD_DATA_MARKER = re.compile(r"FB_PUBLIC_LOAD_DATA_\s*=\s*")
FBZX_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r'<input[^>]*name="fbzx"[^>]*value="([^"]*)"', re.IGNORECASE),
    re.compile(r'<input[^>]*value="([^"]*)"[^>]*name="fbzx"', re.IGNORECASE),
)

SIMPLE_QUESTION_TYPES: frozenset[int] = frozenset(
    {
        QuestionType.SHORT_ANSWER,
        QuestionType.PARAGRAPH,
        QuestionType.MULTIPLE_CHOICE,
        QuestionType.DROPDOWN,
        QuestionType.CHECKBOX,
        QuestionType.LINEAR_SCALE,
        QuestionType.DATE,
        QuestionType.TIME,
    }
)



def _safe_get(container: Any, *indices: int, default: Any = None) -> Any:
    """Truy cập lồng nhau an toàn vào mảng JSON: _safe_get(raw, 1, 8)."""
    current = container
    for index in indices:
        if not isinstance(current, list) or index >= len(current) or index < -len(current):
            return default
        current = current[index]
    return default if current is None else current


def _clean_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _as_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str) and re.fullmatch(r"-?\d+", value.strip()):
        return int(value.strip())
    return None



def _raw_decode_after_marker(html: str) -> Any:
    """Giải mã JSON trực tiếp từ vị trí '[' sau dấu '=' (an toàn với chuỗi chứa "];</script>")."""
    marker = FB_PUBLIC_LOAD_DATA_MARKER.search(html)
    if not marker:
        if "accounts.google.com" in html and "ServiceLogin" in html:
            raise FormRequiresLoginError("Biểu mẫu yêu cầu đăng nhập Google.")
        raise FormStructureError(
            "Không tìm thấy FB_PUBLIC_LOAD_DATA_ trong trang. Link có thể không phải form công khai."
        )
    start = html.find("[", marker.end())
    if start == -1:
        raise FormStructureError("FB_PUBLIC_LOAD_DATA_ không chứa mảng JSON hợp lệ.")
    data, _ = json.JSONDecoder().raw_decode(html, start)
    return data


def extract_fb_public_load_data(html: str) -> list[Any]:
    match = FB_PUBLIC_LOAD_DATA_PATTERN.search(html)
    data: Any
    try:
        if match:
            try:
                data = json.loads(match.group(1))
            except json.JSONDecodeError:
                # Regex không tham lam có thể cắt giữa chuỗi chứa "];</script>" → thử giải mã trực tiếp
                data = _raw_decode_after_marker(html)
        else:
            data = _raw_decode_after_marker(html)
    except json.JSONDecodeError as exc:
        raise FormStructureError(f"Không thể giải mã FB_PUBLIC_LOAD_DATA_: {exc}") from exc

    if not isinstance(data, list) or len(data) < 2 or not isinstance(data[1], list):
        raise FormStructureError("Cấu trúc FB_PUBLIC_LOAD_DATA_ không đúng định dạng mong đợi.")
    return data


def extract_fbzx(html: str, raw_data: list[Any] | None = None) -> str | None:
    for pattern in FBZX_PATTERNS:
        match = pattern.search(html)
        if match and match.group(1):
            return match.group(1)
    if raw_data is not None:
        token = _safe_get(raw_data, 14)
        if isinstance(token, (str, int)) and str(token).strip():
            return str(token).strip()
    return None


def _parse_options(raw_options: Any, allow_jump: bool) -> list[ParsedOption]:
    options: list[ParsedOption] = []
    if not isinstance(raw_options, list):
        return options
    for opt in raw_options:
        if not isinstance(opt, list) or not opt:
            continue
        raw_value = opt[0]
        value = "" if raw_value is None else str(raw_value)
        is_other = value == "" and _safe_get(opt, 4) == 1
        jump = _as_int(_safe_get(opt, 2)) if allow_jump else None
        if is_other:
            options.append(
                ParsedOption(label="Mục khác", value=OTHER_OPTION_VALUE, is_other=True, jump_to_section_id=jump)
            )
        elif value.strip():
            options.append(ParsedOption(label=value, value=value, is_other=False, jump_to_section_id=jump))
    return options


def _parse_simple_question(
    item: list[Any], item_id: int, title: str, description: str | None, type_id: int, page_index: int
) -> ParsedQuestion | None:
    meta = _safe_get(item, 4, 0)
    if not isinstance(meta, list) or not meta or meta[0] is None:
        logger.warning("Bỏ qua câu hỏi '%s' (item_id=%s): thiếu entry_id", title, item_id)
        return None

    options = _parse_options(
        _safe_get(meta, 1), allow_jump=type_id in (QuestionType.MULTIPLE_CHOICE, QuestionType.DROPDOWN)
    )
    scale_low = scale_high = None
    if type_id == QuestionType.LINEAR_SCALE:
        labels = _safe_get(meta, 3, default=[])
        scale_low = _clean_text(_safe_get(labels, 0))
        scale_high = _clean_text(_safe_get(labels, 1))
        if not options:
            logger.warning("Thang đo '%s' không có mức nào, bỏ qua", title)
            return None
    if type_id in (QuestionType.MULTIPLE_CHOICE, QuestionType.DROPDOWN, QuestionType.CHECKBOX) and not options:
        logger.warning("Câu trắc nghiệm '%s' không có lựa chọn, bỏ qua", title)
        return None

    return ParsedQuestion(
        item_id=item_id,
        entry_id=str(meta[0]),
        title=title,
        description=description,
        type_id=type_id,
        type_name=QUESTION_TYPE_NAMES[type_id],
        page_index=page_index,
        is_required=bool(_safe_get(meta, 2, default=0)),
        options=options,
        scale_low_label=scale_low,
        scale_high_label=scale_high,
        is_multi_select=type_id == QuestionType.CHECKBOX,
    )


def _parse_grid_rows(
    item: list[Any], item_id: int, title: str, description: str | None, page_index: int
) -> list[ParsedQuestion]:
    rows = _safe_get(item, 4, default=[])
    questions: list[ParsedQuestion] = []
    if not isinstance(rows, list):
        return questions
    for row_index, row in enumerate(rows):
        if not isinstance(row, list) or not row or row[0] is None:
            continue
        columns = _parse_options(_safe_get(row, 1), allow_jump=False)
        if not columns:
            continue
        row_label = _clean_text(_safe_get(row, 3, 0)) or f"Hàng {row_index + 1}"
        # row[11] == [1] đánh dấu Checkbox Grid
        is_checkbox_grid = _safe_get(row, 11, 0) == 1
        questions.append(
            ParsedQuestion(
                item_id=item_id,
                entry_id=str(row[0]),
                title=f"{title} [{row_label}]",
                description=description,
                type_id=QuestionType.GRID,
                type_name="CHECKBOX_GRID" if is_checkbox_grid else QUESTION_TYPE_NAMES[QuestionType.GRID],
                page_index=page_index,
                is_required=bool(_safe_get(row, 2, default=0)),
                options=columns,
                grid_item_id=item_id,
                grid_title=title,
                row_label=row_label,
                is_multi_select=is_checkbox_grid,
            )
        )
    return questions


def parse_fb_public_load_data(
    raw_data: list[Any], *, view_url: str, submit_url: str, fbzx: str | None
) -> ParsedFormStructure:
    form_info = raw_data[1]
    title = (
        _clean_text(_safe_get(form_info, 8))
        or _clean_text(_safe_get(raw_data, 3))
        or "Biểu mẫu không có tiêu đề"
    )
    form_description = _clean_text(_safe_get(form_info, 0))
    items = _safe_get(form_info, 1, default=[])
    if not isinstance(items, list):
        raise FormStructureError("Danh sách câu hỏi (raw_data[1][1]) không hợp lệ.")

    page_index = 0
    sections: list[ParsedSection] = [
        ParsedSection(page_index=0, section_item_id=None, title=title, description=form_description)
    ]
    questions: list[ParsedQuestion] = []

    for item in items:
        if not isinstance(item, list) or len(item) < 4:
            continue
        item_id = _as_int(item[0])
        type_id = _as_int(item[3])
        if item_id is None or type_id is None:
            continue
        item_title = _clean_text(item[1]) or ""
        item_description = _clean_text(_safe_get(item, 2))

        if type_id == PAGE_BREAK_TYPE_ID:
            # item[5] của Page Break là điều hướng "Sau phần trước, chuyển tới..." của trang ĐỨNG TRƯỚC nó
            nav_code = _as_int(_safe_get(item, 5))
            if nav_code is not None:
                action, target = decode_jump(nav_code)
                previous = sections[-1]
                previous.navigation_action = action
                previous.jump_to_section_id = target
            page_index += 1
            sections.append(
                ParsedSection(
                    page_index=page_index,
                    section_item_id=item_id,
                    title=item_title or f"Trang {page_index + 1}",
                    description=item_description,
                    navigation_action=NavigationAction.NEXT_PAGE,
                )
            )
            continue

        if type_id == QuestionType.GRID:
            questions.extend(
                _parse_grid_rows(item, item_id, item_title or "Câu hỏi lưới", item_description, page_index)
            )
        elif type_id in SIMPLE_QUESTION_TYPES:
            question = _parse_simple_question(
                item, item_id, item_title or f"Câu hỏi {item_id}", item_description, type_id, page_index
            )
            if question is not None:
                questions.append(question)
        else:
            # 6 = Tiêu đề/mô tả, 11 = Hình ảnh, 12 = Video... không cần điền
            logger.debug("Bỏ qua phần tử tĩnh type_id=%s item_id=%s", type_id, item_id)

    known_sections = {s.section_item_id for s in sections if s.section_item_id is not None}
    for question in questions:
        for option in question.options:
            jump = option.jump_to_section_id
            if jump is not None and jump > 0 and jump not in known_sections:
                logger.warning(
                    "Lựa chọn '%s' của câu '%s' trỏ tới section %s không tồn tại",
                    option.label, question.title, jump,
                )

    return ParsedFormStructure(
        title=title,
        description=form_description,
        view_url=view_url,
        submit_url=submit_url,
        fbzx=fbzx,
        total_pages=page_index + 1,
        sections=sections,
        questions=questions,
    )
