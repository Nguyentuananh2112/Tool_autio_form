"""Cấu trúc chuẩn hóa của một Google Form sau khi bóc tách `FB_PUBLIC_LOAD_DATA_`."""

from __future__ import annotations

from enum import IntEnum, StrEnum

from pydantic import BaseModel, ConfigDict, Field

OTHER_OPTION_VALUE = "__other_option__"

# Mã điều hướng đã xác nhận trên form thật (dev-notes CONF-001) — KHÁC Mục 5.1.C của spec:
#   -2 = "Tiếp tục đến phần tiếp theo" (mặc định khi bật rẽ nhánh), -3 = "Gửi biểu mẫu".
#   -1 chưa gặp trên form thật (có thể là "Quay lại phần 1"); tạm coi như sang trang tiếp.
JUMP_UNCONFIRMED = -1
JUMP_NEXT_PAGE = -2
JUMP_SUBMIT = -3


class QuestionType(IntEnum):
    SHORT_ANSWER = 0
    PARAGRAPH = 1
    MULTIPLE_CHOICE = 2
    DROPDOWN = 3
    CHECKBOX = 4
    LINEAR_SCALE = 5
    GRID = 7
    DATE = 9
    TIME = 10


PAGE_BREAK_TYPE_ID = 8

QUESTION_TYPE_NAMES: dict[int, str] = {
    QuestionType.SHORT_ANSWER: "SHORT_ANSWER",
    QuestionType.PARAGRAPH: "PARAGRAPH",
    QuestionType.MULTIPLE_CHOICE: "MULTIPLE_CHOICE",
    QuestionType.DROPDOWN: "DROPDOWN",
    QuestionType.CHECKBOX: "CHECKBOX",
    QuestionType.LINEAR_SCALE: "LINEAR_SCALE",
    QuestionType.GRID: "GRID",
    QuestionType.DATE: "DATE",
    QuestionType.TIME: "TIME",
}

TEXT_TYPES: frozenset[int] = frozenset({QuestionType.SHORT_ANSWER, QuestionType.PARAGRAPH})
SINGLE_CHOICE_TYPES: frozenset[int] = frozenset(
    {QuestionType.MULTIPLE_CHOICE, QuestionType.DROPDOWN, QuestionType.LINEAR_SCALE}
)
BRANCHING_TYPES: frozenset[int] = frozenset({QuestionType.MULTIPLE_CHOICE, QuestionType.DROPDOWN})


class NavigationAction(StrEnum):
    NEXT_PAGE = "NEXT_PAGE"
    SUBMIT = "SUBMIT"
    GO_TO_PAGE = "GO_TO_PAGE"


def decode_jump(code: int | None) -> tuple[NavigationAction, int | None]:
    """Chuyển mã rẽ nhánh thô thành (hành động, section_item_id đích)."""
    if code is None or code == 0 or code in (JUMP_NEXT_PAGE, JUMP_UNCONFIRMED):
        return NavigationAction.NEXT_PAGE, None
    if code == JUMP_SUBMIT:
        return NavigationAction.SUBMIT, None
    if code > 0:
        return NavigationAction.GO_TO_PAGE, code
    return NavigationAction.NEXT_PAGE, None


class ParsedOption(BaseModel):
    label: str
    value: str
    is_other: bool = False
    jump_to_section_id: int | None = None


class ParsedSection(BaseModel):
    page_index: int = Field(ge=0)
    section_item_id: int | None = None
    title: str
    description: str | None = None
    # Hành động sau khi hoàn thành trang này (nếu không có câu hỏi rẽ nhánh nào kích hoạt)
    navigation_action: NavigationAction = NavigationAction.NEXT_PAGE
    jump_to_section_id: int | None = None


class ParsedQuestion(BaseModel):
    item_id: int
    entry_id: str
    title: str
    description: str | None = None
    type_id: int
    type_name: str
    page_index: int = Field(ge=0)
    is_required: bool = False
    options: list[ParsedOption] = Field(default_factory=list)
    # Linear scale
    scale_low_label: str | None = None
    scale_high_label: str | None = None
    # Grid: mỗi hàng được tách thành một ParsedQuestion riêng với entry_id riêng
    grid_item_id: int | None = None
    grid_title: str | None = None
    row_label: str | None = None
    # True với Checkbox và Checkbox Grid
    is_multi_select: bool = False

    @property
    def has_other(self) -> bool:
        return any(option.is_other for option in self.options)

    @property
    def choice_options(self) -> list[ParsedOption]:
        """Các lựa chọn thông thường (không gồm ô "Mục khác")."""
        return [option for option in self.options if not option.is_other]

    @property
    def is_text(self) -> bool:
        return self.type_id in TEXT_TYPES

    @property
    def is_single_choice(self) -> bool:
        return self.type_id in SINGLE_CHOICE_TYPES or (
            self.type_id == QuestionType.GRID and not self.is_multi_select
        )


class ParsedFormStructure(BaseModel):
    model_config = ConfigDict(use_enum_values=False)

    title: str
    description: str | None = None
    view_url: str
    submit_url: str
    fbzx: str | None = None
    total_pages: int = Field(ge=1)
    sections: list[ParsedSection]
    questions: list[ParsedQuestion]

    def get_question(self, entry_id: str) -> ParsedQuestion | None:
        return next((q for q in self.questions if q.entry_id == entry_id), None)

    def page_index_of_section(self, section_item_id: int) -> int | None:
        return next(
            (s.page_index for s in self.sections if s.section_item_id == section_item_id), None
        )

    def questions_on_page(self, page_index: int) -> list[ParsedQuestion]:
        return [q for q in self.questions if q.page_index == page_index]
