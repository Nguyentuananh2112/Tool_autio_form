"""Kiểu dùng chung cho DTO."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

from pydantic import AfterValidator


def _ensure_utc(value: datetime) -> datetime:
    # SQLite trả về giờ UTC KHÔNG kèm múi giờ → trình duyệt hiểu nhầm là giờ địa phương (dev-notes BUG-005)
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


UtcDateTime = Annotated[datetime, AfterValidator(_ensure_utc)]
