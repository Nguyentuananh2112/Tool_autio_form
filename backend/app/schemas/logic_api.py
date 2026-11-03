"""DTO của API Soát logic (màn 11)."""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.schemas.campaign_schema import QuestionRuleConfig, SpssGroupConfig
from app.schemas.logic_schema import LogicMap


class LogicReviewRequest(BaseModel):
    rules: list[QuestionRuleConfig] = Field(default_factory=list)
    spss_groups: list[SpssGroupConfig] = Field(default_factory=list)
    # Bản đang sửa trên màn hình; bỏ trống = bản đã lưu của form
    logic: LogicMap | None = None
    sample_size: int = Field(default=200, ge=50, le=2000)


class ViolationCount(BaseModel):
    kind: str  # RULE / EXCLUSIVE / SPREAD
    key: str  # rule_id / entry_id / group_id
    before: int  # số phản hồi mâu thuẫn nếu sinh kiểu cũ
    after: int  # số phản hồi còn mâu thuẫn sau soát (phải = 0)


class GroupCorrelation(BaseModel):
    group_id: str
    name: str
    before: float | None  # tương quan trung bình giữa các câu (đã theo chiều tích cực)
    after: float | None


class RatioDrift(BaseModel):
    entry_id: str
    title: str
    max_drift_pct: float  # điểm % lệch lớn nhất của một đáp án so với khi không soát


class SampleRespondent(BaseModel):
    attitude: str  # "khá tích cực", ...
    answers: dict[str, list[str]]


class LogicReviewResult(BaseModel):
    sample_size: int
    inconsistent_before: int
    inconsistent_after: int
    repaired: int
    regenerated: int
    violations: list[ViolationCount]
    correlations: list[GroupCorrelation]
    drifts: list[RatioDrift]
    sample: SampleRespondent | None
    logic: LogicMap
    ready: bool
