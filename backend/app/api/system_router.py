"""Điều khiển tiến trình backend từ vỏ app desktop."""

from __future__ import annotations

import asyncio
import signal

from fastapi import APIRouter, status

router = APIRouter(prefix="/system", tags=["system"])
SHUTDOWN_DELAY_SECONDS = 0.2


@router.post("/shutdown", status_code=status.HTTP_202_ACCEPTED)
async def shutdown() -> dict[str, str]:
    """Tắt êm: uvicorn nhận SIGINT → lifespan dừng an toàn mọi chiến dịch (chuyển PAUSED) → thoát.

    Vỏ desktop gọi trước khi đóng app hoặc cài bản cập nhật. Trên Windows, kill tiến trình con là
    TerminateProcess (không kịp lưu trạng thái), nên phải đi đường này.
    """
    asyncio.get_running_loop().call_later(SHUTDOWN_DELAY_SECONDS, signal.raise_signal, signal.SIGINT)
    return {"status": "shutting_down"}
