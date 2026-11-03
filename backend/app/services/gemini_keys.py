"""Chuỗi API key Gemini (SPEC-020): key riêng người dùng → key chung → key dự phòng.

Key nào hết lượt (429) hoặc không hợp lệ thì tự chuyển key sau. Hết cả → `AiKeysUnavailableError`
kèm trạng thái từng key để giao diện hiện hộp thoại "Hết lượt AI — dán key của bạn".
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, TypeVar

import httpx
from google import genai

from app.core.build_secrets import embedded_keys
from app.services import secret_store

logger = logging.getLogger(__name__)

T = TypeVar("T")
ClientFactory = Callable[[str], Any]

QUOTA_CODES = frozenset({429})
INVALID_CODES = frozenset({400, 401, 403})


class KeySlot(StrEnum):
    USER = "USER"  # key người dùng dán (kho bảo mật Windows)
    SHARED = "SHARED"  # key chung nhúng lúc build (khi phát triển: GEMINI_API_KEY trong .env)
    BACKUP = "BACKUP"  # key dự phòng nhúng lúc build


class KeyState(StrEnum):
    MISSING = "MISSING"
    EXHAUSTED = "EXHAUSTED"
    INVALID = "INVALID"
    OK = "OK"


@dataclass(frozen=True, slots=True)
class KeyAttempt:
    slot: KeySlot
    state: KeyState


class AiKeysUnavailableError(RuntimeError):
    """Không key nào dùng được (chưa có / hết lượt / không hợp lệ)."""

    def __init__(self, attempts: list[KeyAttempt]) -> None:
        self.attempts = attempts
        has_any = any(a.state != KeyState.MISSING for a in attempts)
        super().__init__(
            "Hết lượt AI — dán API key Gemini của bạn để tiếp tục."
            if has_any
            else "Chưa có API key Gemini — dán key của bạn để tiếp tục."
        )


class AiUnreachableError(RuntimeError):
    """Không kết nối được Gemini (mất mạng / bị chặn) — đổi key không giúp được."""


def candidate_keys() -> list[tuple[KeySlot, str | None]]:
    from app.core.config import get_settings

    shared, backup = embedded_keys()
    return [
        (KeySlot.USER, secret_store.get_gemini_api_key()),
        (KeySlot.SHARED, shared or get_settings().GEMINI_API_KEY or None),
        (KeySlot.BACKUP, backup),
    ]


def _error_code(exc: BaseException) -> int | None:
    code = getattr(exc, "code", None)
    return code if isinstance(code, int) else None


def _is_network(exc: BaseException) -> bool:
    return isinstance(exc, (httpx.TransportError, ConnectionError, TimeoutError, OSError))


async def run_with_keys(
    call: Callable[[Any], Awaitable[T]],
    *,
    keys: list[tuple[KeySlot, str | None]] | None = None,
    client_factory: ClientFactory | None = None,
) -> T:
    """Chạy `call(client)` với lần lượt từng key cho tới khi thành công."""
    factory = client_factory or (lambda key: genai.Client(api_key=key))
    attempts: list[KeyAttempt] = []
    seen: set[str] = set()
    for slot, key in keys if keys is not None else candidate_keys():
        if not key or key in seen:
            attempts.append(KeyAttempt(slot, KeyState.MISSING))
            continue
        seen.add(key)
        try:
            return await call(factory(key))
        except Exception as exc:  # APIError của google-genai hoặc lỗi đã dịch có thuộc tính `code`
            code = _error_code(exc)
            if code in QUOTA_CODES:
                logger.warning("Key Gemini %s hết lượt, chuyển key sau", slot.value)
                attempts.append(KeyAttempt(slot, KeyState.EXHAUSTED))
                continue
            if code in INVALID_CODES:
                logger.warning("Key Gemini %s không hợp lệ (%s), chuyển key sau", slot.value, code)
                attempts.append(KeyAttempt(slot, KeyState.INVALID))
                continue
            if code is None and _is_network(exc):
                raise AiUnreachableError("Không kết nối được Gemini. Kiểm tra mạng rồi thử lại.") from exc
            raise
    raise AiKeysUnavailableError(attempts)
