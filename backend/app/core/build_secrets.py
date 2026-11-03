"""Key Gemini chung / dự phòng được nhúng lúc build bản phát hành (SPEC-020).

GitHub Actions chạy `packaging/write_build_secrets.py` để sinh file `_build_secrets.py` (bị gitignore)
từ GitHub Secrets ngay trước khi đóng gói. Key không bao giờ nằm trong mã nguồn.
Mã hoá XOR chỉ để key không lộ nguyên văn khi ai đó lục chuỗi trong file cài — KHÔNG phải bảo mật;
thiệt hại khi lộ key được chặn bằng hạn mức chi tiêu trên Google Cloud.
"""

from __future__ import annotations

import base64

_MASK = b"auto-form/gemini"


def encode(key: str) -> str:
    raw = key.encode()
    return base64.b64encode(bytes(b ^ _MASK[i % len(_MASK)] for i, b in enumerate(raw))).decode()


def decode(blob: str) -> str | None:
    if not blob:
        return None
    raw = base64.b64decode(blob)
    value = bytes(b ^ _MASK[i % len(_MASK)] for i, b in enumerate(raw)).decode().strip()
    return value or None


def embedded_keys() -> tuple[str | None, str | None]:
    """(key chung, key dự phòng). Bản chạy từ mã nguồn không có file sinh → (None, None)."""
    try:
        from app.core import _build_secrets  # type: ignore[attr-defined]
    except ImportError:
        return None, None
    return decode(getattr(_build_secrets, "SHARED", "")), decode(getattr(_build_secrets, "BACKUP", ""))
