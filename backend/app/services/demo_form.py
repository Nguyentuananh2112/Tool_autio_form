"""Form mẫu cho Chế độ tập dùng (SPEC-017): người mới thử mọi tính năng mà không cần link thật.

Có đủ các loại câu hay gặp: trắc nghiệm, rẽ nhánh, hộp kiểm (có Mục khác), lưới Likert,
thang đo 1–10, tự luận bắt buộc. Địa chỉ dùng tên miền `.invalid` nên không thể gửi đi đâu.
"""

from __future__ import annotations

from app.schemas.form_schema import (
    OTHER_OPTION_VALUE,
    NavigationAction,
    ParsedFormStructure,
    ParsedOption,
    ParsedQuestion,
    ParsedSection,
)

DEMO_TITLE = "Form mẫu: Khảo sát thói quen uống cà phê (Chế độ tập dùng)"
DEMO_VIEW_URL = "https://demo.autoform.invalid/forms/mau/viewform"
DEMO_SUBMIT_URL = "https://demo.autoform.invalid/forms/mau/formResponse"
SECTION_HABIT = 9001
SECTION_REASON = 9002
SECTION_END = 9003


def _options(*labels: str, jumps: dict[str, int] | None = None) -> list[ParsedOption]:
    jumps = jumps or {}
    return [ParsedOption(label=label, value=label, jump_to_section_id=jumps.get(label)) for label in labels]


def _likert() -> list[ParsedOption]:
    return _options("1", "2", "3", "4", "5")


def _question(entry: int, title: str, type_id: int, type_name: str, page: int, options: list[ParsedOption],
              *, required: bool = True, **extra: object) -> ParsedQuestion:
    return ParsedQuestion(
        item_id=entry, entry_id=str(entry), title=title, type_id=type_id, type_name=type_name,
        page_index=page, is_required=required, options=options, **extra,  # type: ignore[arg-type]
    )


def build_demo_structure() -> ParsedFormStructure:
    other = ParsedOption(label="Mục khác", value=OTHER_OPTION_VALUE, is_other=True)
    grid_rows = ["Hương vị", "Giá cả hợp lý", "Không gian quán", "Thái độ phục vụ"]
    questions = [
        _question(1001, "A1: Giới tính của bạn?", 2, "MULTIPLE_CHOICE", 0, _options("Nam", "Nữ")),
        _question(1002, "A2: Độ tuổi của bạn?", 2, "MULTIPLE_CHOICE", 0, _options("Dưới 18", "18 - 25", "26 - 35", "Trên 35")),
        _question(1003, "A3: Bạn có uống cà phê ít nhất 1 lần/tuần không?", 2, "MULTIPLE_CHOICE", 0,
                  _options("Có", "Không", jumps={"Có": SECTION_HABIT, "Không": SECTION_REASON})),
        _question(1004, "B1: Bạn thường mua cà phê ở đâu? (Chọn tối đa 2)", 4, "CHECKBOX", 1,
                  [*_options("Quán gần nhà", "Chuỗi cà phê", "Tự pha ở nhà", "Ứng dụng giao hàng"), other],
                  is_multi_select=True),
        *[
            _question(1010 + i, f"B2: Bạn hài lòng với quán quen thế nào? [{row}]", 7, "GRID", 1, _likert(),
                      grid_item_id=1010, grid_title="B2: Bạn hài lòng với quán quen thế nào?", row_label=row)
            for i, row in enumerate(grid_rows)
        ],
        _question(1020, "B3: Bạn sẵn lòng giới thiệu quán quen cho bạn bè ở mức nào?", 5, "LINEAR_SCALE", 1,
                  _options(*[str(i) for i in range(1, 11)]), scale_low_label="Không bao giờ", scale_high_label="Chắc chắn"),
        _question(1030, "C1: Vì sao bạn ít uống cà phê?", 2, "MULTIPLE_CHOICE", 2,
                  [*_options("Không thích vị đắng", "Lo ảnh hưởng sức khỏe", "Thích trà hơn"), other]),
        _question(1040, "D1: Bạn muốn quán cà phê cải thiện điều gì?", 0, "SHORT_ANSWER", 3, []),
    ]
    sections = [
        ParsedSection(page_index=0, title="A. Thông tin chung"),
        ParsedSection(page_index=1, section_item_id=SECTION_HABIT, title="B. Thói quen uống cà phê",
                      navigation_action=NavigationAction.GO_TO_PAGE, jump_to_section_id=SECTION_END),
        ParsedSection(page_index=2, section_item_id=SECTION_REASON, title="C. Lý do ít uống"),
        ParsedSection(page_index=3, section_item_id=SECTION_END, title="D. Góp ý"),
    ]
    return ParsedFormStructure(
        title=DEMO_TITLE, description="Form có sẵn trong app để tập dùng. Không có dữ liệu nào được gửi ra ngoài.",
        view_url=DEMO_VIEW_URL, submit_url=DEMO_SUBMIT_URL, fbzx=None,
        total_pages=len(sections), sections=sections, questions=questions,
    )
