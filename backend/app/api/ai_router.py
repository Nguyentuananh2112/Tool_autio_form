from __future__ import annotations

from fastapi import APIRouter

from app.core.config import get_settings
from app.schemas.misc_api import GeneratePoolRequest, GeneratePoolResponse
from app.services.gemini_service import generate_answer_pool

router = APIRouter(prefix="/ai", tags=["ai"])


@router.post("/generate-pool", response_model=GeneratePoolResponse)
async def generate_pool(payload: GeneratePoolRequest) -> GeneratePoolResponse:
    answers = await generate_answer_pool(
        payload.question_title, payload.survey_context, payload.count, payload.persona,
        model=get_settings().GEMINI_MODEL,
    )
    return GeneratePoolResponse(answers=answers)
