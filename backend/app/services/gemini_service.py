"""Sinh hàng loạt câu trả lời tự luận bằng Gemini (Batch Pre-generation, Mục 5.3 spec).

Không bao giờ gọi Gemini trong lúc gửi form: pool được sinh trước, lưu vào
`question_rules.cached_ai_pool`, rồi generator bốc từ pool (kèm Micro-Mutation).
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Awaitable, Callable
from typing import Any

from google import genai
from google.genai import errors, types
from pydantic import BaseModel, ValidationError

from app.services.secret_store import resolve_gemini_api_key

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "gemini-2.5-flash"
DEFAULT_PERSONA = "Sinh viên đại học tại Việt Nam, trả lời tự nhiên, đa dạng độ dài từ 5 đến 25 từ"
MAX_PER_REQUEST = 50
MAX_POOL_SIZE = 500
RETRYABLE_CODES = frozenset({429, 500, 502, 503, 504})

Sleep = Callable[[float], Awaitable[None]]


class GeminiServiceError(RuntimeError):
    pass


class GeminiKeyMissingError(GeminiServiceError):
    pass


class GeneratedAnswersResponse(BaseModel):
    answers: list[str]


def build_prompt(
    question_title: str, survey_context: str, count: int, persona_hint: str, avoid: list[str]
) -> str:
    avoid_block = ""
    if avoid:
        sample = "\n".join(f"- {answer}" for answer in avoid[-30:])
        avoid_block = f"\nKHÔNG lặp lại các câu đã có sau:\n{sample}\n"
    return (
        f'Bạn đang tham gia điền một khảo sát có chủ đề: "{survey_context}".\n'
        f'Câu hỏi tự luận là: "{question_title}".\n'
        f"Phong cách người điền: {persona_hint}.\n"
        f"Hãy sinh ra đúng {count} câu trả lời hoàn toàn khác nhau, tự nhiên như người thật gõ "
        "(có câu ngắn gọn, câu chi tiết, không dùng văn phong liệt kê máy móc của AI)."
        f"{avoid_block}"
    )


def _parse_answers(response: Any) -> list[str]:
    parsed = getattr(response, "parsed", None)
    try:
        if isinstance(parsed, GeneratedAnswersResponse):
            return parsed.answers
        if isinstance(parsed, dict):
            return GeneratedAnswersResponse.model_validate(parsed).answers
        text = getattr(response, "text", None)
        if text:
            return GeneratedAnswersResponse.model_validate(json.loads(text)).answers
    except (ValidationError, json.JSONDecodeError) as exc:
        raise GeminiServiceError(f"Gemini trả về dữ liệu không đúng định dạng: {exc}") from exc
    raise GeminiServiceError("Gemini không trả về câu trả lời nào.")


def _friendly_api_error(exc: errors.APIError) -> GeminiServiceError:
    code = getattr(exc, "code", None)
    if code in (400, 401, 403):
        return GeminiServiceError("Gemini API key không hợp lệ hoặc chưa được cấp quyền. Kiểm tra lại trong Cài đặt.")
    if code == 429:
        return GeminiServiceError("Đã vượt giới hạn lượt gọi Gemini. Hãy thử lại sau ít phút.")
    return GeminiServiceError(f"Gemini báo lỗi ({code}): {exc}")


async def _generate_once(
    client: genai.Client, model: str, prompt: str, *, max_retries: int, sleep: Sleep
) -> list[str]:
    config = types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema=GeneratedAnswersResponse,
        temperature=0.9,
    )
    for attempt in range(max_retries + 1):
        try:
            response = await client.aio.models.generate_content(model=model, contents=prompt, config=config)
            return _parse_answers(response)
        except errors.APIError as exc:
            if getattr(exc, "code", None) in RETRYABLE_CODES and attempt < max_retries:
                wait = 2.0 ** (attempt + 1)
                logger.warning("Gemini lỗi %s, thử lại sau %.0f giây", exc.code, wait)
                await sleep(wait)
                continue
            raise _friendly_api_error(exc) from exc
    raise GeminiServiceError("Gemini không phản hồi sau nhiều lần thử.")


async def generate_answer_pool(
    question_title: str,
    survey_context: str,
    sample_count: int = 50,
    persona_hint: str = DEFAULT_PERSONA,
    *,
    api_key: str | None = None,
    client: genai.Client | None = None,
    model: str = DEFAULT_MODEL,
    max_retries: int = 3,
    sleep: Sleep = asyncio.sleep,
) -> list[str]:
    """Sinh `sample_count` câu trả lời khác nhau, chia lô tối đa 50 câu/lần gọi."""
    if not question_title.strip():
        raise GeminiServiceError("Thiếu nội dung câu hỏi.")
    if not 1 <= sample_count <= MAX_POOL_SIZE:
        raise GeminiServiceError(f"Số câu cần sinh phải trong khoảng 1–{MAX_POOL_SIZE}.")

    if client is None:
        key = resolve_gemini_api_key(api_key)
        if not key:
            raise GeminiKeyMissingError("Chưa có Gemini API key. Nhập key trong Cài đặt → Gemini AI.")
        client = genai.Client(api_key=key)

    answers: list[str] = []
    seen: set[str] = set()
    max_rounds = -(-sample_count // MAX_PER_REQUEST) + 2  # thêm 2 lượt bù câu trùng
    for _ in range(max_rounds):
        need = min(MAX_PER_REQUEST, sample_count - len(answers))
        if need <= 0:
            break
        prompt = build_prompt(question_title, survey_context or question_title, need, persona_hint, answers)
        for raw in await _generate_once(client, model, prompt, max_retries=max_retries, sleep=sleep):
            cleaned = " ".join(str(raw).split())
            key_norm = cleaned.casefold()
            if cleaned and key_norm not in seen:
                seen.add(key_norm)
                answers.append(cleaned)

    if not answers:
        raise GeminiServiceError("Gemini không sinh được câu trả lời nào.")
    return answers[:sample_count]
