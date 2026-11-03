"""Unit test cho app/services/answer_coercion.py: chuyển ô Excel/CSV thành Answer cho từng loại câu."""

from datetime import date, datetime, time

import pandas as pd
import pytest

from app.schemas.form_schema import OTHER_OPTION_VALUE, QuestionType
from app.services.answer_coercion import CoercionError, cell_to_text, coerce_cell, is_blank, normalize
from app.services.spss_generator import ANSWER_KIND_DATE, ANSWER_KIND_TEXT, ANSWER_KIND_TIME
from tests.unit.spss_factories import option, other_option, question


def _single(values: list[str], *, other: bool = False, type_id: int = QuestionType.MULTIPLE_CHOICE):
    options = [option(v) for v in values] + ([other_option()] if other else [])
    return question("100", type_id, options)


def _multi(values: list[str], *, other: bool = False):
    return _single(values, other=other, type_id=QuestionType.CHECKBOX)


GENDER = ["Nam", "Nữ"]
SCALE_1_5 = ["1", "2", "3", "4", "5"]
CHANNELS = ["Giá cả, khuyến mãi", "Đa dạng sản phẩm", "Giao hàng"]


# ---------- hàm phụ ----------

@pytest.mark.parametrize(("value", "blank"), [
    (None, True), (float("nan"), True), ("", True), ("  \t", True),
    (0, False), (0.0, False), ("0", False), ("x", False), (False, False),
])
def test_is_blank(value, blank: bool) -> None:
    assert is_blank(value) is blank


@pytest.mark.parametrize(("value", "text"), [
    (4.0, "4"), (4.5, "4.5"), (-2.0, "-2"), (7, "7"), ("  Nam ", "Nam"),
    (datetime(2024, 1, 2, 3, 4), "2024-01-02T03:04:00"),
    (pd.Timestamp("2024-01-02"), "2024-01-02T00:00:00"),
])
def test_cell_to_text(value, text: str) -> None:
    assert cell_to_text(value) == text


def test_normalize() -> None:
    assert normalize("  Rất   HÀI lòng. ") == "rất hài lòng"
    assert normalize("Đồng ý", strip_accents=True) == "dong y"
    # Dạng NFD (dấu tổ hợp) và NFC được coi như nhau
    assert normalize("Nũ") == normalize("Nũ")


# ---------- ô trống ----------

@pytest.mark.parametrize("type_id", [QuestionType.MULTIPLE_CHOICE, QuestionType.CHECKBOX, QuestionType.DATE,
                                     QuestionType.TIME, QuestionType.SHORT_ANSWER])
@pytest.mark.parametrize("value", [None, float("nan"), "", "   "])
def test_o_trong_tra_answer_none(type_id: int, value) -> None:
    q = question("1", type_id, [option("A")] if type_id in (2, 4) else [])
    result = coerce_cell(q, value)
    assert result.answer is None and result.warning is None


# ---------- văn bản ----------

def test_van_ban_giu_nguyen_va_so_nguyen_bo_phan_thap_phan() -> None:
    q = question("1", QuestionType.PARAGRAPH, [])
    assert coerce_cell(q, " Rất tốt ").answer.values == ["Rất tốt"]
    answer = coerce_cell(q, 4.0).answer
    assert answer.values == ["4"] and answer.kind == ANSWER_KIND_TEXT


# ---------- một lựa chọn ----------

@pytest.mark.parametrize(("raw", "expected"), [
    ("Nữ", "Nữ"), ("nữ", "Nữ"), ("  NỮ. ", "Nữ"), ("Nu", "Nữ"), ("nam", "Nam"), ("Nũ", "Nữ"),
])
def test_mot_lua_chon_khop_khong_phan_biet_hoa_thuong_va_dau(raw: str, expected: str) -> None:
    result = coerce_cell(_single(GENDER), raw)
    assert result.answer.values == [expected] and result.warning is None


def test_mot_lua_chon_khop_chinh_xac_uu_tien_hon_bo_dau() -> None:
    """'Nụ' và 'Nữ' cùng bỏ dấu thành 'nu' → khớp có dấu được ưu tiên."""
    q = _single(["Nữ", "Nụ"])
    assert coerce_cell(q, "nụ").answer.values == ["Nụ"]


@pytest.mark.parametrize(("raw", "expected", "numeric"), [(1, "Nam", 1.0), (2.0, "Nữ", 2.0), ("2", "Nữ", 2.0)])
def test_mot_lua_chon_ma_so_thu_tu(raw, expected: str, numeric: float) -> None:
    answer = coerce_cell(_single(GENDER), raw).answer
    assert answer.values == [expected] and answer.numeric_value == numeric


def test_ma_so_ngoai_pham_vi_va_khong_co_muc_khac_bao_loi() -> None:
    with pytest.raises(CoercionError, match="không khớp"):
        coerce_cell(_single(GENDER), 3)
    with pytest.raises(CoercionError):
        coerce_cell(_single(GENDER), "0")


def test_thang_do_0_den_10_dung_gia_tri_that() -> None:
    q = _single([str(i) for i in range(11)], type_id=QuestionType.LINEAR_SCALE)
    for raw, expected in ((0, "0"), (10.0, "10"), ("7", "7")):
        answer = coerce_cell(q, raw).answer
        assert answer.values == [expected] and answer.numeric_value == float(expected)


def test_thang_do_1_5_gia_tri_so() -> None:
    q = _single(SCALE_1_5, type_id=QuestionType.LINEAR_SCALE)
    assert coerce_cell(q, 4.0).answer.numeric_value == 4.0
    with pytest.raises(CoercionError):
        coerce_cell(q, 6)


def test_khong_khop_dua_vao_muc_khac_kem_canh_bao() -> None:
    result = coerce_cell(_single(GENDER, other=True), "Không tiết lộ")
    assert result.answer.values == [OTHER_OPTION_VALUE]
    assert result.answer.other_text == "Không tiết lộ"
    assert result.answer.numeric_value == 3.0  # K + 1
    assert "Mục khác" in result.warning


def test_mot_lua_chon_khong_khop_va_khong_co_muc_khac_bao_loi() -> None:
    with pytest.raises(CoercionError, match="Không tiết lộ"):
        coerce_cell(_single(GENDER), "Không tiết lộ")


def test_dropdown_dung_chung_logic_mot_lua_chon() -> None:
    q = _single(["Hà Nội", "TP HCM"], type_id=QuestionType.DROPDOWN)
    assert coerce_cell(q, "ha noi").answer.values == ["Hà Nội"]


# ---------- nhiều lựa chọn ----------

def test_checkbox_lua_chon_chua_dau_phay() -> None:
    result = coerce_cell(_multi(CHANNELS), "Giao hàng; Giá cả, khuyến mãi")
    assert result.answer.values == ["Giá cả, khuyến mãi", "Giao hàng"]  # theo thứ tự trên form
    assert result.warning is None and result.answer.other_text is None


def test_checkbox_khong_phan_biet_hoa_thuong_va_dau_phan_cach() -> None:
    result = coerce_cell(_multi(CHANNELS), "GIAO HÀNG | đa dạng sản phẩm")
    assert result.answer.values == ["Đa dạng sản phẩm", "Giao hàng"]


def test_checkbox_ma_so() -> None:
    assert coerce_cell(_multi(CHANNELS), "1, 3").answer.values == ["Giá cả, khuyến mãi", "Giao hàng"]
    assert coerce_cell(_multi(CHANNELS), 2.0).answer.values == ["Đa dạng sản phẩm"]


def test_checkbox_ma_so_trung_voi_lua_chon_da_chon_khong_lap() -> None:
    assert coerce_cell(_multi(CHANNELS), "Giao hàng, 3").answer.values == ["Giao hàng"]


def test_checkbox_phan_du_vao_muc_khac() -> None:
    result = coerce_cell(_multi(CHANNELS, other=True), "Giao hàng, Bạn bè giới thiệu")
    assert result.answer.values == ["Giao hàng", OTHER_OPTION_VALUE]
    assert result.answer.other_text.casefold() == "bạn bè giới thiệu"
    assert "giới thiệu" in result.warning


def test_checkbox_phan_du_muc_khac_giu_nguyen_chu_hoa() -> None:
    """BUG-010 (đã sửa): chữ người dùng gõ vào "Mục khác" phải giữ nguyên chữ hoa."""
    result = coerce_cell(_multi(CHANNELS, other=True), "Giao hàng, Bạn bè Giới Thiệu")
    assert result.answer.other_text == "Bạn bè Giới Thiệu"


def test_checkbox_phan_du_khong_co_muc_khac_bao_loi() -> None:
    with pytest.raises(CoercionError, match="(?i)bạn bè"):
        coerce_cell(_multi(CHANNELS), "Giao hàng, Bạn bè")


def test_checkbox_chi_toan_dau_phan_cach_tra_none() -> None:
    assert coerce_cell(_multi(CHANNELS), " ,; | ").answer is None


def test_checkbox_ma_so_ngoai_pham_vi_la_phan_du() -> None:
    with pytest.raises(CoercionError):
        coerce_cell(_multi(CHANNELS), "1, 9")


def test_checkbox_grid_dung_nhanh_nhieu_lua_chon() -> None:
    q = question("1", QuestionType.GRID, [option(v) for v in SCALE_1_5])
    q.is_multi_select = True
    assert coerce_cell(q, "2, 5").answer.values == ["2", "5"]


# ---------- ngày ----------

@pytest.mark.parametrize("value", [
    "15/03/2024", "15-03-2024", "2024-03-15", " 15/3/2024 ",
    date(2024, 3, 15), datetime(2024, 3, 15, 10, 30), pd.Timestamp("2024-03-15 08:00"),
])
def test_ngay_nhieu_dinh_dang(value) -> None:
    answer = coerce_cell(question("1", QuestionType.DATE, []), value).answer
    assert answer.values == ["2024-03-15"] and answer.kind == ANSWER_KIND_DATE


def test_ngay_uu_tien_ngay_truoc_thang() -> None:
    assert coerce_cell(question("1", QuestionType.DATE, []), "02/03/2024").answer.values == ["2024-03-02"]


@pytest.mark.parametrize("value", ["không phải ngày", "32/13/2024", "99999999999999999999"])
def test_ngay_khong_hop_le(value) -> None:
    with pytest.raises(CoercionError, match="ngày hợp lệ"):
        coerce_cell(question("1", QuestionType.DATE, []), value)


# ---------- giờ ----------

@pytest.mark.parametrize(("value", "expected"), [
    ("8h30", "08:30"), ("08:30", "08:30"), ("8:05", "08:05"), ("23.59", "23:59"), ("7H00", "07:00"),
    ("08:30:45", "08:30"), (time(8, 30, 15), "08:30"), (datetime(2024, 1, 1, 14, 5), "14:05"),
    (pd.Timestamp("2024-01-01 09:07"), "09:07"),
])
def test_gio_nhieu_dinh_dang(value, expected: str) -> None:
    answer = coerce_cell(question("1", QuestionType.TIME, []), value).answer
    assert answer.values == [expected] and answer.kind == ANSWER_KIND_TIME


@pytest.mark.parametrize("value", ["24:00", "12:60", "abc", "8 giờ", "830"])
def test_gio_khong_hop_le(value) -> None:
    with pytest.raises(CoercionError, match="giờ hợp lệ"):
        coerce_cell(question("1", QuestionType.TIME, []), value)
