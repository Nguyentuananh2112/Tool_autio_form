"""Một lần gọi Gemini trả JSON, có thử lại và model dự phòng — dùng chung cho mọi tính năng AI.

- 5xx (quá tải, VD 503 "high demand"): chờ tăng dần rồi thử lại.
- 429: thử lại 1 lần (có thể chỉ là giới hạn theo phút), sau đó để chuỗi key chuyển key khác.
- 404 / quá tải kéo dài: chuyển sang model dự phòng (VD gemini-2.5-flash đã bị ngừng cho key mới — BUG-015).
- 400/401/403: không thử lại; giữ mã để chuỗi key chuyển key.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import Any

from google.genai import errors, types

logger = logging.getLogger(__name__)

Sleep = Callable[[float], Awaitable[None]]

FALLBACK_MODELS = ("gemini-flash-latest", "gemini-flash-lite-latest")
SERVER_CODES = frozenset({500, 502, 503, 504})
QUOTA_RETRIES = 1


class GeminiCallError(RuntimeError):
    def __init__(self, message: str, code: int | None = None) -> None:
        super().__init__(message)
        self.code = code  # chuỗi key dựa vào mã này để quyết định chuyển key


def friendly_error(exc: errors.APIError) -> GeminiCallError:
    code = getattr(exc, "code", None)
    if code in (400, 401, 403):
        return GeminiCallError("Gemini API key không hợp lệ hoặc chưa được cấp quyền. Kiểm tra lại trong Cài đặt.", code)
    if code == 429:
        return GeminiCallError("Đã vượt giới hạn lượt gọi Gemini. Hãy thử lại sau ít phút.", code)
    if code in SERVER_CODES:
        return GeminiCallError("Gemini đang quá tải. Hãy thử lại sau ít phút.", code)
    return GeminiCallError(f"Gemini báo lỗi ({code}): {exc}", code)


def _models(model: str) -> list[str]:
    return list(dict.fromkeys([model, *FALLBACK_MODELS]))


async def generate_json(
    client: Any,
    model: str,
    prompt: str,
    schema: type,
    *,
    temperature: float,
    max_retries: int = 3,
    sleep: Sleep = asyncio.sleep,
) -> Any:
    """Trả về response thô của Gemini (đọc `.parsed` / `.text`)."""
    config = types.GenerateContentConfig(response_mime_type="application/json", response_schema=schema, temperature=temperature)
    last: errors.APIError | None = None
    for candidate in _models(model):
        for attempt in range(max_retries + 1):
            try:
                return await client.aio.models.generate_content(model=candidate, contents=prompt, config=config)
            except errors.APIError as exc:
                last = exc
                code = getattr(exc, "code", None)
                if code == 404:
                    logger.warning("Model %s không dùng được (404), thử model dự phòng", candidate)
                    break
                limit = min(max_retries, QUOTA_RETRIES) if code == 429 else max_retries
                if code in SERVER_CODES | {429} and attempt < limit:
                    wait = 2.0 ** (attempt + 1)
                    logger.warning("Gemini lỗi %s (%s), thử lại sau %.0f giây", code, candidate, wait)
                    await sleep(wait)
                    continue
                if code in SERVER_CODES:
                    break  # quá tải kéo dài → thử model dự phòng
                raise friendly_error(exc) from exc
    assert last is not None
    raise friendly_error(last) from last
