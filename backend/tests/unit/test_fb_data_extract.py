"""Unit test cho phần trích xuất của fb_data_parser: _safe_get, _as_int, FB_PUBLIC_LOAD_DATA_, fbzx."""

import json

import pytest

from app.services.fb_data_parser import _as_int, _safe_get, extract_fb_public_load_data, extract_fbzx
from app.services.form_errors import FormRequiresLoginError, FormStructureError

MINIMAL = [None, ["Mô tả", [], None]]


def _page(data_json: str, tail: str = ";</script>") -> str:
    return f"<html><script>var FB_PUBLIC_LOAD_DATA_ = {data_json}{tail}</html>"


# ---------- _safe_get ----------

@pytest.mark.parametrize(
    ("indices", "expected"),
    [
        ((), [[1, [2, 3]], None, "x"]),
        ((0, 0), 1),
        ((0, 1, 1), 3),
        ((2,), "x"),
        ((-1,), "x"),
        ((-3, 0), 1),
    ],
)
def test_safe_get_truy_cap_hop_le(indices, expected) -> None:
    assert _safe_get([[1, [2, 3]], None, "x"], *indices) == expected


@pytest.mark.parametrize(
    "indices",
    [(5,), (-4,), (0, 0, 0), (2, 0), (1,), (1, 0)],
)
def test_safe_get_tra_mac_dinh_khi_khong_truy_cap_duoc(indices) -> None:
    """Vượt chỉ số, đi sâu vào số/chuỗi, hoặc gặp None → default."""
    assert _safe_get([[1, [2, 3]], None, "x"], *indices, default="MD") == "MD"


def test_safe_get_khong_phai_list() -> None:
    assert _safe_get({"a": 1}, 0) is None
    assert _safe_get(None, 0, default=0) == 0


def test_safe_get_gia_tri_falsy_khac_none_duoc_giu() -> None:
    assert _safe_get([0, "", []], 0, default=9) == 0
    assert _safe_get([0, "", []], 1, default=9) == ""
    assert _safe_get([0, "", []], 2, default=9) == []


# ---------- _as_int ----------

@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (5, 5), (-3, -3), (0, 0), ("12", 12), (" -7 ", -7), ("007", 7),
        (True, None), (False, None), (1.0, None), ("1.5", None), ("abc", None),
        ("", None), (None, None), ([1], None), ("1e3", None),
    ],
)
def test_as_int(value, expected) -> None:
    """bool bị từ chối dù là lớp con của int; chuỗi chỉ nhận số nguyên."""
    assert _as_int(value) == expected


# ---------- extract_fb_public_load_data ----------

def test_trich_xuat_bang_regex() -> None:
    assert extract_fb_public_load_data(_page(json.dumps(MINIMAL))) == MINIMAL


def test_trich_xuat_du_phong_khi_chuoi_chua_dau_ket_thuc() -> None:
    """Tiêu đề chứa "];</script>" làm regex không tham lam cắt sai → dùng raw_decode."""
    data = [None, ["Mô tả có ];</script> bên trong", [], None], None, "Tiêu đề ];"]
    html = _page(json.dumps(data, ensure_ascii=False))
    assert extract_fb_public_load_data(html) == data


def test_trich_xuat_du_phong_khi_khong_co_the_script_dong() -> None:
    """Không có "</script>" ngay sau → regex trượt, raw_decode vẫn đọc được."""
    html = _page(json.dumps(MINIMAL), tail=";\nvar khac = 1;")
    assert extract_fb_public_load_data(html) == MINIMAL


def test_trich_xuat_khong_co_dau_var() -> None:
    html = f"<script>window.FB_PUBLIC_LOAD_DATA_={json.dumps(MINIMAL)}</script>"
    assert extract_fb_public_load_data(html) == MINIMAL


def test_thieu_marker_bao_loi_cau_truc() -> None:
    with pytest.raises(FormStructureError, match="Không tìm thấy"):
        extract_fb_public_load_data("<html><body>Không có gì</body></html>")


def test_trang_dang_nhap_bao_loi_dang_nhap() -> None:
    html = '<a href="https://accounts.google.com/ServiceLogin?continue=x">Đăng nhập</a>'
    with pytest.raises(FormRequiresLoginError):
        extract_fb_public_load_data(html)


def test_marker_khong_co_mang() -> None:
    with pytest.raises(FormStructureError, match="không chứa mảng"):
        extract_fb_public_load_data("<script>var FB_PUBLIC_LOAD_DATA_ = null</script>")


@pytest.mark.parametrize(
    "html",
    [
        _page("[1, 2,]"),  # regex khớp nhưng JSON hỏng
        "<script>var FB_PUBLIC_LOAD_DATA_ = [1, {</script>",  # nhánh raw_decode hỏng
    ],
)
def test_json_hong_bao_loi_giai_ma(html: str) -> None:
    with pytest.raises(FormStructureError, match="giải mã"):
        extract_fb_public_load_data(html)


@pytest.mark.parametrize("data", [[], [None], [None, "không phải list"], [None, None]])
def test_cau_truc_sai_dinh_dang(data) -> None:
    with pytest.raises(FormStructureError, match="định dạng"):
        extract_fb_public_load_data(_page(json.dumps(data)))


# ---------- extract_fbzx ----------

@pytest.mark.parametrize(
    "html",
    [
        '<input type="hidden" name="fbzx" value="-123">',
        '<input type="hidden" value="-123" name="fbzx">',
        '<INPUT TYPE="hidden" NAME="fbzx" VALUE="-123">',
        '<input value="-123" class="a" name="fbzx" />',
    ],
)
def test_fbzx_moi_thu_tu_thuoc_tinh(html: str) -> None:
    assert extract_fbzx(html) == "-123"


def test_fbzx_du_phong_tu_raw_14() -> None:
    raw = [None] * 14 + [" -456 "]
    assert extract_fbzx("<html></html>", raw) == "-456"
    assert extract_fbzx("<html></html>", [None] * 14 + [789]) == "789"


def test_fbzx_html_uu_tien_hon_raw() -> None:
    raw = [None] * 14 + ["-456"]
    assert extract_fbzx('<input name="fbzx" value="-1">', raw) == "-1"


def test_fbzx_value_rong_thi_dung_du_phong() -> None:
    raw = [None] * 14 + ["-456"]
    assert extract_fbzx('<input name="fbzx" value="">', raw) == "-456"


@pytest.mark.parametrize("raw", [None, [], [None] * 15, [None] * 14 + ["  "], [None] * 14 + [[1]]])
def test_fbzx_khong_co(raw) -> None:
    assert extract_fbzx("<html></html>", raw) is None
