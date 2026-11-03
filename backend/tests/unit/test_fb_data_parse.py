"""Unit test cho parse_fb_public_load_data và decode_jump: các trường hợp biên của mảng thô."""

from typing import Any

import pytest

from app.schemas.form_schema import OTHER_OPTION_VALUE, NavigationAction, QuestionType, decode_jump
from app.services.fb_data_parser import parse_fb_public_load_data
from app.services.form_errors import FormStructureError

URLS = {"view_url": "https://v", "submit_url": "https://s", "fbzx": "-1"}


def _raw(items: Any, title: Any = "Tiêu đề", file_name: Any = "ten-file", description: Any = None) -> list[Any]:
    form_info = [description, items, None, None, None, None, None, None, title]
    return [None, form_info, None, file_name]


def _parse(items: Any, **kwargs: Any):
    return parse_fb_public_load_data(_raw(items, **kwargs), **URLS)


def _mc(item_id: int, entry: int | None, options: list, type_id: int = 2, required: int = 1) -> list:
    return [item_id, f"Câu {item_id}", None, type_id, [[entry, options, required]]]


OPTS = [["A", None, None], ["B", None, None]]


# ---------- decode_jump ----------

@pytest.mark.parametrize(
    ("code", "expected"),
    [
        (None, (NavigationAction.NEXT_PAGE, None)),
        (0, (NavigationAction.NEXT_PAGE, None)),
        (-1, (NavigationAction.NEXT_PAGE, None)),
        (-2, (NavigationAction.NEXT_PAGE, None)),
        (-3, (NavigationAction.SUBMIT, None)),
        (123456, (NavigationAction.GO_TO_PAGE, 123456)),
        (1, (NavigationAction.GO_TO_PAGE, 1)),
        (-4, (NavigationAction.NEXT_PAGE, None)),
        (-99, (NavigationAction.NEXT_PAGE, None)),
    ],
)
def test_decode_jump(code, expected) -> None:
    assert decode_jump(code) == expected


# ---------- tiêu đề, danh sách rỗng ----------

def test_danh_sach_rong_van_co_mot_trang() -> None:
    form = _parse([], description="Mô tả")
    assert form.title == "Tiêu đề" and form.description == "Mô tả"
    assert form.total_pages == 1 and len(form.sections) == 1 and form.questions == []
    assert form.fbzx == "-1" and form.view_url == "https://v"


def test_tieu_de_du_phong() -> None:
    assert _parse([], title="  ").title == "ten-file"
    assert _parse([], title=None, file_name=None).title == "Biểu mẫu không có tiêu đề"


def test_items_khong_phai_list_bao_loi() -> None:
    with pytest.raises(FormStructureError):
        parse_fb_public_load_data([None, [None, "x"]], **URLS)


def test_items_none_coi_nhu_rong() -> None:
    assert _parse(None).questions == []


def test_bo_qua_phan_tu_hong() -> None:
    """Phần tử không phải list, quá ngắn, item_id/type_id không phải số đều bị bỏ qua."""
    items = ["x", [1, "a"], ["id", "Câu", None, 2], [5, "Câu", None, True], _mc(10, 1010, OPTS)]
    form = _parse(items)
    assert [q.entry_id for q in form.questions] == ["1010"]


@pytest.mark.parametrize(
    "item",
    [
        [10, "Thiếu meta", None, 0],
        [10, "Meta None", None, 0, None],
        [10, "Meta rỗng", None, 0, [[]]],
        [10, "Entry None", None, 0, [[None, None, 1]]],
    ],
)
def test_cau_hoi_thieu_entry_id_bi_bo_qua(item) -> None:
    assert _parse([item]).questions == []


def test_trac_nghiem_khong_co_lua_chon_bi_bo_qua() -> None:
    items = [_mc(1, 11, []), _mc(2, 12, None, type_id=4), _mc(3, 13, [["", None, None]], type_id=3)]
    assert _parse(items).questions == []


# ---------- ngắt trang ----------

def test_ngat_trang_la_phan_tu_dau_tien() -> None:
    form = _parse([[900, "", None, 8, None], _mc(1, 11, OPTS)])
    assert form.total_pages == 2
    assert form.sections[1].title == "Trang 2" and form.sections[1].section_item_id == 900
    assert form.questions[0].page_index == 1


@pytest.mark.parametrize(
    ("nav", "action", "target"),
    [
        (-2, NavigationAction.NEXT_PAGE, None),
        (-3, NavigationAction.SUBMIT, None),
        (901, NavigationAction.GO_TO_PAGE, 901),
        (None, NavigationAction.NEXT_PAGE, None),
    ],
)
def test_ma_dieu_huong_cua_ngat_trang_gan_cho_trang_truoc(nav, action, target) -> None:
    items = [_mc(1, 11, OPTS), [900, "P2", "Mô tả P2", 8, None, nav], [901, "P3", None, 8, None]]
    form = _parse(items)
    assert form.sections[0].navigation_action == action
    assert form.sections[0].jump_to_section_id == target
    assert form.sections[1].navigation_action == NavigationAction.NEXT_PAGE
    assert form.sections[1].description == "Mô tả P2"
    assert form.total_pages == 3


# ---------- lưới ----------

def _grid(rows: list) -> list:
    return [50, "Lưới", None, 7, rows]


COLS = [["1"], ["2"], ["3"]]


def test_luoi_trac_nghiem_va_luoi_checkbox() -> None:
    rows = [
        [5001, COLS, 1, ["Hàng A"]],
        [5002, COLS, 0, ["Hàng B"], None, None, None, None, None, None, None, [1]],
        [5003, COLS, 0, None],
    ]
    questions = _parse([_grid(rows)]).questions
    assert [q.entry_id for q in questions] == ["5001", "5002", "5003"]
    first, second, third = questions
    assert first.type_name == "GRID" and not first.is_multi_select and first.is_required
    assert first.is_single_choice and first.title == "Lưới [Hàng A]" and first.grid_item_id == 50
    assert second.type_name == "CHECKBOX_GRID" and second.is_multi_select and not second.is_single_choice
    assert third.row_label == "Hàng 3"
    assert [o.value for o in first.options] == ["1", "2", "3"]
    assert all(o.jump_to_section_id is None for o in first.options)


def test_luoi_bo_hang_hong_va_hang_khong_cot() -> None:
    rows = ["x", [], [None, COLS], [5004, []], [5005, COLS, 1, ["OK"]]]
    questions = _parse([_grid(rows), [51, "Lưới hỏng", None, 7, "không phải list"]]).questions
    assert [q.entry_id for q in questions] == ["5005"]


def test_luoi_khong_tieu_de() -> None:
    item = [50, None, None, 7, [[5001, COLS, 1, ["A"]]]]
    assert _parse([item]).questions[0].title == "Câu hỏi lưới [A]"


# ---------- thang đo, Mục khác, rẽ nhánh ----------

def test_thang_do_tuyen_tinh_co_nhan() -> None:
    item = [60, "Thang", None, 5, [[6001, [["1"], ["2"], ["3"], ["4"], ["5"]], 1, [" Rất tệ ", "Rất tốt"]]]]
    q = _parse([item]).questions[0]
    assert q.scale_low_label == "Rất tệ" and q.scale_high_label == "Rất tốt"
    assert q.type_name == "LINEAR_SCALE" and q.is_single_choice


def test_thang_do_khong_nhan_va_khong_muc() -> None:
    no_label = [60, "Thang", None, 5, [[6001, [["1"], ["2"]], 1]]]
    empty = [61, "Thang rỗng", None, 5, [[6002, [], 1, ["a", "b"]]]]
    questions = _parse([no_label, empty]).questions
    assert len(questions) == 1
    assert questions[0].scale_low_label is None and questions[0].scale_high_label is None


def test_lua_chon_muc_khac() -> None:
    opts = [["A", None, None], ["", None, None, None, 1], ["", None, None], [None]]
    q = _parse([_mc(1, 11, opts)]).questions[0]
    assert [o.value for o in q.options] == ["A", OTHER_OPTION_VALUE]
    assert q.has_other and q.options[1].is_other and q.options[1].label == "Mục khác"
    assert [o.value for o in q.choice_options] == ["A"]


def test_dropdown_re_nhanh_va_checkbox_khong_re_nhanh() -> None:
    branching = [["Có", None, 900], ["Không", None, -3], ["", None, -2, None, 1]]
    items = [
        _mc(1, 11, branching, type_id=3),
        _mc(2, 12, [["X", None, 900], ["Y", None, "901"]], type_id=4),
        [900, "P2", None, 8, None],
    ]
    dropdown, checkbox = _parse(items).questions
    assert [o.jump_to_section_id for o in dropdown.options] == [900, -3, -2]
    assert dropdown.options[2].is_other
    assert checkbox.is_multi_select and all(o.jump_to_section_id is None for o in checkbox.options)


def test_re_nhanh_toi_section_khong_ton_tai_chi_canh_bao(caplog) -> None:
    form = _parse([_mc(1, 11, [["A", None, 777], ["B", None, None]])])
    assert form.questions[0].options[0].jump_to_section_id == 777
    assert "777" in caplog.text


@pytest.mark.parametrize("type_id", [6, 11, 12, 99])
def test_phan_tu_tinh_bi_bo_qua(type_id: int) -> None:
    items = [[70, "Tĩnh", None, type_id, [[7001, None, 0]]], _mc(1, 11, OPTS)]
    form = _parse(items)
    assert [q.entry_id for q in form.questions] == ["11"] and form.total_pages == 1


@pytest.mark.parametrize(
    ("type_id", "name"),
    [(QuestionType.DATE, "DATE"), (QuestionType.TIME, "TIME"), (QuestionType.SHORT_ANSWER, "SHORT_ANSWER"),
     (QuestionType.PARAGRAPH, "PARAGRAPH")],
)
def test_ngay_gio_va_van_ban(type_id: int, name: str) -> None:
    item = [80, None, "Mô tả câu", type_id, [[8001, None, 0]]]
    q = _parse([item]).questions[0]
    assert q.type_name == name and q.options == [] and not q.is_required
    assert q.title == "Câu hỏi 80" and q.description == "Mô tả câu"
    assert q.is_text == (type_id in (QuestionType.SHORT_ANSWER, QuestionType.PARAGRAPH))


def test_is_required_mac_dinh_false_khi_thieu() -> None:
    item = [80, "Câu", None, 0, [[8001]]]
    q = _parse([item]).questions[0]
    assert q.entry_id == "8001" and q.is_required is False
