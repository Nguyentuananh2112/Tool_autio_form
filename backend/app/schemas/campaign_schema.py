"""Cấu hình sinh dữ liệu của chiến dịch (luật câu hỏi, nhóm SPSS, lịch chạy) và kết quả preview.

Phase 3 sẽ bổ sung các DTO request/response của campaign_router vào file này.
"""

from __future__ import annotations

from datetime import date, time
from enum import StrEnum

from pydantic import BaseModel, Field, field_validator, model_validator


class RuleStrategy(StrEnum):
    # Trắc nghiệm/Likert/Checkbox: theo trọng số; Tự luận: bốc từ text_pool; Ngày/Giờ: ngẫu nhiên trong khoảng
    AUTO = "AUTO"
    FIXED = "FIXED"  # luôn trả lời fixed_value
    SKIP = "SKIP"  # không trả lời (chỉ hợp lệ với câu không bắt buộc)


class QuestionRuleConfig(BaseModel):
    entry_id: str = Field(min_length=1, max_length=50)
    question_type: int
    strategy: RuleStrategy = RuleStrategy.AUTO
    # Radio/Dropdown/Scale/Grid: trọng số tương đối theo option value (tổng nên = 100).
    # Checkbox/Checkbox Grid: xác suất độc lập 0..100 cho từng ô.
    # Khóa "__other_option__" là ô "Mục khác".
    weights: dict[str, float] = Field(default_factory=dict)
    min_checked: int = Field(default=0, ge=0)
    max_checked: int | None = Field(default=None, ge=1)
    other_text_pool: list[str] = Field(default_factory=list)
    # Tự luận: câu trả lời sẵn (từ Gemini cached_ai_pool hoặc người dùng nhập)
    text_pool: list[str] = Field(default_factory=list)
    fixed_value: str | list[str] | None = None
    # Tỷ lệ % trả lời đối với câu KHÔNG bắt buộc
    answer_rate: float = Field(default=100.0, ge=0.0, le=100.0)
    # Ngày / Giờ
    date_start: date | None = None
    date_end: date | None = None
    time_start: time | None = None
    time_end: time | None = None
    # Cấu hình AI (Phase 2 dùng để sinh text_pool)
    ai_context: str | None = None
    ai_persona: str | None = None
    ai_sample_count: int = Field(default=50, ge=1, le=500)

    @field_validator("entry_id")
    @classmethod
    def _entry_id_digits(cls, value: str) -> str:
        cleaned = value.strip().removeprefix("entry.")
        if not cleaned.isdigit():
            raise ValueError("entry_id chỉ gồm phần số, VD '123456789'")
        return cleaned

    @field_validator("weights")
    @classmethod
    def _weights_non_negative(cls, value: dict[str, float]) -> dict[str, float]:
        for key, weight in value.items():
            if weight < 0:
                raise ValueError(f"Trọng số của '{key}' không được âm")
        return value

    @field_validator("text_pool", "other_text_pool")
    @classmethod
    def _strip_pool(cls, value: list[str]) -> list[str]:
        return [item.strip() for item in value if item and item.strip()]

    @model_validator(mode="after")
    def _check_ranges(self) -> QuestionRuleConfig:
        if self.max_checked is not None and self.max_checked < self.min_checked:
            raise ValueError("max_checked phải >= min_checked")
        if self.date_start and self.date_end and self.date_start > self.date_end:
            raise ValueError("date_start phải <= date_end")
        if self.time_start and self.time_end and self.time_start > self.time_end:
            raise ValueError("time_start phải <= time_end")
        if self.strategy == RuleStrategy.FIXED and self.fixed_value in (None, "", []):
            raise ValueError("Chiến lược FIXED yêu cầu fixed_value")
        return self


class SpssGroupConfig(BaseModel):
    group_id: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=255)
    mean: float = Field(ge=0.0, le=100.0, description="Điểm trung bình mục tiêu trên thang đo")
    std: float = Field(ge=0.1, le=3.0, description="Độ lệch chuẩn mục tiêu của từng biến quan sát")
    # Tương quan kỳ vọng giữa các biến quan sát. Nếu bỏ trống sẽ suy ra từ alpha_target.
    r: float | None = Field(default=None, ge=0.0, le=0.95)
    alpha_target: float | None = Field(default=None, ge=0.0, le=0.99)
    entries: list[str] = Field(min_length=2)
    # Biến quan sát đảo chiều (reverse-coded); alpha được tính sau khi đảo ngược lại
    reversed_entries: list[str] = Field(default_factory=list)
    # Hiệu chỉnh tham số ẩn để bù sai lệch do làm tròn & cắt biên thang Likert
    calibrate: bool = True

    @field_validator("entries", "reversed_entries")
    @classmethod
    def _normalize_entries(cls, value: list[str]) -> list[str]:
        return [entry.strip().removeprefix("entry.") for entry in value]

    @model_validator(mode="after")
    def _check_group(self) -> SpssGroupConfig:
        if len(set(self.entries)) != len(self.entries):
            raise ValueError("Một câu hỏi xuất hiện nhiều lần trong cùng nhóm")
        if not set(self.reversed_entries) <= set(self.entries):
            raise ValueError("reversed_entries phải là tập con của entries")
        if self.r is None and self.alpha_target is None:
            raise ValueError("Cần cung cấp r hoặc alpha_target")
        return self


class ScheduleMode(StrEnum):
    BURST = "BURST"
    SCHEDULED = "SCHEDULED"


class ScheduleConfig(BaseModel):
    mode: ScheduleMode = ScheduleMode.BURST
    duration_minutes: float | None = Field(default=None, gt=0, le=60 * 24 * 30)
    concurrency: int = Field(default=10, ge=1, le=200)

    @model_validator(mode="after")
    def _check_duration(self) -> ScheduleConfig:
        if self.mode == ScheduleMode.SCHEDULED and self.duration_minutes is None:
            raise ValueError("Chế độ SCHEDULED yêu cầu duration_minutes")
        return self


class SpssItemPreview(BaseModel):
    entry_id: str
    title: str
    is_reversed: bool
    mean: float
    std: float
    distribution: dict[str, int]


class SpssGroupPreview(BaseModel):
    group_id: str
    name: str
    n_samples: int
    n_items: int
    cronbach_alpha: float | None
    alpha_target: float | None
    mean_inter_item_r: float | None
    target_r: float | None
    latent_r: float
    target_mean: float
    achieved_mean: float
    target_std: float
    achieved_std: float
    items: list[SpssItemPreview]
    warnings: list[str] = Field(default_factory=list)
