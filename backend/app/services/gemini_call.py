"""Một lần gọi Gemini trả JSON, có thử lại và model dự phòng — dùng chung cho mọi tính năng AI.

- 503 "high demand" / quá CALL_TIMEOUT giây (model chậm có MODEL_TIMEOUTS riêng): chuyển NGAY sang model dự phòng.
  Cả lần gọi không quá TOTAL_BUDGET giây để giao diện không hết thời gian chờ trước. Đo thật 2026-11-03: khi Flash quá
  tải, mỗi lần gọi phải chờ 10–100 giây mới nhận 503 → thử lại cùng model làm người dùng chờ nhiều phút.
- 500/502/504 (trục trặc ngắn): chờ tăng dần rồi thử lại cùng model.
- 429: thử lại 1 lần (có thể chỉ là giới hạn theo phút), sau đó để chuỗi key chuyển key khác.
- 404: model bị ngừng (VD gemini-2.5-flash với key mới — BUG-015) → model dự phòng.
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

# Thứ tự gọi model: model chính đứng đầu, sau đó là các model dự phòng (RISK-013). Đo thật 2026-11-25:
# flash-latest / 3.1-flash-lite trả 503 liên tục, còn 3.5-flash-lite trả lời ~1,5 giây và 3.5-flash 16–27 giây.
# Model bị ngừng (404) được bỏ qua ngay nên ghi thêm tên cụ thể ở cuối không gây hại.
MODEL_CHAIN = (
    "gemini-3.5-flash-lite",
    "gemini-3.5-flash",
    "gemini-flash-latest",
    "gemini-flash-lite-latest",
    "gemini-3.1-flash-lite",
)
PRIMARY_MODEL = MODEL_CHAIN[0]
# Mọi model đều quá tải: chờ rồi đi lại cả chuỗi (đo thật: quá tải thường chỉ kéo dài vài chục giây)
OVERLOAD_ROUNDS = 2
OVERLOAD_PAUSE = 10.0
SERVER_CODES = frozenset({500, 502, 503, 504})
OVERLOAD_CODES = frozenset({503})
QUOTA_RETRIES = 1
CALL_TIMEOUT = 45.0
# Model chậm nhưng vẫn trả lời: đo 2026-11-25, 3.5-flash đọc form 53 câu mất 48 giây (> CALL_TIMEOUT)
MODEL_TIMEOUTS = {"gemini-3.5-flash": 90.0}
# Tổng thời gian tối đa của một lần generate_json, nhỏ hơn thời gian giao diện chờ (180–300 giây)
TOTAL_BUDGET = 150.0
OVERLOADED_MESSAGE = "Gemini đang quá tải. Hãy thử lại sau ít phút."


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
        return GeminiCallError(OVERLOADED_MESSAGE, code)
    return GeminiCallError(f"Gemini báo lỗi ({code}): {exc}", code)


def _models(model: str) -> list[str]:
    """Model được chọn đứng đầu, rồi đủ chuỗi MODEL_CHAIN (bỏ trùng)."""
    return list(dict.fromkeys([model, *MODEL_CHAIN]))


async def generate_json(
    client: Any,
    model: str,
    prompt: str,
    schema: type,
    *,
    temperature: float,
    max_retries: int = 3,
    sleep: Sleep = asyncio.sleep,
    timeout: float = CALL_TIMEOUT,
    budget: float = TOTAL_BUDGET,
) -> Any:
    """Trả về response thô của Gemini (đọc `.parsed` / `.text`)."""
    config = types.GenerateContentConfig(response_mime_type="application/json", response_schema=schema, temperature=temperature)
    deadline = asyncio.get_running_loop().time() + budget
    last: GeminiCallError | None = None
    for round_index in range(OVERLOAD_ROUNDS):
        if round_index:
            if _remaining(deadline) <= OVERLOAD_PAUSE:
                break
            logger.warning("Mọi model Gemini đều quá tải, chờ %.0f giây rồi thử lại cả chuỗi", OVERLOAD_PAUSE)
            await sleep(OVERLOAD_PAUSE)
        response, last = await _try_models(client, model, prompt, config, max_retries, sleep, timeout, deadline)
        if response is not None:
            return response
    raise last or GeminiCallError(OVERLOADED_MESSAGE, 503)


def _remaining(deadline: float) -> float:
    return deadline - asyncio.get_running_loop().time()


async def _try_models(
    client: Any, model: str, prompt: str, config: Any, max_retries: int, sleep: Sleep, timeout: float, deadline: float
) -> tuple[Any, GeminiCallError | None]:
    """Một lượt qua chuỗi model. Trả (response, None) khi thành công, (None, lỗi cuối) khi mọi model quá tải
    hoặc đã hết tổng thời gian cho phép."""
    last: GeminiCallError | None = None
    for candidate in _models(model):
        for attempt in range(max_retries + 1):
            wait_limit = min(MODEL_TIMEOUTS.get(candidate, timeout), _remaining(deadline))
            if wait_limit <= 0:
                logger.warning("Hết tổng thời gian cho phép, dừng gọi Gemini")
                return None, last or GeminiCallError(OVERLOADED_MESSAGE, 503)
            try:
                return await asyncio.wait_for(
                    client.aio.models.generate_content(model=candidate, contents=prompt, config=config), wait_limit
                ), None
            except TimeoutError:
                logger.warning("Gemini (%s) không trả lời sau %.0f giây, chuyển model dự phòng", candidate, wait_limit)
                last = GeminiCallError(OVERLOADED_MESSAGE, 503)
                break
            except errors.APIError as exc:
                last = friendly_error(exc)
                code = getattr(exc, "code", None)
                if code == 404 or code in OVERLOAD_CODES:
                    logger.warning("Model %s lỗi %s, chuyển model dự phòng", candidate, code)
                    break
                limit = min(max_retries, QUOTA_RETRIES) if code == 429 else max_retries
                if code in SERVER_CODES | {429} and attempt < limit:
                    wait = 2.0 ** (attempt + 1)
                    logger.warning("Gemini lỗi %s (%s), thử lại sau %.0f giây", code, candidate, wait)
                    await sleep(wait)
                    continue
                if code in SERVER_CODES:
                    break
                raise last from exc
    return None, last
