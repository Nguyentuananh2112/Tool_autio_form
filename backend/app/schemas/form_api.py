"""DTO cho API phân tích & quản lý form."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

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
    created_at: datetime


class FormDetail(FormSummary):
    structure: ParsedFormStructure
