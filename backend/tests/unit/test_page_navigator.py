"""Unit test cho app/services/spss/page_navigator.py (mô phỏng đường đi pageHistory)."""

from app.schemas.form_schema import JUMP_NEXT_PAGE, JUMP_SUBMIT, NavigationAction, QuestionType
from app.services.spss.answers import Answer
from app.services.spss.page_navigator import PageNavigator
from tests.unit.spss_factories import form, option, question, section

S1, S2, S3 = 501, 502, 503


def _branch(entry_id: str, page: int, jumps: dict[str, int | None], type_id: int = QuestionType.MULTIPLE_CHOICE):
    return question(entry_id, type_id, [option(v, j) for v, j in jumps.items()], page=page)


def _three_pages(*questions, sections=None):
    sections = sections or [section(0, None), section(1, S1), section(2, S2)]
    return PageNavigator(form(sections, list(questions)))


def _ans(**values: str) -> dict[str, Answer]:
    return {key.removeprefix("e"): Answer(values=[value]) for key, value in values.items()}


def test_khong_re_nhanh_di_het_cac_trang() -> None:
    assert _three_pages().page_history({}) == [0, 1, 2]


def test_re_nhanh_toi_section_va_nop() -> None:
    nav = _three_pages(_branch("10", 0, {"Có": S2, "Không": JUMP_SUBMIT}))
    assert nav.page_history(_ans(e10="Có")) == [0, 2]
    assert nav.page_history(_ans(e10="Không")) == [0]


def test_cau_re_nhanh_cuoi_cung_trong_trang_thang() -> None:
    nav = _three_pages(
        _branch("10", 0, {"A": JUMP_SUBMIT}),
        _branch("11", 0, {"B": S2}),
    )
    assert nav.page_history(_ans(e10="A", e11="B")) == [0, 2]


def test_lua_chon_khong_co_jump_khong_ghi_de_cau_truoc() -> None:
    nav = _three_pages(
        _branch("10", 0, {"A": S2}),
        _branch("11", 0, {"B": None}),
    )
    assert nav.page_history(_ans(e10="A", e11="B")) == [0, 2]


def test_dropdown_cung_re_nhanh() -> None:
    nav = _three_pages(_branch("10", 0, {"X": JUMP_SUBMIT}, type_id=QuestionType.DROPDOWN))
    assert nav.page_history(_ans(e10="X")) == [0]


def test_checkbox_khong_tinh_la_re_nhanh() -> None:
    nav = _three_pages(_branch("10", 0, {"X": JUMP_SUBMIT}, type_id=QuestionType.CHECKBOX))
    assert nav.page_history(_ans(e10="X")) == [0, 1, 2]


def test_cau_tra_loi_rong_hoac_thieu_bi_bo_qua() -> None:
    nav = _three_pages(_branch("10", 0, {"A": JUMP_SUBMIT}))
    assert nav.page_history({"10": Answer(values=[])}) == [0, 1, 2]
    assert nav.page_history({}) == [0, 1, 2]


def test_jump_toi_section_khong_ton_tai_sang_trang_ke() -> None:
    nav = _three_pages(_branch("10", 0, {"A": 999_999}))
    assert nav.page_history(_ans(e10="A")) == [0, 1, 2]


def test_ma_next_page_tuong_minh() -> None:
    nav = _three_pages(_branch("10", 0, {"A": JUMP_NEXT_PAGE}))
    assert nav.page_history(_ans(e10="A")) == [0, 1, 2]


def test_nhay_nguoc_ve_trang_da_qua_thi_nop() -> None:
    nav = _three_pages(_branch("20", 1, {"Lại": S1}), _branch("30", 2, {"Về": S1}))
    # Trang 1 nhảy về chính nó → dừng ngay để tránh vòng lặp
    assert nav.page_history(_ans(e20="Lại")) == [0, 1]
    # Trang 2 nhảy ngược về trang 1 → dừng
    assert nav.page_history(_ans(e30="Về")) == [0, 1, 2]


def test_dieu_huong_cap_section_submit_va_go_to() -> None:
    sections = [
        section(0, None, NavigationAction.GO_TO_PAGE, S2),
        section(1, S1),
        section(2, S2, NavigationAction.SUBMIT),
        section(3, S3),
    ]
    nav = PageNavigator(form(sections, []))
    assert nav.page_history({}) == [0, 2]


def test_re_nhanh_cau_hoi_uu_tien_hon_dieu_huong_section() -> None:
    sections = [section(0, None, NavigationAction.SUBMIT), section(1, S1), section(2, S2)]
    nav = PageNavigator(form(sections, [_branch("10", 0, {"A": S1, "B": None})]))
    assert nav.page_history(_ans(e10="A")) == [0, 1, 2]
    assert nav.page_history(_ans(e10="B")) == [0]


def test_trang_khong_co_section_mac_dinh_sang_trang_ke() -> None:
    """total_pages lớn hơn số section (dữ liệu thiếu) → trang thiếu coi như NEXT_PAGE."""
    structure = form([section(0, None)], [])
    structure.total_pages = 3
    assert PageNavigator(structure).page_history({}) == [0, 1, 2]


def test_form_page_break_dau_tien() -> None:
    """Page break là phần tử đầu tiên → trang 0 trống, câu hỏi bắt đầu từ trang 1."""
    sections = [section(0, None), section(1, S1), section(2, S2)]
    nav = PageNavigator(form(sections, [_branch("10", 1, {"Nộp": JUMP_SUBMIT, "Tiếp": S2})]))
    assert nav.page_history(_ans(e10="Nộp")) == [0, 1]
    assert nav.page_history(_ans(e10="Tiếp")) == [0, 1, 2]
