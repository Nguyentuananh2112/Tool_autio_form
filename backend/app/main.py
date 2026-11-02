"""Entrypoint FastAPI: CORS, lifespan (DB, khôi phục chiến dịch, tắt an toàn), router, WebSocket."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import ai_router, campaign_router, campaign_run_router, excel_router, form_router, health_router, settings_router, ws_router
from app.api.deps import require_app_token
from app.api.errors import register_error_handlers
from app.core.config import get_settings
from app.core.database import AsyncSessionLocal, dispose_engine, init_db
from app.core.security import TOKEN_HEADER
from app.services.campaign_service import recover_interrupted
from app.workers.campaign_control import registry

logger = logging.getLogger(__name__)
SHUTDOWN_TIMEOUT_SECONDS = 15


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    await init_db()
    async with AsyncSessionLocal() as session:
        recovered = await recover_interrupted(session)
    if recovered:
        logger.info("Đã chuyển %d chiến dịch bị gián đoạn sang PAUSED", recovered)
    try:
        yield
    finally:
        # Tắt app: dừng an toàn mọi chiến dịch (chúng chuyển sang PAUSED, mở lại bấm Tiếp tục)
        await registry.stop_all(timeout=SHUTDOWN_TIMEOUT_SECONDS)
        await dispose_engine()


def create_app(*, runner_kwargs: dict[str, Any] | None = None) -> FastAPI:
    app_settings = get_settings()
    app = FastAPI(
        title=app_settings.APP_NAME,
        version=app_settings.APP_VERSION,
        lifespan=lifespan,
        docs_url="/docs" if not app_settings.is_production else None,
        redoc_url=None,
    )
    app.state.runner_kwargs = runner_kwargs or {}
    app.add_middleware(
        CORSMiddleware,
        allow_origins=app_settings.cors_origins_list,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["Content-Type", TOKEN_HEADER],
    )
    register_error_handlers(app)

    prefix = app_settings.API_V1_PREFIX
    app.include_router(health_router.router, prefix=prefix)
    protected = [Depends(require_app_token)]
    for module in (form_router, excel_router, ai_router, settings_router, campaign_router, campaign_run_router):
        app.include_router(module.router, prefix=prefix, dependencies=protected)
    app.include_router(ws_router.router)
    return app


app = create_app()
