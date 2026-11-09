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
from app.services.humanize.ai_cleanup import clean_ai_text

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "gemini-flash-latest"
DEFAULT_PERSONA = "người Việt Nam bình thường, đủ độ tuổi và nghề nghiệp, phần lớn trả lời trên điện thoại"
MAX_PER_REQUEST = 50
MAX_POOL_SIZE = 500

# Lỗi Gemini đã dịch sang tiếng Việt (giữ mã HTTP để chuỗi key chuyển key) — xem gemini_call
GeminiServiceError = GeminiCallError


class GeminiKeyMissingError(GeminiServiceError):
    pass


class GeneratedAnswersResponse(BaseModel):
    answers: list[str]


# Dấu hiệu văn AI mà người trả lời khảo sát gần như không dùng (SPEC-022)
AI_PHRASES = (
    "nâng cao trải nghiệm", "tối ưu hóa", "đa dạng hóa", "vượt trội", "hài lòng tuyệt đối", "điểm cộng lớn",
    "góp phần", "mang lại giá trị", "đáp ứng tốt nhu cầu", "không ngừng cải thiện", "một cách hiệu quả",
)


def build_prompt(
    question_title: str, survey_context: str, count: int, persona_hint: str, avoid: list[str]
) -> str:
    """Câu lệnh để Gemini viết như NHIỀU người thật khác nhau, không như một trợ lý AI (SPEC-022).

    Tỷ lệ độ dài / câu qua loa theo nghiên cứu câu hỏi mở (Pew: trả lời trên điện thoại ~80 ký tự;
    DISQO, GESIS: "không có / không biết" là câu trả lời hợp lệ, hay gặp). Chữ hoa, dấu câu, viết tắt,
    gõ không dấu do app tự thêm theo kiểu gõ của từng người (services/humanize) nên ở đây chỉ cần nội dung.
    """
    avoid_block = ""
    if avoid:
        sample = "\n".join(f"- {answer}" for answer in avoid[-30:])
        avoid_block = f"\nKHÔNG lặp lại hay viết na ná các câu đã có:\n{sample}\n"
    banned = ", ".join(f'"{phrase}"' for phrase in AI_PHRASES)
    rules = [
        "Độ dài rất khác nhau: khoảng 1/3 chỉ 1–5 từ (VD 'giao nhanh', 'giá hơi cao'), khoảng 2/5 từ 6–15 từ, "
        "phần còn lại dài hơn, vài câu kể chuyện riêng cụ thể (VD 'lần trước đặt sách bị móp góc mà đổi trả lâu').",
        "Khoảng 1/8 trả lời qua loa / không có ý kiến như người thật vẫn hay làm "
        "(VD 'không có gì', 'chưa nghĩ ra', 'như giờ là ổn rồi', 'bình thường').",
        "Quan điểm khác nhau: có người khen, có người chê thẳng, có người trung lập; mỗi người chỉ nói 1–2 ý họ quan tâm.",
        "Văn nói đời thường như nhắn tin: được dùng 'thì', 'kiểu', 'cũng', 'hơi', 'chắc', 'nói chung', câu cụt, "
        "không cần đủ chủ ngữ vị ngữ.",
        "TUYỆT ĐỐI KHÔNG: gạch đầu dòng, đánh số, ngoặc kép, gạch ngang dài, chấm than; không mở đầu bằng "
        "'Theo tôi' / 'Tôi nghĩ rằng'; không nhắc lại câu hỏi; không viết như chuyên gia hay quảng cáo; "
        f"không dùng các cụm sáo rỗng: {banned}.",
        "Viết tiếng Việt có dấu bình thường (app tự xử lý chữ hoa, dấu câu, viết tắt).",
        "Các ví dụ trong ngoặc chỉ để hiểu ý — KHÔNG chép lại nguyên văn; câu nào cũng phải bám đúng nội dung câu hỏi.",
    ]
    bullet_list = "\n".join(f"- {rule}" for rule in rules)
    return (
        f'Khảo sát chủ đề: "{survey_context}".\n'
        f'Câu hỏi tự luận: "{question_title}".\n'
        f"Hãy viết đúng {count} câu trả lời của {count} NGƯỜI KHÁC NHAU ({persona_hint}), "
        "như họ thật sự gõ vào ô trả lời:\n"
        f"{bullet_list}"
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
            cleaned = clean_ai_text(str(raw))
            key_norm = cleaned.casefold()
            if cleaned and key_norm not in seen:
                seen.add(key_norm)
                answers.append(cleaned)

    if not answers:
        raise GeminiServiceError("Gemini không sinh được câu trả lời nào.")
    return answers[:sample_count]
