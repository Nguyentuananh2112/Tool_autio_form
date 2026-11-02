"""Sự kiện real-time của chiến dịch, gửi qua WebSocket `/ws/campaigns/{id}` (Mục 6.4 spec)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field


def _now() -> datetime:
    return datetime.now(UTC)


class SubmissionUpdateEvent(BaseModel):
    event: Literal["SUBMISSION_UPDATE"] = "SUBMISSION_UPDATE"
    campaign_id: str
    sequence_number: int
    completed_count: int
    failed_count: int
    engine_used: str
    status_code: int
    is_success: bool
    page_history: str
    error_detail: str | None = None
    next_delay_seconds: float | None = None
    timestamp: datetime = Field(default_factory=_now)


class StatusChangeEvent(BaseModel):
    event: Literal["STATUS_CHANGE"] = "STATUS_CHANGE"
    campaign_id: str
    status: str
    reason: str | None = None
    timestamp: datetime = Field(default_factory=_now)


class RateLimitedEvent(BaseModel):
    event: Literal["RATE_LIMITED"] = "RATE_LIMITED"
    campaign_id: str
    sequence_number: int
    status_code: int
    wait_seconds: float
    consecutive_blocks: int
    will_pause: bool
    timestamp: datetime = Field(default_factory=_now)
