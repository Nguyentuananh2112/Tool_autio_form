from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING, Any

from sqlalchemy import BigInteger, Boolean, CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.campaign import Campaign


class EngineUsed(StrEnum):
    HTTPX = "HTTPX"
    PLAYWRIGHT = "PLAYWRIGHT"


class SubmissionLog(Base):
    __tablename__ = "submission_logs"
    __table_args__ = (
        CheckConstraint(
            "engine_used IN ('HTTPX', 'PLAYWRIGHT')", name="engine_used_valid"
        ),
        Index("ix_submission_logs_campaign_sequence", "campaign_id", "sequence_number"),
    )

    # BigInteger + autoincrement trên PostgreSQL sinh ra BIGSERIAL
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    campaign_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False, index=True
    )
    sequence_number: Mapped[int] = mapped_column(Integer, nullable=False)
    engine_used: Mapped[str] = mapped_column(String(30), nullable=False)
    status_code: Mapped[int] = mapped_column(Integer, nullable=False)
    is_success: Mapped[bool] = mapped_column(Boolean, nullable=False)
    # {"entry.123": ["Nam"], "pageHistory": "0,1", ...}
    payload_sent: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    error_detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    executed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    campaign: Mapped[Campaign] = relationship(back_populates="submission_logs")

    def __repr__(self) -> str:
        return (
            f"<SubmissionLog campaign={self.campaign_id} seq={self.sequence_number} "
            f"engine={self.engine_used} ok={self.is_success}>"
        )
