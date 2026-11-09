from __future__ import annotations

import asyncio

from fastapi import APIRouter, status

from app.core.config import get_settings
from app.schemas.misc_api import AppSettingsRead, GeminiKeyUpdate
from app.services import secret_store
from app.services.gemini_keys import KeySlot, candidate_keys

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("", response_model=AppSettingsRead)
async def read_settings() -> AppSettingsRead:
    app_settings = get_settings()
    keys = dict(await asyncio.to_thread(candidate_keys))
    user_key = bool(keys.get(KeySlot.USER))
    shared_key = bool(keys.get(KeySlot.SHARED) or keys.get(KeySlot.BACKUP))
    return AppSettingsRead(
        app_version=app_settings.APP_VERSION,
        data_dir=str(app_settings.DATA_DIR),
        gemini_model=app_settings.GEMINI_MODEL,
        gemini_key_configured=user_key or shared_key,
        gemini_user_key=user_key,
        gemini_shared_key=shared_key,
    )


@router.put("/gemini-key", status_code=status.HTTP_204_NO_CONTENT)
async def save_gemini_key(payload: GeminiKeyUpdate) -> None:
    await asyncio.to_thread(secret_store.set_gemini_api_key, payload.api_key)


@router.delete("/gemini-key", status_code=status.HTTP_204_NO_CONTENT)
async def delete_gemini_key() -> None:
    await asyncio.to_thread(secret_store.delete_gemini_api_key)
