"""Ghép cột Excel/CSV với câu hỏi Google Form và chuyển các dòng thành phản hồi gửi được.

Luồng: read_table → suggest_mappings (tự ghép, người dùng sửa trên UI) → build_records
(lưu vào `campaigns.excel_data`) → records_to_responses (khi chạy chiến dịch).
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from difflib import SequenceMatcher
from typing import Any

import pandas as pd

from app.schemas.excel_schema import ColumnMapping, ColumnMatchKind, ConversionReport, ExcelPreview, RowIssue
from app.schemas.form_schema import ParsedFormStructure, ParsedQuestion
from app.services.answer_coercion import CoercionError, cell_to_text, coerce_cell, is_blank, normalize
from app.services.excel_reader import list_sheets, read_table
from app.services.spss_generator import Answer, GeneratedResponse, SurveyDataGenerator

ROW_KEY = "__row__"
TITLE_MATCH_THRESHOLD = 0.55
PREVIEW_ROWS = 5
QUESTION_CODE = re.compile(r"^\s*([A-Za-z]{1,3}\d{1,3})(?=$|[\s:.\-_)\]])")
COLUMN_CODE = re.compile(r"^\s*([A-Za-z]{1,3}\d{1,3})(?=$|[\s:.\-_)\[\]])")


def _code_of(text: str, pattern: re.Pattern[str]) -> str | None:
    match = pattern.match(text)
    return match.group(1).upper() if match else None


def _strip_code(text: str) -> str:
    return QUESTION_CODE.sub("", text).lstrip(" :.-_)")


def _similarity(left: str, right: str) -> float:
    a, b = normalize(left, strip_accents=True), normalize(right, strip_accents=True)
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()


def _candidates(question: ParsedQuestion) -> list[str]:
    if question.grid_title is not None and question.row_label:
        return [question.row_label, question.title, _strip_code(question.title)]
    return [question.title, _strip_code(question.title)]


def _title_score(column: str, question: ParsedQuestion) -> float:
    column_text = _strip_code(column) or column
    return max(_similarity(column_text, candidate) for candidate in _candidates(question))


def suggest_mappings(columns: Sequence[str], structure: ParsedFormStructure) -> list[ColumnMapping]:
    """Gợi ý ghép tự động: ưu tiên mã câu (A1, C10...), sau đó độ giống tiêu đề. Mỗi câu chỉ ghép 1 cột."""
    by_code: dict[str, list[ParsedQuestion]] = {}
    for question in structure.questions:
        code = _code_of(question.grid_title or question.title, QUESTION_CODE)
        if code:
            by_code.setdefault(code, []).append(question)

    proposals: list[tuple[float, int, ParsedQuestion, ColumnMatchKind]] = []
    for index, column in enumerate(columns):
        code = _code_of(column, COLUMN_CODE)
        coded = by_code.get(code or "", [])
        if len(coded) == 1:
            proposals.append((1.0, index, coded[0], ColumnMatchKind.CODE))
            continue
        pool = coded or structure.questions  # mã của câu lưới: chọn hàng bằng độ giống tên hàng
        best = max(pool, key=lambda q: _title_score(column, q), default=None)
        if best is not None:
            score = _title_score(column, best)
            if score >= TITLE_MATCH_THRESHOLD:
                proposals.append((score, index, best, ColumnMatchKind.TITLE))

    mappings = [ColumnMapping(column=column) for column in columns]
    used: set[str] = set()
    for score, index, question, kind in sorted(proposals, key=lambda p: (-p[0], p[1])):
        if question.entry_id in used:
            continue
        used.add(question.entry_id)
        mappings[index] = ColumnMapping(
            column=columns[index], entry_id=question.entry_id, question_title=question.title,
            kind=kind, score=round(score, 3),
        )
    return mappings


def _json_safe(value: Any) -> Any:
    if is_blank(value):
        return None
    if isinstance(value, (int, bool)):
        return value
    return cell_to_text(value)


def build_records(frame: pd.DataFrame, mappings: Sequence[ColumnMapping]) -> list[dict[str, Any]]:
    """Dòng Excel → {entry_id: giá trị, "__row__": số dòng}, an toàn để lưu JSON."""
    active = [(m.column, m.entry_id) for m in mappings if m.entry_id and m.column in frame.columns]
    records: list[dict[str, Any]] = []
    for position, (_, row) in enumerate(frame.iterrows()):
        record: dict[str, Any] = {ROW_KEY: position + 2}
        for column, entry_id in active:
            record[entry_id] = _json_safe(row[column])
        records.append(record)
    return records


def records_to_responses(
    records: Sequence[dict[str, Any]], structure: ParsedFormStructure
) -> tuple[list[GeneratedResponse], ConversionReport]:
    questions = {q.entry_id: q for q in structure.questions}
    path_builder = SurveyDataGenerator(structure)
    responses: list[GeneratedResponse] = []
    issues: list[RowIssue] = []
    invalid = 0

    for record in records:
        row_number = int(record.get(ROW_KEY, 0))
        answers: dict[str, Answer] = {}
        row_errors: list[RowIssue] = []
        for entry_id, value in record.items():
            question = questions.get(entry_id)
            if question is None:
                continue
            try:
                coerced = coerce_cell(question, value)
            except CoercionError as exc:
                row_errors.append(RowIssue(row_number=row_number, entry_id=entry_id, severity="ERROR", message=f"{question.title}: {exc}"))
                continue
            if coerced.warning:
                issues.append(RowIssue(row_number=row_number, entry_id=entry_id, severity="WARNING", message=f"{question.title}: {coerced.warning}"))
            if coerced.answer is not None:
                answers[entry_id] = coerced.answer

        pages = path_builder.build_page_history(answers)
        visited = set(pages)
        for question in structure.questions:
            if question.page_index in visited and question.is_required and question.entry_id not in answers:
                row_errors.append(RowIssue(
                    row_number=row_number, entry_id=question.entry_id, severity="ERROR",
                    message=f"Trống câu bắt buộc: {question.title}",
                ))

        if row_errors:
            invalid += 1
            issues.extend(row_errors)
            continue
        ordered = {
            q.entry_id: answers[q.entry_id]
            for q in structure.questions
            if q.entry_id in answers and q.page_index in visited
        }
        responses.append(GeneratedResponse(sequence_number=len(responses) + 1, answers=ordered, page_history=pages))

    report = ConversionReport(total_rows=len(records), valid_rows=len(responses), invalid_rows=invalid, issues=issues)
    return responses, report


def preview_file(
    content: bytes, filename: str, structure: ParsedFormStructure, *, sheet: str | int = 0
) -> ExcelPreview:
    frame = read_table(content, filename, sheet=sheet)
    columns = [str(column) for column in frame.columns]
    preview = [
        {column: _json_safe(value) for column, value in row.items()}
        for _, row in frame.head(PREVIEW_ROWS).iterrows()
    ]
    return ExcelPreview(
        filename=filename,
        sheet_names=list_sheets(content, filename),
        columns=columns,
        row_count=len(frame),
        mappings=suggest_mappings(columns, structure),
        preview_rows=preview,
    )
