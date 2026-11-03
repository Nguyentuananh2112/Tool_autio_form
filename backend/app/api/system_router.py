"""Điều khiển tiến trình backend từ vỏ app desktop + tải trình duyệt dự phòng."""

from __future__ import annotations

import asyncio
import signal

from fastapi import APIRouter, status
from pydantic import BaseModel

from app.services.browser_installer import installer

router = APIRouter(prefix="/system", tags=["system"])
SHUTDOWN_DELAY_SECONDS = 0.2


class BrowserStatusRead(BaseModel):
    installed: bool
    installing: bool
    percent: int | None = None
    detail: str | None = None
    error: str | None = None


@router.post("/shutdown", status_code=status.HTTP_202_ACCEPTED)
async def shutdown() -> dict[str, str]:
    """Tắt êm: uvicorn nhận SIGINT → lifespan dừng an toàn mọi chiến dịch (chuyển PAUSED) → thoát.

    Vỏ desktop gọi trước khi đóng app hoặc cài bản cập nhật. Trên Windows, kill tiến trình con là
    TerminateProcess (không kịp lưu trạng thái), nên phải đi đường này.
    """
    asyncio.get_running_loop().call_later(SHUTDOWN_DELAY_SECONDS, signal.raise_signal, signal.SIGINT)
    return {"status": "shutting_down"}


@router.get("/browser", response_model=BrowserStatusRead)
async def browser_status() -> BrowserStatusRead:
    """Trạng thái trình duyệt dự phòng (đã tải chưa, đang tải bao nhiêu %)."""
    return BrowserStatusRead.model_validate((await installer.status()).__dict__)


@router.post("/browser/install", response_model=BrowserStatusRead, status_code=status.HTTP_202_ACCEPTED)
async def install_browser() -> BrowserStatusRead:
    """Bắt đầu tải trình duyệt chạy nền; giao diện hỏi lại GET /system/browser để xem tiến độ."""
    installer.start()
    return BrowserStatusRead.model_validate((await installer.status()).__dict__)
