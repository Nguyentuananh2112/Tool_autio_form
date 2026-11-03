"""API Soát logic (màn 11, SPEC-020): AI đọc câu hỏi → người dùng xem/sửa → soát mẫu thử → xác nhận."""

from __future__ import annotations

import uuid

from fastapi import APIRouter

from app.api.deps import DbSession
from app.schemas.logic_api import LogicReviewRequest, LogicReviewResult
from app.schemas.logic_schema import LogicMap
from app.services import logic_service

router = APIRouter(prefix="/forms/{form_id}/logic", tags=["logic"])


@router.get("", response_model=LogicMap | None)
async def read_logic(form_id: uuid.UUID, session: DbSession) -> LogicMap | None:
    return await logic_service.get_logic(session, form_id)


@router.post("/analyze", response_model=LogicMap)
async def analyze_logic(form_id: uuid.UUID, session: DbSession) -> LogicMap:
    """Lượt 1: Gemini đọc toàn bộ câu hỏi. Hết lượt AI → 429 code AI_KEYS_UNAVAILABLE."""
    return await logic_service.analyze(session, form_id)


@router.put("", response_model=LogicMap)
async def save_logic(form_id: uuid.UUID, payload: LogicMap, session: DbSession) -> LogicMap:
    return await logic_service.save_logic(session, form_id, payload)


@router.post("/review", response_model=LogicReviewResult)
async def review_logic(form_id: uuid.UUID, payload: LogicReviewRequest, session: DbSession) -> LogicReviewResult:
    """Lượt 2–3 trên mẫu thử trong máy (không gửi gì lên Google)."""
    return await logic_service.review(session, form_id, payload)
