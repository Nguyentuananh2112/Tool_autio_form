"""Kiểm tra & chuẩn hóa link Google Form; dựng view_url / submit_url (Mục 5.1.A spec)."""

from __future__ import annotations

import re
from urllib.parse import urlsplit, urlunsplit

from app.services.form_errors import FormClosedError, FormFetchError, FormRequiresLoginError, InvalidFormUrlError

ALLOWED_FORM_HOSTS: frozenset[str] = frozenset({"docs.google.com", "forms.gle"})
LOGIN_HOSTS: frozenset[str] = frozenset({"accounts.google.com"})
FORM_SUFFIX_PATTERN = re.compile(r"/(viewform|formResponse|closedform|alreadyresponded)[^/]*$")
EDIT_PATH_PATTERN = re.compile(r"/(edit|viewanalytics)(/|$)")


def normalize_form_url(url: str) -> str:
    """Kiểm tra & chuẩn hóa URL người dùng nhập (chặn SSRF tới host khác Google Forms)."""
    raw = (url or "").strip()
    if not raw:
        raise InvalidFormUrlError("URL Google Form không được để trống.")
    if not re.match(r"^https?://", raw, re.IGNORECASE):
        raw = "https://" + raw

    parts = urlsplit(raw)
    host = (parts.hostname or "").lower()
    if host not in ALLOWED_FORM_HOSTS:
        raise InvalidFormUrlError("Chỉ hỗ trợ link docs.google.com/forms/... hoặc forms.gle/...")
    if host == "docs.google.com":
        if not parts.path.startswith("/forms/"):
            raise InvalidFormUrlError("Link docs.google.com không phải là Google Form.")
        if EDIT_PATH_PATTERN.search(parts.path):
            raise InvalidFormUrlError(
                "Đây là link chỉnh sửa (/edit). Hãy dùng link chia sẻ công khai (/viewform hoặc forms.gle)."
            )
    elif parts.path.strip("/") == "":
        raise InvalidFormUrlError("Link forms.gle thiếu mã biểu mẫu.")

    return urlunsplit(("https", host, parts.path, parts.query, ""))


def build_form_urls(final_url: str) -> tuple[str, str]:
    """Từ URL cuối cùng sau redirect, dựng (view_url, submit_url)."""
    parts = urlsplit(final_url)
    path = FORM_SUFFIX_PATTERN.sub("", parts.path.rstrip("/"))
    view_url = urlunsplit(("https", parts.netloc, f"{path}/viewform", "", ""))
    submit_url = re.sub(r"/viewform.*$", "/formResponse", view_url)
    return view_url, submit_url


def ensure_public_final_url(final_url: str) -> None:
    parts = urlsplit(final_url)
    host = (parts.hostname or "").lower()
    if host in LOGIN_HOSTS or "ServiceLogin" in parts.path:
        raise FormRequiresLoginError(
            "Biểu mẫu yêu cầu đăng nhập Google (giới hạn tổ chức hoặc 1 phản hồi/người). Hệ thống chỉ hỗ trợ form công khai."
        )
    if host != "docs.google.com" or "/forms/" not in parts.path:
        raise FormFetchError(f"Link chuyển hướng tới địa chỉ không phải Google Form: {host}")
    if "/closedform" in parts.path:
        raise FormClosedError("Biểu mẫu đã ngừng nhận phản hồi.")
