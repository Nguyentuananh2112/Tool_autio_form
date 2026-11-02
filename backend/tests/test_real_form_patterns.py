"""Hồi quy cho các mẫu cấu trúc gặp trên Google Form thật (dev-notes CONF-001, 2026-11-02).

Dữ liệu được ẩn danh hóa, chỉ giữ lại hình dạng mảng FB_PUBLIC_LOAD_DATA_:
- Phần tử đầu tiên là Page Break (trang 0 chỉ có tiêu đề form).
- Câu rẽ nhánh mà mọi lựa chọn đều = -2 ("Tiếp tục đến phần tiếp theo").
- Page Break có item[5] = id section đích (điều hướng của trang trước nó) hoặc -3 (gửi biểu mẫu).
"""

import json

from app.schemas.form_schema import NavigationAction
from app.services.form_parser import parse_form_html
from app.services.spss_generator import SurveyDataGenerator

SEC_A, SEC_B, SEC_C, SEC_D, SEC_FINAL, SEC_END = 11, 22, 33, 44, 55, 66


def _choice(item_id: int, entry: int, options: list[tuple[str, int | None]]) -> list:
    return [item_id, f"Q{item_id}", None, 2, [[entry, [[label, None, jump, None, 0] for label, jump in options], 1]]]


def _page_break(item_id: int, nav: int | None = None) -> list:
    return [item_id, f"S{item_id}", None, 8, None, nav]


def _build_html() -> str:
    items = [
        _page_break(SEC_A),
        _choice(101, 1001, [("Đã từng", SEC_B), ("Chưa từng", SEC_D)]),
        _page_break(SEC_B),
        _choice(102, 1002, [("Rất khác", -2), ("Không khác", -2)]),
        _page_break(SEC_C),
        _choice(103, 1003, [("1", None), ("2", None)]),
        _page_break(SEC_D, nav=SEC_FINAL),  # sau trang C -> nhảy tới trang cuối
        _choice(104, 1004, [("x", None), ("y", None)]),
        _page_break(SEC_FINAL),
        _choice(105, 1005, [("A", None), ("B", None)]),
        _page_break(SEC_END, nav=-3),  # sau trang cuối -> gửi biểu mẫu
    ]
    raw = [None, ["", items, None, None, None, None, None, None, "Form thật ẩn danh"]]
    return f"<script>var FB_PUBLIC_LOAD_DATA_ = {json.dumps(raw, ensure_ascii=False)};</script>"


def test_navigation_codes_from_real_form() -> None:
    form = parse_form_html(_build_html(), "https://docs.google.com/forms/d/e/X/viewform")
    pages = {s.section_item_id: s for s in form.sections}
    assert form.total_pages == 7 and not form.questions_on_page(0)
    assert pages[SEC_C].navigation_action == NavigationAction.GO_TO_PAGE
    assert pages[SEC_C].jump_to_section_id == SEC_FINAL
    assert pages[SEC_FINAL].navigation_action == NavigationAction.SUBMIT


def test_minus_two_continues_instead_of_submitting() -> None:
    form = parse_form_html(_build_html(), "https://docs.google.com/forms/d/e/X/viewform")
    histories = {r.page_history_str for r in SurveyDataGenerator(form, seed=1).generate(300)}
    # Đã từng: 0 -> A -> B -> C -> (nhảy) FINAL -> gửi ; Chưa từng: 0 -> A -> D -> FINAL -> gửi
    assert histories == {"0,1,2,3,5", "0,1,4,5"}
