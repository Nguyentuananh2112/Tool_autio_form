"""Lưu bí mật (Gemini API key) trong kho bảo mật của hệ điều hành (Windows Credential Manager).

Các hàm ở đây là đồng bộ và rất nhanh; trong code async gọi qua `asyncio.to_thread`.
"""

from __future__ import annotations

import logging

import keyring
from keyring.errors import KeyringError, PasswordDeleteError

logger = logging.getLogger(__name__)

SERVICE_NAME = "Auto-Form"
GEMINI_KEY_NAME = "gemini_api_key"


class SecretStoreError(RuntimeError):
    pass


def get_gemini_api_key() -> str | None:
    try:
        value = keyring.get_password(SERVICE_NAME, GEMINI_KEY_NAME)
    except KeyringError:
        logger.exception("Không đọc được Gemini API key từ kho bảo mật")
        return None
    return value.strip() if value and value.strip() else None


def set_gemini_api_key(api_key: str) -> None:
    cleaned = api_key.strip()
    if not cleaned:
        raise SecretStoreError("API key không được để trống.")
    try:
        keyring.set_password(SERVICE_NAME, GEMINI_KEY_NAME, cleaned)
    except KeyringError as exc:
        raise SecretStoreError(f"Không lưu được API key vào kho bảo mật: {exc}") from exc


def delete_gemini_api_key() -> None:
    try:
        keyring.delete_password(SERVICE_NAME, GEMINI_KEY_NAME)
    except PasswordDeleteError:
        return  # chưa từng lưu
    except KeyringError as exc:
        raise SecretStoreError(f"Không xóa được API key: {exc}") from exc


def resolve_gemini_api_key(explicit: str | None = None) -> str | None:
    """Thứ tự ưu tiên: key truyền vào → kho bảo mật → biến môi trường (chỉ khi phát triển)."""
    if explicit and explicit.strip():
        return explicit.strip()
    stored = get_gemini_api_key()
    if stored:
        return stored
    from app.core.config import get_settings

    return get_settings().GEMINI_API_KEY or None
