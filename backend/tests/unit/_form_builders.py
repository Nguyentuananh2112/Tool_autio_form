"""Dựng nhanh form / log / luật bằng đối tượng thật (không cần DB) cho test đơn vị."""

from datetime import datetime
from typing import Any

from app.models import QuestionRule, SubmissionLog
from app.schemas.form_schema import (
    OTHER_OPTION_VALUE,
    QUESTION_TYPE_NAMES,
    ParsedFormStructure,
    ParsedOption,
    ParsedQuestion,
    ParsedSection,
    QuestionType,
)


def question(entry_id: str, type_id: int, labels: list[str] | None = None, *, other: bool = False,
             title: str | None = None, multi: bool | None = None) -> ParsedQuestion:
    options = [ParsedOption(label=label, value=label) for label in labels or []]
    if other:
        options.append(ParsedOption(label="Mục khác", value=OTHER_OPTION_VALUE, is_other=True))
    return ParsedQuestion(
        item_id=int(entry_id), entry_id=entry_id, title=title or f"Câu {entry_id}", type_id=type_id,
        type_name=QUESTION_TYPE_NAMES[type_id], page_index=0, options=options,
        is_multi_select=type_id == QuestionType.CHECKBOX if multi is None else multi,
    )


def form(*questions: ParsedQuestion) -> ParsedFormStructure:
    return ParsedFormStructure(
        title="Form thử", view_url="https://docs.google.com/forms/d/e/X/viewform",
        submit_url="https://docs.google.com/forms/d/e/X/formResponse", total_pages=1,
        sections=[ParsedSection(page_index=0, title="Trang 1")], questions=list(questions),
    )


def log(seq: int, payload: dict[str, Any], *, ok: bool = True, **kwargs: Any) -> SubmissionLog:
    return SubmissionLog(
        sequence_number=seq, payload_sent=payload, is_success=ok,
        engine_used=kwargs.get("engine", "HTTPX"), status_code=kwargs.get("status", 200 if ok else 400),
        error_detail=kwargs.get("error"), executed_at=kwargs.get("at", datetime(2026, 1, 2, 3, 4, 5)),
    )


def rule(entry_id: str, type_id: int, config: dict[str, Any]) -> QuestionRule:
    return QuestionRule(entry_id=entry_id, question_type=type_id, config_json=config)
