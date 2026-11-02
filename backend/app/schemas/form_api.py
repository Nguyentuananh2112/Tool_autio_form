"""DTO cho API phân tích & quản lý form."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import UtcDateTime
from app.schemas.form_schema import ParsedFormStructure


class FormParseRequest(BaseModel):
    url: str = Field(min_length=5, max_length=2000)


class FormSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    view_url: str
    submit_url: str
    total_pages: int
    question_count: int
    is_demo: bool = False
    created_at: UtcDateTime


class FormDetail(FormSummary):
    structure: ParsedFormStructure
