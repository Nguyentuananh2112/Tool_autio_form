"""Sinh hàng loạt câu trả lời tự luận bằng Gemini (Batch Pre-generation, Mục 5.3 spec).

Không bao giờ gọi Gemini trong lúc gửi form: pool được sinh trước, lưu vào
`question_rules.cached_ai_pool`, rồi generator bốc từ pool (kèm Micro-Mutation).
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from google import genai
from pydantic import BaseModel, ValidationError

from app.services.gemini_call import GeminiCallError, Sleep, generate_json
from app.services.gemini_keys import run_with_keys

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "gemini-flash-latest"
DEFAULT_PERSONA = "Sinh viên đại học tại Việt Nam, trả lời tự nhiên, đa dạng độ dài từ 5 đến 25 từ"
MAX_PER_REQUEST = 50
MAX_POOL_SIZE = 500

# Lỗi Gemini đã dịch sang tiếng Việt (giữ mã HTTP để chuỗi key chuyển key) — xem gemini_call
GeminiServiceError = GeminiCallError


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


async def _generate_once(
    client: genai.Client, model: str, prompt: str, *, max_retries: int, sleep: Sleep
) -> list[str]:
    response = await generate_json(
        client, model, prompt, GeneratedAnswersResponse, temperature=0.9, max_retries=max_retries, sleep=sleep
    )
    return _parse_answers(response)


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

    async def with_client(active: genai.Client) -> list[str]:
        return await _pool_with_client(
            active, question_title, survey_context, sample_count, persona_hint, model, max_retries, sleep
        )

    if client is not None:
        return await with_client(client)
    if api_key:
        return await with_client(genai.Client(api_key=api_key.strip()))
    return await run_with_keys(with_client)


async def _pool_with_client(
    client: genai.Client, question_title: str, survey_context: str, sample_count: int,
    persona_hint: str, model: str, max_retries: int, sleep: Sleep,
) -> list[str]:
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
