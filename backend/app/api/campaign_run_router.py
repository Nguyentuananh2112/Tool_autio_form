"""Điều khiển chạy chiến dịch: bắt đầu / tạm dừng / tiếp tục / dừng, nhật ký, xuất dữ liệu, gửi thử."""

from __future__ import annotations

import asyncio
import uuid
from typing import Literal

from fastapi import APIRouter, Query, Response
from sqlalchemy import select

from app.api.deps import DbSession, RunnerKwargs
from app.api.errors import ConflictError
from sqlalchemy.orm import selectinload

from app.models import Campaign, CampaignStatus, SubmissionLog
from app.schemas.campaign_api import (
    CampaignRead,
    CampaignSummary,
    RetryFailedResponse,
    SubmissionLogRead,
    TrialSubmitRequest,
    TrialSubmitResponse,
)
from app.services import campaign_service, export_service
from app.services.campaign_summary import build_summary
from app.services.distribution_service import QuestionDistribution, build_distributions
from app.services.logic_service import stored_logic
from app.services.spss_generator import SurveyDataGenerator, build_payload_tuples
from app.workers.campaign_control import registry
from app.workers.campaign_runner import USER_PAUSE_REASON, default_http_factory, start_campaign
from app.workers.simulated_submitter import SimulatedSubmitter
from app.workers.submission_types import payload_to_json

router = APIRouter(prefix="/campaigns", tags=["campaign-run"])


async def _read(session: DbSession, campaign_id: uuid.UUID) -> CampaignRead:
    session.expire_all()
    return campaign_service.to_read(await campaign_service.get_campaign(session, campaign_id))


@router.post("/{campaign_id}/start", response_model=CampaignRead, status_code=202)
async def start(campaign_id: uuid.UUID, session: DbSession, runner_kwargs: RunnerKwargs) -> CampaignRead:
    campaign = await campaign_service.get_campaign(session, campaign_id)
    if campaign.status == CampaignStatus.COMPLETED:
        raise ConflictError("Chiến dịch đã hoàn thành. Hãy tạo chiến dịch mới để gửi thêm.")
    start_campaign(campaign_id, **runner_kwargs)
    return await _read(session, campaign_id)


@router.get("/{campaign_id}/summary", response_model=CampaignSummary)
async def summary(campaign_id: uuid.UUID, session: DbSession) -> CampaignSummary:
    """Thông báo kết thúc (màn 13): số thành công / lỗi, thời gian, lỗi gom theo lý do kèm cách xử lý."""
    session.expire_all()
    campaign = await campaign_service.get_campaign(session, campaign_id)
    logs = (await session.execute(select(SubmissionLog).where(SubmissionLog.campaign_id == campaign_id))).scalars().all()
    return build_summary(campaign, logs)


@router.post("/{campaign_id}/retry-failed", response_model=RetryFailedResponse, status_code=202)
async def retry_failed(campaign_id: uuid.UUID, session: DbSession, runner_kwargs: RunnerKwargs) -> RetryFailedResponse:
    """Gửi lại đúng các phản hồi đã lỗi (nội dung giữ nguyên), không gửi trùng phản hồi đã thành công."""
    retried = await campaign_service.reset_failed(session, campaign_id)
    start_campaign(campaign_id, **runner_kwargs)
    return RetryFailedResponse(retried=retried, campaign=await _read(session, campaign_id))


@router.post("/{campaign_id}/pause", response_model=CampaignRead)
async def pause(campaign_id: uuid.UUID, session: DbSession) -> CampaignRead:
    campaign = await campaign_service.get_campaign(session, campaign_id)
    control = registry.get(str(campaign_id))
    if control and control.is_active:
        control.pause(USER_PAUSE_REASON)
    elif campaign.status == CampaignStatus.RUNNING:
        await campaign_service.set_status(session, campaign_id, CampaignStatus.PAUSED)
    else:
        raise ConflictError("Chiến dịch không chạy nên không thể tạm dừng.")
    return await _read(session, campaign_id)


@router.post("/{campaign_id}/resume", response_model=CampaignRead)
async def resume(campaign_id: uuid.UUID, session: DbSession, runner_kwargs: RunnerKwargs) -> CampaignRead:
    campaign = await campaign_service.get_campaign(session, campaign_id)
    control = registry.get(str(campaign_id))
    if control and control.is_active:
        if not control.is_paused:
            raise ConflictError("Chiến dịch đang chạy.")
        control.resume()
    elif campaign.status in (CampaignStatus.PAUSED, CampaignStatus.FAILED, CampaignStatus.IDLE):
        # App đã khởi động lại: tạo runner mới, nó tự bỏ qua các phản hồi đã gửi
        start_campaign(campaign_id, **runner_kwargs)
    else:
        raise ConflictError("Chiến dịch đã hoàn thành.")
    return await _read(session, campaign_id)


@router.post("/{campaign_id}/stop", response_model=CampaignRead)
async def stop(campaign_id: uuid.UUID, session: DbSession) -> CampaignRead:
    await campaign_service.get_campaign(session, campaign_id)
    control = registry.get(str(campaign_id))
    if not (control and control.is_active):
        raise ConflictError("Chiến dịch không chạy.")
    control.cancel()
    if control.task is not None:
        await asyncio.wait({control.task}, timeout=15)
    return await _read(session, campaign_id)


@router.get("/{campaign_id}/logs", response_model=list[SubmissionLogRead])
async def logs(
    campaign_id: uuid.UUID,
    session: DbSession,
    limit: int = Query(default=100, ge=1, le=1000),
    before_id: int | None = Query(default=None, ge=1),
) -> list[SubmissionLogRead]:
    await campaign_service.get_campaign(session, campaign_id)
    query = select(SubmissionLog).where(SubmissionLog.campaign_id == campaign_id)
    if before_id is not None:
        query = query.where(SubmissionLog.id < before_id)
    result = await session.execute(query.order_by(SubmissionLog.id.desc()).limit(limit))
    return [
        SubmissionLogRead.model_validate(log).model_copy(update={"page_history": log.payload_sent.get("pageHistory")})
        for log in result.scalars().all()
    ]


@router.get("/{campaign_id}/distribution", response_model=list[QuestionDistribution])
async def distribution(campaign_id: uuid.UUID, session: DbSession) -> list[QuestionDistribution]:
    campaign = await session.get(
        Campaign, campaign_id, options=[selectinload(Campaign.form), selectinload(Campaign.question_rules)],
        populate_existing=True,
    )
    if campaign is None:
        raise campaign_service.NotFoundError("Không tìm thấy chiến dịch.")
    result = await session.execute(select(SubmissionLog).where(SubmissionLog.campaign_id == campaign_id))
    logs = list(result.scalars().all())
    structure = campaign_service.structure_of(campaign.form)
    return await asyncio.to_thread(build_distributions, structure, list(campaign.question_rules), logs)


@router.get("/{campaign_id}/export")
async def export(
    campaign_id: uuid.UUID, session: DbSession, format: Literal["xlsx", "csv"] = "xlsx"
) -> Response:
    campaign = await campaign_service.get_campaign(session, campaign_id)
    structure = campaign_service.structure_of(campaign.form)
    result = await session.execute(
        select(SubmissionLog).where(SubmissionLog.campaign_id == campaign_id).order_by(SubmissionLog.sequence_number)
    )
    rows = list(result.scalars().all())

    def build() -> bytes:
        text_frame = export_service.build_text_frame(structure, rows)
        if format == "csv":
            return export_service.to_csv_bytes(text_frame)
        return export_service.to_xlsx_bytes(text_frame, export_service.build_numeric_frame(structure, rows))

    content = await asyncio.to_thread(build)
    media = "text/csv" if format == "csv" else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    return Response(
        content=content, media_type=media,
        headers={"Content-Disposition": f'attachment; filename="campaign-{campaign_id}.{format}"'},
    )


@router.post("/trial-submit", response_model=TrialSubmitResponse)
async def trial_submit(payload: TrialSubmitRequest, session: DbSession, runner_kwargs: RunnerKwargs) -> TrialSubmitResponse:
    """Nút "Gửi thử 1 phản hồi": sinh 1 phản hồi theo cấu hình hiện tại và gửi thật lên form."""
    form = await campaign_service.get_form(session, payload.form_id)
    structure = campaign_service.structure_of(form)
    # Có bản đồ logic (kể cả chưa xác nhận) thì gửi thử cũng theo logic, giống lúc chạy thật
    generator = SurveyDataGenerator(structure, payload.rules, payload.spss_groups, logic=stored_logic(form), humanize=True)
    response = (await asyncio.to_thread(generator.generate, 1))[0]
    tuples = build_payload_tuples(response, structure.fbzx)
    if form.is_demo or payload.dry_run:
        submitter = SimulatedSubmitter(delay=0)
    else:
        submitter = runner_kwargs.get("http_factory", default_http_factory)(payload.proxy)
    try:
        outcome = await submitter.submit(structure, tuples)
    finally:
        await submitter.aclose()
    return TrialSubmitResponse(
        success=outcome.ok, outcome=outcome.kind.value, status_code=outcome.status_code,
        engine_used=outcome.engine.value, error=outcome.error,
        page_history=response.page_history_str, payload_sent=payload_to_json(tuples),
    )
