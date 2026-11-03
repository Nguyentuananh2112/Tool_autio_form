"""Phân loại câu mẫu tự luận thành tích cực / trung lập / tiêu cực (để người chấm cao nhận câu khen)."""

from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, Field, ValidationError

from app.schemas.logic_schema import TextSentiment
from app.services.gemini_call import GeminiCallError as GeminiServiceError
from app.services.gemini_call import generate_json

MAX_TEXTS_PER_CALL = 200


class AiSentiment(BaseModel):
    index: int
    sentiment: str


class AiSentimentResponse(BaseModel):
    labels: list[AiSentiment] = Field(default_factory=list)


def build_prompt(question_title: str, subject: str, texts: list[str]) -> str:
    numbered = "\n".join(f"{i}. {text}" for i, text in enumerate(texts))
    return (
        f'Câu hỏi khảo sát: "{question_title}" (về: {subject}).\n'
        "Phân loại từng câu trả lời dưới đây theo thái độ của người viết với đối tượng: "
        "POSITIVE (khen, hài lòng), NEUTRAL (trung tính, chỉ mô tả, góp ý nhẹ), NEGATIVE (chê, không hài lòng, phàn nàn).\n"
        "Trả về đúng chỉ số (index) của mỗi câu.\n"
        f"{numbered}"
    )


def _parse(response: Any) -> AiSentimentResponse:
    parsed = getattr(response, "parsed", None)
    try:
        if isinstance(parsed, AiSentimentResponse):
            return parsed
        if isinstance(parsed, dict):
            return AiSentimentResponse.model_validate(parsed)
        text = getattr(response, "text", None)
        if text:
            return AiSentimentResponse.model_validate(json.loads(text))
    except (ValidationError, json.JSONDecodeError) as exc:
        raise GeminiServiceError(f"Gemini trả về phân loại không đúng định dạng: {exc}") from exc
    raise GeminiServiceError("Gemini không trả về phân loại câu trả lời.")


async def classify_texts(
    client: Any, question_title: str, subject: str, texts: list[str], model: str
) -> dict[str, TextSentiment]:
    """Câu không được AI trả về (hoặc nhãn lạ) coi là trung lập."""
    labels: dict[str, TextSentiment] = {}
    for start in range(0, len(texts), MAX_TEXTS_PER_CALL):
        chunk = texts[start : start + MAX_TEXTS_PER_CALL]
        response = await generate_json(
            client, model, build_prompt(question_title, subject, chunk), AiSentimentResponse, temperature=0.0
        )
        for item in _parse(response).labels:
            if 0 <= item.index < len(chunk):
                try:
                    labels[chunk[item.index]] = TextSentiment(item.sentiment.strip().upper())
                except ValueError:
                    continue
    return {text: labels.get(text, TextSentiment.NEUTRAL) for text in texts}
