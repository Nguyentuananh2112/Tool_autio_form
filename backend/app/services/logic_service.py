"""Nghiệp vụ Soát logic dùng cho router: đọc câu hỏi bằng AI, lưu / xác nhận, chạy soát trên mẫu thử."""

from __future__ import annotations

import asyncio
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models import Form
from app.schemas.campaign_schema import QuestionRuleConfig
from app.schemas.logic_api import LogicReviewRequest, LogicReviewResult
from app.schemas.logic_schema import LogicMap
from app.services.campaign_service import get_form, structure_of
from app.services.demo_form import build_demo_logic
from app.services.gemini_keys import run_with_keys
from app.services.logic.ai_reader import read_form_logic
from app.services.logic.review import review_logic
from app.services.logic.text_classifier import classify_texts
from app.services.logic.validation import LogicMapInvalidError, ensure_valid


def stored_logic(form: Form) -> LogicMap | None:
    return LogicMap.model_validate(form.logic_map) if form.logic_map else None


async def _store(session: AsyncSession, form: Form, logic: LogicMap) -> LogicMap:
    form.logic_map = logic.model_dump(mode="json")
    await session.commit()
    return logic


async def get_logic(session: AsyncSession, form_id: uuid.UUID) -> LogicMap | None:
    return stored_logic(await get_form(session, form_id))


async def analyze(session: AsyncSession, form_id: uuid.UUID) -> LogicMap:
    """Lượt 1. Kết quả mới luôn ở trạng thái chưa xác nhận."""
    form = await get_form(session, form_id)
    structure = structure_of(form)
    if form.is_demo:
        logic = build_demo_logic()
    else:
        model = get_settings().GEMINI_MODEL
        logic = await run_with_keys(lambda client: read_form_logic(client, structure, model))
    previous = stored_logic(form)
    if previous is not None:
        logic.consistency = previous.consistency  # giữ lựa chọn độ đồng đều của người dùng
    return await _store(session, form, logic)


async def save_logic(session: AsyncSession, form_id: uuid.UUID, logic: LogicMap) -> LogicMap:
    form = await get_form(session, form_id)
    ensure_valid(structure_of(form), logic)
    return await _store(session, form, logic)


async def _label_texts(logic: LogicMap, rules: list[QuestionRuleConfig], structure_titles: dict[str, str]) -> bool:
    """Phân loại cảm xúc câu mẫu tự luận còn thiếu nhãn. Trả True nếu có thay đổi."""
    pools = {rule.entry_id: rule.text_pool for rule in rules if rule.text_pool}
    names = {group.group_id: group.name for group in logic.attitude_groups}
    changed = False
    model = get_settings().GEMINI_MODEL
    for text in logic.text_attitudes:
        missing = [t for t in pools.get(text.entry_id, []) if t not in text.labels]
        if not missing:
            continue
        title, subject = structure_titles.get(text.entry_id, ""), names.get(text.group_id, "")
        labels = await run_with_keys(lambda client, m=missing, ti=title, su=subject: classify_texts(client, ti, su, m, model))
        text.labels.update(labels)
        changed = True
    return changed


async def review(session: AsyncSession, form_id: uuid.UUID, payload: LogicReviewRequest) -> LogicReviewResult:
    """Lượt 2–3 trên mẫu thử (không gửi gì lên Google)."""
    form = await get_form(session, form_id)
    structure = structure_of(form)
    logic = payload.logic or stored_logic(form)
    if logic is None:
        raise LogicMapInvalidError(["Form chưa được đọc câu hỏi. Bấm \"Soát lại từ đầu\" để AI đọc form."])
    ensure_valid(structure, logic)
    titles = {q.entry_id: q.title for q in structure.questions}
    if await _label_texts(logic, payload.rules, titles) or payload.logic is not None:
        await _store(session, form, logic)
    return await asyncio.to_thread(
        review_logic, structure, payload.rules, payload.spss_groups, logic, payload.sample_size
    )
