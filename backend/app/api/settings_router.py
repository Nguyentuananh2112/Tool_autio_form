from __future__ import annotations

import asyncio

from fastapi import APIRouter, status

from app.core.config import get_settings
from app.schemas.misc_api import AppSettingsRead, GeminiKeyUpdate
from app.services import secret_store

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("", response_model=AppSettingsRead)
async def read_settings() -> AppSettingsRead:
    app_settings = get_settings()
    key = await asyncio.to_thread(secret_store.resolve_gemini_api_key)
    return AppSettingsRead(
        app_version=app_settings.APP_VERSION,
        data_dir=str(app_settings.DATA_DIR),
        gemini_model=app_settings.GEMINI_MODEL,
        gemini_key_configured=bool(key),
    )


@router.put("/gemini-key", status_code=status.HTTP_204_NO_CONTENT)
async def save_gemini_key(payload: GeminiKeyUpdate) -> None:
    await asyncio.to_thread(secret_store.set_gemini_api_key, payload.api_key)


@router.delete("/gemini-key", status_code=status.HTTP_204_NO_CONTENT)
async def delete_gemini_key() -> None:
    await asyncio.to_thread(secret_store.delete_gemini_api_key)
