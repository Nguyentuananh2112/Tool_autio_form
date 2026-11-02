"""Tạo, xem, xóa chiến dịch và chạy thử nhóm SPSS (Mục 6.3 spec)."""

from __future__ import annotations

import asyncio
import uuid

from fastapi import APIRouter, status

from app.api.deps import DbSession
from app.api.errors import ConflictError
from app.schemas.campaign_api import CampaignCreate, CampaignRead, SpssPreviewRequest, SpssPreviewResponse
from app.services import campaign_service
from app.services.spss_generator import SurveyDataGenerator
from app.workers.campaign_control import registry

router = APIRouter(prefix="/campaigns", tags=["campaigns"])


@router.post("", response_model=CampaignRead, status_code=status.HTTP_201_CREATED)
async def create_campaign(payload: CampaignCreate, session: DbSession) -> CampaignRead:
    return campaign_service.to_read(await campaign_service.create_campaign(session, payload))


@router.get("", response_model=list[CampaignRead])
async def list_campaigns(session: DbSession) -> list[CampaignRead]:
    return [campaign_service.to_read(c) for c in await campaign_service.list_campaigns(session)]


@router.post("/preview-spss", response_model=SpssPreviewResponse)
async def preview_spss(payload: SpssPreviewRequest, session: DbSession) -> SpssPreviewResponse:
    structure = campaign_service.structure_of(await campaign_service.get_form(session, payload.form_id))

    def run() -> SpssPreviewResponse:
        generator = SurveyDataGenerator(structure, payload.rules, payload.spss_groups)
        return SpssPreviewResponse(groups=generator.preview_spss_groups(payload.sample_size), warnings=[])

    return await asyncio.to_thread(run)


@router.get("/{campaign_id}", response_model=CampaignRead)
async def read_campaign(campaign_id: uuid.UUID, session: DbSession) -> CampaignRead:
    return campaign_service.to_read(await campaign_service.get_campaign(session, campaign_id))


@router.delete("/{campaign_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_campaign(campaign_id: uuid.UUID, session: DbSession) -> None:
    control = registry.get(str(campaign_id))
    if control and control.is_active:
        raise ConflictError("Chiến dịch đang chạy. Hãy dừng trước khi xóa.")
    await session.delete(await campaign_service.get_campaign(session, campaign_id))
    await session.commit()
    registry.discard(str(campaign_id))
