"""Bảo vệ API local: chỉ tiến trình app desktop (biết APP_TOKEN) mới gọi được backend.

Không có tài khoản/đăng nhập (SPEC-011). Backend chỉ nghe 127.0.0.1, nhưng một trang web
bất kỳ trong trình duyệt của người dùng vẫn có thể gửi request tới cổng local → cần token.
"""

from __future__ import annotations

import secrets

from app.core.config import Settings

TOKEN_HEADER = "X-App-Token"


def generate_app_token() -> str:
    return secrets.token_urlsafe(32)


def is_token_valid(app_settings: Settings, provided: str | None) -> bool:
    expected = app_settings.APP_TOKEN
    if not expected:
        # Fail closed: bản phát hành bắt buộc có token
        return not app_settings.is_production
    if not provided:
        return False
    return secrets.compare_digest(provided.encode(), expected.encode())
