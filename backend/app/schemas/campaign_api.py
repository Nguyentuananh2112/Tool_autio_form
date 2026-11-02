"""DTO cho API chiến dịch (tạo, xem, chạy thử SPSS, nhật ký, nhập Excel)."""

from __future__ import annotations

import uuid
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models import DataSource
from app.schemas.campaign_schema import QuestionRuleConfig, ScheduleConfig, SpssGroupConfig, SpssGroupPreview
from app.schemas.common import UtcDateTime
from app.schemas.excel_schema import ConversionReport

MAX_TARGET = 10_000


class CampaignCreate(BaseModel):
    form_id: uuid.UUID
    name: str = Field(min_length=1, max_length=255)
    data_source: DataSource = DataSource.PROBABILITY
    # Nguồn Excel: bỏ trống = dùng hết các dòng hợp lệ
    total_target: int | None = Field(default=None, ge=1, le=MAX_TARGET)
    schedule: ScheduleConfig = Field(default_factory=ScheduleConfig)
    rules: list[QuestionRuleConfig] = Field(default_factory=list)
    spss_groups: list[SpssGroupConfig] = Field(default_factory=list)
    excel_records: list[dict[str, Any]] | None = None
    proxy: str | None = Field(default=None, max_length=500)
    use_playwright_fallback: bool = True

    @model_validator(mode="after")
    def _check_source(self) -> CampaignCreate:
        if self.data_source == DataSource.PROBABILITY and self.total_target is None:
            raise ValueError("Cần nhập số phản hồi cần gửi (total_target).")
        if self.data_source == DataSource.EXCEL and not self.excel_records:
            raise ValueError("Nguồn Excel cần excel_records (dữ liệu đã ghép cột).")
        return self


class CampaignRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    form_id: uuid.UUID
    form_title: str
    name: str
    data_source: str
    status: str
    total_target: int
    completed_count: int
    failed_count: int
    schedule: ScheduleConfig
    proxy: str | None
    use_playwright_fallback: bool
    created_at: UtcDateTime
    is_active: bool = False
    pause_reason: str | None = None


class SpssPreviewRequest(BaseModel):
    form_id: uuid.UUID
    rules: list[QuestionRuleConfig] = Field(default_factory=list)
    spss_groups: list[SpssGroupConfig] = Field(default_factory=list)
    sample_size: int = Field(default=200, ge=20, le=5000)


class SpssPreviewResponse(BaseModel):
    groups: list[SpssGroupPreview]
    warnings: list[str]


class TrialSubmitRequest(BaseModel):
    form_id: uuid.UUID
    rules: list[QuestionRuleConfig] = Field(default_factory=list)
    spss_groups: list[SpssGroupConfig] = Field(default_factory=list)
    proxy: str | None = Field(default=None, max_length=500)
    # True = chỉ mô phỏng, xem dữ liệu sẽ gửi (form mẫu luôn mô phỏng)
    dry_run: bool = False


class TrialSubmitResponse(BaseModel):
    success: bool
    outcome: str
    status_code: int
    engine_used: str
    error: str | None
    page_history: str
    payload_sent: dict[str, Any]


class SubmissionLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    sequence_number: int
    engine_used: str
    status_code: int
    is_success: bool
    error_detail: str | None
    executed_at: UtcDateTime
    page_history: str | None = None


class ExcelConvertResponse(BaseModel):
    report: ConversionReport
    records: list[dict[str, Any]]
