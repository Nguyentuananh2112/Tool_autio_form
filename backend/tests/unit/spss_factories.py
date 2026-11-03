"""Hàm dựng nhanh ParsedQuestion / ParsedFormStructure cho unit test nhóm spss."""

from __future__ import annotations

from app.schemas.form_schema import (
    OTHER_OPTION_VALUE,
    QUESTION_TYPE_NAMES,
    NavigationAction,
    ParsedFormStructure,
    ParsedOption,
    ParsedQuestion,
    ParsedSection,
    QuestionType,
)


def option(value: str, jump: int | None = None) -> ParsedOption:
    return ParsedOption(label=value, value=value, jump_to_section_id=jump)


def other_option(jump: int | None = None) -> ParsedOption:
    return ParsedOption(label="Mục khác", value=OTHER_OPTION_VALUE, is_other=True, jump_to_section_id=jump)


def question(
    entry_id: str,
    type_id: int = QuestionType.MULTIPLE_CHOICE,
    options: list[ParsedOption] | None = None,
    *,
    required: bool = False,
    page: int = 0,
    title: str | None = None,
) -> ParsedQuestion:
    return ParsedQuestion(
        item_id=int(entry_id),
        entry_id=entry_id,
        title=title or f"Câu {entry_id}",
        type_id=type_id,
        type_name=QUESTION_TYPE_NAMES.get(type_id, "GRID"),
        page_index=page,
        is_required=required,
        options=options or [],
        is_multi_select=type_id == QuestionType.CHECKBOX,
    )


def section(page: int, item_id: int | None, action: NavigationAction = NavigationAction.NEXT_PAGE,
            jump: int | None = None) -> ParsedSection:
    return ParsedSection(page_index=page, section_item_id=item_id, title=f"Trang {page + 1}",
                         navigation_action=action, jump_to_section_id=jump)


def form(sections: list[ParsedSection], questions: list[ParsedQuestion]) -> ParsedFormStructure:
    return ParsedFormStructure(
        title="Form thử", view_url="https://docs.google.com/forms/d/e/X/viewform",
        submit_url="https://docs.google.com/forms/d/e/X/formResponse", total_pages=len(sections),
        sections=sections, questions=questions,
    )
