"""Chạy backend: `python -m app` (khi phát triển) hoặc file .exe đóng gói từ `run_backend.py` (vỏ desktop gọi)."""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler

import uvicorn

from app.core.config import get_settings

LOG_FILE_BYTES = 2 * 1024 * 1024
LOG_BACKUPS = 3


def configure_logging() -> None:
    """Log ra console và ra file <DATA_DIR>/logs/backend.log (bản cài không có cửa sổ console)."""
    app_settings = get_settings()
    log_dir = app_settings.DATA_DIR / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    handlers: list[logging.Handler] = [
        logging.StreamHandler(),
        RotatingFileHandler(log_dir / "backend.log", maxBytes=LOG_FILE_BYTES, backupCount=LOG_BACKUPS, encoding="utf-8"),
    ]
    logging.basicConfig(
        level=logging.DEBUG if app_settings.DEBUG else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=handlers,
    )


def main() -> None:
    app_settings = get_settings()
    configure_logging()
    from app.main import app  # import sau khi cấu hình log

    uvicorn.run(
        app,
        host=app_settings.HOST,
        port=app_settings.PORT,
        log_level="debug" if app_settings.DEBUG else "info",
        log_config=None,  # dùng cấu hình logging ở trên (ghi cả ra file)
    )


if __name__ == "__main__":
    main()
