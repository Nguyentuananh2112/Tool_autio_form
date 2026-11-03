"""Unit test cho app/services/form_url.py: chuẩn hóa link, dựng view/submit URL, kiểm tra URL cuối."""

import pytest

from app.services.form_errors import FormClosedError, FormFetchError, FormRequiresLoginError, InvalidFormUrlError
from app.services.form_url import build_form_urls, ensure_public_final_url, normalize_form_url

BASE = "https://docs.google.com/forms/d/e/ABC"


# ---------- normalize_form_url ----------

@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (f"{BASE}/viewform", f"{BASE}/viewform"),
        ("http://docs.google.com/forms/d/e/ABC/viewform", f"{BASE}/viewform"),
        ("HTTPS://DOCS.GOOGLE.COM/forms/d/e/ABC/viewform", f"{BASE}/viewform"),
        ("docs.google.com/forms/d/e/ABC/viewform", f"{BASE}/viewform"),
        (f"   {BASE}/viewform?usp=sf_link  \n", f"{BASE}/viewform?usp=sf_link"),
        (f"{BASE}/viewform#doan-neo", f"{BASE}/viewform"),
        ("https://forms.gle/abc123", "https://forms.gle/abc123"),
        ("forms.gle/abc123", "https://forms.gle/abc123"),
        ("http://forms.gle/abc123", "https://forms.gle/abc123"),
    ],
)
def test_chuan_hoa_link_hop_le(raw: str, expected: str) -> None:
    """Thêm https, ép https, hạ chữ host, bỏ khoảng trắng và fragment, giữ query."""
    assert normalize_form_url(raw) == expected


@pytest.mark.parametrize("raw", ["", "   ", None])
def test_link_trong_bi_tu_choi(raw) -> None:
    with pytest.raises(InvalidFormUrlError, match="trống"):
        normalize_form_url(raw)


@pytest.mark.parametrize(
    "raw",
    [
        "https://evil.com/forms/d/e/ABC/viewform",
        "https://docs.google.com.evil.com/forms/d/x",
        "https://google.com/forms/d/x",
        "ftp://docs.google.com/forms/d/x",
        "https://user@evil.com/docs.google.com/forms/d/x",
    ],
)
def test_host_la_bi_tu_choi(raw: str) -> None:
    """Chặn SSRF: chỉ cho docs.google.com và forms.gle."""
    with pytest.raises(InvalidFormUrlError):
        normalize_form_url(raw)


@pytest.mark.parametrize(
    "raw",
    ["https://docs.google.com/document/d/1/edit", "https://docs.google.com/spreadsheets/d/1", "https://docs.google.com/"],
)
def test_docs_google_khong_phai_form(raw: str) -> None:
    with pytest.raises(InvalidFormUrlError, match="không phải là Google Form"):
        normalize_form_url(raw)


@pytest.mark.parametrize(
    "raw",
    [
        "https://docs.google.com/forms/d/ABC/edit",
        "https://docs.google.com/forms/d/ABC/edit?usp=sharing",
        "https://docs.google.com/forms/d/ABC/edit/",
        "https://docs.google.com/forms/d/ABC/viewanalytics",
    ],
)
def test_link_chinh_sua_bi_tu_choi(raw: str) -> None:
    with pytest.raises(InvalidFormUrlError, match="/edit"):
        normalize_form_url(raw)


def test_duong_dan_chua_chu_edit_nhung_khong_phai_doan_edit_van_hop_le() -> None:
    """'/editor' hay mã form chứa 'edit' không bị nhầm là link chỉnh sửa."""
    assert normalize_form_url(f"{BASE}editx/viewform") == f"{BASE}editx/viewform"


@pytest.mark.parametrize("raw", ["https://forms.gle", "https://forms.gle/", "forms.gle///"])
def test_forms_gle_thieu_ma(raw: str) -> None:
    with pytest.raises(InvalidFormUrlError, match="thiếu mã"):
        normalize_form_url(raw)


# ---------- build_form_urls ----------

@pytest.mark.parametrize(
    "final_url",
    [
        f"{BASE}/viewform",
        f"{BASE}/viewform?usp=sf_link",
        f"{BASE}/viewform?usp=sf_link&entry.1=x",
        f"{BASE}/formResponse",
        f"{BASE}/closedform",
        f"{BASE}/alreadyresponded",
        f"{BASE}/viewform/",
        f"{BASE}",
        f"{BASE}/",
        f"{BASE}/viewform#x",
    ],
)
def test_dung_url_tu_moi_hau_to(final_url: str) -> None:
    """Mọi hậu tố/query đều quy về .../viewform và .../formResponse."""
    view_url, submit_url = build_form_urls(final_url)
    assert view_url == f"{BASE}/viewform"
    assert submit_url == f"{BASE}/formResponse"


def test_dung_url_giu_duong_dan_u_0() -> None:
    """Link của người đăng nhập nhiều tài khoản (/u/0/) vẫn giữ nguyên tiền tố."""
    view_url, submit_url = build_form_urls("https://docs.google.com/forms/u/0/d/e/XYZ/viewform?pli=1")
    assert view_url == "https://docs.google.com/forms/u/0/d/e/XYZ/viewform"
    assert submit_url == "https://docs.google.com/forms/u/0/d/e/XYZ/formResponse"


def test_dung_url_luon_dung_https() -> None:
    view_url, submit_url = build_form_urls("http://docs.google.com/forms/d/e/ABC/viewform")
    assert view_url.startswith("https://") and submit_url.startswith("https://")


# ---------- ensure_public_final_url ----------

def test_url_cong_khai_hop_le_khong_loi() -> None:
    ensure_public_final_url(f"{BASE}/viewform?usp=sf_link")


@pytest.mark.parametrize(
    "final_url",
    [
        "https://accounts.google.com/v3/signin/identifier?continue=x",
        "https://ACCOUNTS.google.com/ServiceLogin?continue=x",
        "https://docs.google.com/forms/ServiceLogin?x=1",
    ],
)
def test_url_yeu_cau_dang_nhap(final_url: str) -> None:
    with pytest.raises(FormRequiresLoginError):
        ensure_public_final_url(final_url)


def test_url_form_da_dong() -> None:
    with pytest.raises(FormClosedError):
        ensure_public_final_url(f"{BASE}/closedform")


@pytest.mark.parametrize(
    "final_url",
    ["https://example.com/forms/x", "https://docs.google.com/document/d/1", "https://forms.gle/abc"],
)
def test_url_khong_phai_form(final_url: str) -> None:
    """Redirect tới host khác hoặc không có /forms/ → lỗi tải form (forms.gle phải được redirect trước)."""
    with pytest.raises(FormFetchError, match="không phải Google Form"):
        ensure_public_final_url(final_url)
