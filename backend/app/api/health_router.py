from __future__ import annotations

from fastapi import APIRouter

from app.core.config import get_settings
from app.core.database import check_db_connection
from app.schemas.misc_api import HealthRead

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthRead)
async def health() -> HealthRead:
    """Vỏ app desktop gọi để biết backend đã sẵn sàng (không cần token)."""
    database_ok = await check_db_connection()
    return HealthRead(status="ok" if database_ok else "degraded", app_version=get_settings().APP_VERSION, database_ok=database_ok)
