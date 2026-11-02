from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.campaign import Campaign


class QuestionRule(Base):
    __tablename__ = "question_rules"
    __table_args__ = (UniqueConstraint("campaign_id", "entry_id", name="uq_question_rules_campaign_entry"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    campaign_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Chỉ phần số của entry.<id>, VD "123456789"
    entry_id: Mapped[str] = mapped_column(String(50), nullable=False)
    question_type: Mapped[int] = mapped_column(Integer, nullable=False)
    # QuestionRuleConfig.model_dump(mode="json")
    config_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    cached_ai_pool: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, default=list, server_default=text("'[]'::jsonb")
    )

    campaign: Mapped[Campaign] = relationship(back_populates="question_rules")

    def __repr__(self) -> str:
        return f"<QuestionRule campaign={self.campaign_id} entry={self.entry_id}>"
