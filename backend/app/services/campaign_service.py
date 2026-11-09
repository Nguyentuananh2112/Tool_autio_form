"""Nghiệp vụ chiến dịch dùng chung cho các router: tạo, đọc, khôi phục sau khi app tắt đột ngột."""

from __future__ import annotations

import asyncio
import uuid

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Campaign, CampaignStatus, DataSource, Form, QuestionRule, SubmissionLog
from app.schemas.campaign_api import CampaignCreate, CampaignRead
from app.schemas.campaign_schema import ScheduleConfig
from app.schemas.form_schema import ParsedFormStructure
from app.schemas.logic_schema import LogicMap
from app.services.excel_mapper import records_to_responses
from app.services.spss_generator import GeneratorConfigError, SurveyDataGenerator
from app.workers.campaign_control import registry

INTERRUPTED_REASON = "Ứng dụng đã tắt khi chiến dịch đang chạy. Bấm Tiếp tục để gửi phần còn lại."


class NotFoundError(LookupError):
    pass


class InvalidCampaignError(ValueError):
    def __init__(self, message: str, errors: list[str] | None = None) -> None:
        self.errors = errors or []
        super().__init__(message)


def structure_of(form: Form) -> ParsedFormStructure:
    return ParsedFormStructure.model_validate(form.parsed_structure)


async def get_form(session: AsyncSession, form_id: uuid.UUID) -> Form:
    form = await session.get(Form, form_id)
    if form is None:
        raise NotFoundError("Không tìm thấy form.")
    return form


async def get_campaign(session: AsyncSession, campaign_id: uuid.UUID) -> Campaign:
    # populate_existing: object có sẵn trong session (vừa tạo) chưa nạp `form` → nạp lại thay vì lazy-load
    campaign = await session.get(
        Campaign, campaign_id, options=[selectinload(Campaign.form)], populate_existing=True
    )
    if campaign is None:
        raise NotFoundError("Không tìm thấy chiến dịch.")
    return campaign


def to_read(campaign: Campaign) -> CampaignRead:
    control = registry.get(str(campaign.id))
    return CampaignRead(
        id=campaign.id,
        form_id=campaign.form_id,
        form_title=campaign.form.title,
        name=campaign.name,
        data_source=campaign.data_source,
        status=campaign.status,
        total_target=campaign.total_target,
        completed_count=campaign.completed_count,
        failed_count=campaign.failed_count,
        schedule=ScheduleConfig.model_validate(campaign.schedule_config),
        proxy=campaign.proxy_list[0] if campaign.proxy_list else None,
        use_playwright_fallback=campaign.use_playwright_fallback,
        created_at=campaign.created_at,
        is_active=bool(control and control.is_active),
        pause_reason=control.pause_reason if control else None,
        status_reason=campaign.status_reason,
        auto_paused=is_auto_paused(campaign.status, (control.pause_reason if control and control.is_paused else None) or campaign.status_reason),
    )


def is_auto_paused(status: str, reason: str | None) -> bool:
    """App TỰ tạm dừng (Google giới hạn / từ chối liên tiếp) — khác người dùng bấm Tạm dừng / Dừng / tắt app."""
    from app.workers.campaign_runner import USER_PAUSE_REASON, USER_STOP_REASON

    return status == CampaignStatus.PAUSED.value and bool(reason) and reason not in {
        USER_PAUSE_REASON, USER_STOP_REASON, INTERRUPTED_REASON,
    }


async def _resolve_target(payload: CampaignCreate, structure: ParsedFormStructure) -> int:
    if payload.data_source == DataSource.PROBABILITY:
        generator = SurveyDataGenerator(structure, payload.rules, payload.spss_groups)
        try:
            await asyncio.to_thread(generator.validate)
        except GeneratorConfigError as exc:
            raise InvalidCampaignError("Cấu hình câu trả lời chưa hợp lệ.", exc.errors) from exc
        assert payload.total_target is not None
        return payload.total_target

    _, report = await asyncio.to_thread(records_to_responses, payload.excel_records or [], structure)
    if report.valid_rows == 0:
        raise InvalidCampaignError(
            "File không có dòng hợp lệ nào.", [issue.message for issue in report.issues[:20]]
        )
    return min(payload.total_target or report.valid_rows, report.valid_rows)


LOGIC_NOT_CONFIRMED = "Chưa soát logic: mở bước Soát logic, xem lại rồi bấm Xác nhận trước khi chạy."


def _confirmed_logic(form: Form, payload: CampaignCreate) -> LogicMap | None:
    """Quy tắc 6: dữ liệu tự sinh chỉ được chạy sau khi đã soát logic. Dữ liệu Excel là dữ liệu thật → giữ nguyên."""
    if payload.data_source != DataSource.PROBABILITY:
        return None
    logic = LogicMap.model_validate(form.logic_map) if form.logic_map else None
    if logic is None or not logic.confirmed:
        raise InvalidCampaignError(LOGIC_NOT_CONFIRMED)
    return logic


async def create_campaign(session: AsyncSession, payload: CampaignCreate) -> Campaign:
    form = await get_form(session, payload.form_id)
    total = await _resolve_target(payload, structure_of(form))
    logic = _confirmed_logic(form, payload)
    campaign = Campaign(
        form_id=form.id,
        name=payload.name.strip(),
        data_source=payload.data_source.value,
        total_target=total,
        schedule_config=payload.schedule.model_dump(mode="json"),
        spss_groups=[group.model_dump(mode="json") for group in payload.spss_groups],
        excel_data=payload.excel_records if payload.data_source == DataSource.EXCEL else None,
        logic_map=logic.model_dump(mode="json") if logic else None,
        proxy_list=[payload.proxy.strip()] if payload.proxy and payload.proxy.strip() else [],
        use_playwright_fallback=payload.use_playwright_fallback,
    )
    for rule in payload.rules:
        campaign.question_rules.append(QuestionRule(
            entry_id=rule.entry_id,
            question_type=rule.question_type,
            # Pool câu tự luận lưu riêng ở cached_ai_pool (Mục 4 spec), loader ghép lại khi chạy
            config_json=rule.model_dump(mode="json", exclude={"text_pool"}),
            cached_ai_pool=rule.text_pool,
        ))
    session.add(campaign)
    await session.commit()
    return await get_campaign(session, campaign.id)


async def list_campaigns(session: AsyncSession) -> list[Campaign]:
    result = await session.execute(
        select(Campaign).options(selectinload(Campaign.form)).order_by(Campaign.created_at.desc())
    )
    return list(result.scalars().all())


async def set_status(session: AsyncSession, campaign_id: uuid.UUID, status: CampaignStatus) -> None:
    await session.execute(update(Campaign).where(Campaign.id == campaign_id).values(status=status.value))
    await session.commit()


async def recover_interrupted(session: AsyncSession) -> int:
    """Khi khởi động: chiến dịch còn RUNNING nghĩa là app đã tắt giữa chừng → chuyển sang PAUSED."""
    result = await session.execute(
        update(Campaign).where(Campaign.status == CampaignStatus.RUNNING.value)
        .values(status=CampaignStatus.PAUSED.value, status_reason=INTERRUPTED_REASON)
    )
    await session.commit()
    return result.rowcount or 0


async def reset_failed(session: AsyncSession, campaign_id: uuid.UUID) -> int:
    """Chuẩn bị "Gửi lại phản hồi lỗi": xoá nhật ký lỗi để các phản hồi đó quay lại hàng đợi.

    Bộ sinh dùng seed cố định theo chiến dịch (+ bản đồ logic đã chụp) nên phản hồi gửi lại GIỐNG HỆT
    phản hồi đã lỗi; dữ liệu Excel cũng đọc lại đúng các dòng cũ.
    """
    campaign = await get_campaign(session, campaign_id)
    control = registry.get(str(campaign_id))
    if control and control.is_active:
        raise InvalidCampaignError("Chiến dịch đang chạy. Hãy chờ chạy xong hoặc dừng hẳn rồi gửi lại.")
    deleted = await session.execute(
        delete(SubmissionLog).where(SubmissionLog.campaign_id == campaign_id, SubmissionLog.is_success.is_(False))
    )
    count = deleted.rowcount or 0
    if count == 0:
        raise InvalidCampaignError("Không có phản hồi lỗi nào để gửi lại.")
    campaign.failed_count = 0
    campaign.status = CampaignStatus.IDLE.value
    campaign.status_reason = None
    await session.commit()
    return count
