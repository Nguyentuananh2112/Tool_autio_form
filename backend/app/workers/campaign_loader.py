"""Đọc chiến dịch từ DB và dựng kế hoạch chạy: cấu trúc form, danh sách phản hồi, phần đã gửi."""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Campaign, DataSource, QuestionRule, SubmissionLog
from app.schemas.campaign_schema import QuestionRuleConfig, ScheduleConfig, SpssGroupConfig
from app.schemas.excel_schema import ConversionReport
from app.schemas.form_schema import ParsedFormStructure
from app.services.excel_mapper import records_to_responses
from app.schemas.logic_schema import LogicMap
from app.services.spss_generator import GeneratedResponse, SurveyDataGenerator
from app.services.text_mutation import micro_mutate


class CampaignNotFoundError(LookupError):
    pass


@dataclass
class CampaignPlan:
    campaign_id: uuid.UUID
    name: str
    structure: ParsedFormStructure
    responses: list[GeneratedResponse]
    schedule: ScheduleConfig
    total_target: int
    proxy: str | None
    use_fallback: bool
    is_demo: bool
    completed_count: int
    failed_count: int
    done_sequences: set[int] = field(default_factory=set)
    excel_report: ConversionReport | None = None

    @property
    def pending(self) -> list[GeneratedResponse]:
        return [r for r in self.responses if r.sequence_number not in self.done_sequences]


def campaign_seed(campaign_id: uuid.UUID) -> int:
    """Seed cố định theo chiến dịch → chạy tiếp sau tạm dừng sinh lại đúng bộ dữ liệu cũ."""
    return campaign_id.int % (2**32)


def rule_to_config(rule: QuestionRule) -> QuestionRuleConfig:
    config = QuestionRuleConfig.model_validate({**rule.config_json, "entry_id": rule.entry_id, "question_type": rule.question_type})
    if not config.text_pool and rule.cached_ai_pool:
        config = config.model_copy(update={"text_pool": [t.strip() for t in rule.cached_ai_pool if t and t.strip()]})
    return config


async def load_plan(session: AsyncSession, campaign_id: uuid.UUID) -> CampaignPlan:
    campaign = await session.get(
        Campaign, campaign_id, options=[selectinload(Campaign.form), selectinload(Campaign.question_rules)]
    )
    if campaign is None:
        raise CampaignNotFoundError(f"Không tìm thấy chiến dịch {campaign_id}")

    structure = ParsedFormStructure.model_validate(campaign.form.parsed_structure)
    report: ConversionReport | None = None
    if campaign.data_source == DataSource.EXCEL:
        responses, report = records_to_responses(campaign.excel_data or [], structure)
        responses = responses[: campaign.total_target]
    else:
        generator = SurveyDataGenerator(
            structure,
            [rule_to_config(rule) for rule in campaign.question_rules],
            [SpssGroupConfig.model_validate(group) for group in campaign.spss_groups],
            seed=campaign_seed(campaign.id),
            text_mutator=micro_mutate,
            logic=LogicMap.model_validate(campaign.logic_map) if campaign.logic_map else None,
        )
        responses = await asyncio.to_thread(generator.generate, campaign.total_target)

    done_rows = await session.execute(
        select(SubmissionLog.sequence_number).where(SubmissionLog.campaign_id == campaign.id)
    )
    return CampaignPlan(
        campaign_id=campaign.id,
        name=campaign.name,
        structure=structure,
        responses=responses,
        schedule=ScheduleConfig.model_validate(campaign.schedule_config),
        total_target=len(responses),
        proxy=campaign.proxy_list[0] if campaign.proxy_list else None,
        use_fallback=campaign.use_playwright_fallback and not campaign.form.is_demo,
        is_demo=campaign.form.is_demo,
        completed_count=campaign.completed_count,
        failed_count=campaign.failed_count,
        done_sequences=set(done_rows.scalars().all()),
        excel_report=report,
    )
