from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, Boolean, CheckConstraint, DateTime, ForeignKey, Integer, String, Uuid, func, text, true
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.form import Form
    from app.models.question_rule import QuestionRule
    from app.models.submission_log import SubmissionLog


class DataSource(StrEnum):
    PROBABILITY = "PROBABILITY"
    EXCEL = "EXCEL"


class CampaignStatus(StrEnum):
    IDLE = "IDLE"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


def _sql_in(values: type[StrEnum]) -> str:
    return ", ".join(f"'{member.value}'" for member in values)


class Campaign(Base):
    __tablename__ = "campaigns"
    __table_args__ = (
        CheckConstraint(f"data_source IN ({_sql_in(DataSource)})", name="data_source_valid"),
        CheckConstraint(f"status IN ({_sql_in(CampaignStatus)})", name="status_valid"),
        CheckConstraint("total_target > 0", name="total_target_positive"),
        CheckConstraint("completed_count >= 0 AND failed_count >= 0", name="counts_non_negative"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    form_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("forms.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    data_source: Mapped[str] = mapped_column(
        String(50), nullable=False, default=DataSource.PROBABILITY.value
    )
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default=CampaignStatus.IDLE.value,
        server_default=CampaignStatus.IDLE.value, index=True,
    )
    total_target: Mapped[int] = mapped_column(Integer, nullable=False)
    completed_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    failed_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    # {"mode": "BURST" | "SCHEDULED", "duration_minutes": 120, "concurrency": 20}
    schedule_config: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    # [{"group_id", "name", "mean", "std", "r", "alpha_target", "entries", "reversed_entries", ...}]
    spss_groups: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON, nullable=False, default=list, server_default=text("'[]'")
    )
    excel_data: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON, nullable=True)
    proxy_list: Mapped[list[str]] = mapped_column(
        JSON, nullable=False, default=list, server_default=text("'[]'")
    )
    use_playwright_fallback: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=true()
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    form: Mapped[Form] = relationship(back_populates="campaigns")
    question_rules: Mapped[list[QuestionRule]] = relationship(
        back_populates="campaign", cascade="all, delete-orphan", passive_deletes=True
    )
    submission_logs: Mapped[list[SubmissionLog]] = relationship(
        back_populates="campaign", cascade="all, delete-orphan", passive_deletes=True,
        lazy="noload",  # có thể lên tới hàng nghìn bản ghi; truy vấn riêng khi cần
    )

    @property
    def processed_count(self) -> int:
        return self.completed_count + self.failed_count

    def __repr__(self) -> str:
        return f"<Campaign id={self.id} name={self.name!r} status={self.status}>"
