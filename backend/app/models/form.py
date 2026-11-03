from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, Boolean, DateTime, String, Text, Uuid, false, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.campaign import Campaign


class Form(Base):
    __tablename__ = "forms"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    view_url: Mapped[str] = mapped_column(Text, nullable=False)
    submit_url: Mapped[str] = mapped_column(Text, nullable=False)
    # Kết quả ParsedFormStructure.model_dump(mode="json") từ form_parser
    parsed_structure: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    # Form mẫu của Chế độ tập dùng: mọi lần gửi chỉ mô phỏng, không gửi lên Google (SPEC-017)
    is_demo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=false())
    # Bản đồ logic (LogicMap.model_dump(mode="json")) từ bước Soát logic; None = chưa soát (SPEC-020)
    logic_map: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    campaigns: Mapped[list[Campaign]] = relationship(
        back_populates="form", cascade="all, delete-orphan", passive_deletes=True
    )

    def __repr__(self) -> str:
        return f"<Form id={self.id} title={self.title!r}>"
