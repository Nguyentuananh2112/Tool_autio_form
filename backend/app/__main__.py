"""Chạy backend: `python -m app` (vỏ app desktop gọi lệnh này, hoặc file .exe đóng gói từ nó)."""

from __future__ import annotations

import logging

import uvicorn

from app.core.config import get_settings


def main() -> None:
    app_settings = get_settings()
    logging.basicConfig(level=logging.DEBUG if app_settings.DEBUG else logging.INFO)
    uvicorn.run(
        "app.main:app",
        host=app_settings.HOST,
        port=app_settings.PORT,
        log_level="debug" if app_settings.DEBUG else "info",
        reload=False,
    )


if __name__ == "__main__":
    main()
