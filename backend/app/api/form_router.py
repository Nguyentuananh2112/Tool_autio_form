from __future__ import annotations

import uuid

from fastapi import APIRouter, status
from sqlalchemy import select

from app.api.deps import DbSession
from app.models import Form
from app.schemas.form_api import FormDetail, FormParseRequest, FormSummary
from app.services.campaign_service import get_form, structure_of
from app.services.form_parser import parse_google_form

router = APIRouter(prefix="/forms", tags=["forms"])


def _summary(form: Form) -> FormSummary:
    structure = structure_of(form)
    return FormSummary(
        id=form.id, title=form.title, view_url=form.view_url, submit_url=form.submit_url,
        total_pages=structure.total_pages, question_count=len(structure.questions), created_at=form.created_at,
    )


def _detail(form: Form) -> FormDetail:
    return FormDetail(**_summary(form).model_dump(), structure=structure_of(form))


@router.post("/parse", response_model=FormDetail, status_code=status.HTTP_201_CREATED)
async def parse_form(payload: FormParseRequest, session: DbSession) -> FormDetail:
    structure = await parse_google_form(payload.url)
    form = Form(
        title=structure.title, view_url=structure.view_url, submit_url=structure.submit_url,
        parsed_structure=structure.model_dump(mode="json"),
    )
    session.add(form)
    await session.commit()
    await session.refresh(form)
    return _detail(form)


@router.get("", response_model=list[FormSummary])
async def list_forms(session: DbSession) -> list[FormSummary]:
    result = await session.execute(select(Form).order_by(Form.created_at.desc()))
    return [_summary(form) for form in result.scalars().all()]


@router.get("/{form_id}", response_model=FormDetail)
async def read_form(form_id: uuid.UUID, session: DbSession) -> FormDetail:
    return _detail(await get_form(session, form_id))


@router.delete("/{form_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_form(form_id: uuid.UUID, session: DbSession) -> None:
    await session.delete(await get_form(session, form_id))
    await session.commit()
