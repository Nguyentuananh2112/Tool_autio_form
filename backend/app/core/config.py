"""Cấu hình ứng dụng desktop, đọc từ biến môi trường / file `.env` bằng Pydantic Settings.

App chạy trên máy người dùng (dev-notes SPEC-008, SPEC-011): dữ liệu nằm trong SQLite ở
thư mục dữ liệu của người dùng, không có tài khoản đăng nhập.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR: Path = Path(__file__).resolve().parents[2]
APP_DIR_NAME = "Auto-Form"


def default_data_dir() -> Path:
    """%APPDATA%\\Auto-Form trên Windows, ~/.local/share/Auto-Form trên hệ khác."""
    appdata = os.environ.get("APPDATA")
    base = Path(appdata) if appdata else Path.home() / ".local" / "share"
    return base / APP_DIR_NAME


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(str(BACKEND_DIR / ".env"),),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ------------------------------------------------------------------ App
    APP_NAME: str = "Auto-Form"
    APP_VERSION: str = "0.1.0"
    ENVIRONMENT: Literal["development", "production"] = "development"
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"
    # Chỉ nghe trên loopback: backend là tiến trình con của app desktop
    HOST: str = "127.0.0.1"
    PORT: int = Field(default=8765, ge=1024, le=65535)
    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"

    # ------------------------------------------------------------- Storage
    DATA_DIR: Path = Field(default_factory=default_data_dir)
    # Để trống = <DATA_DIR>/auto_form.db
    DATABASE_URL: str = ""
    DB_ECHO: bool = False

    # --------------------------------------------------------------- Gemini
    # Key thật được lưu trong kho bảo mật của Windows; biến này chỉ dùng khi phát triển
    GEMINI_API_KEY: str | None = None
    GEMINI_MODEL: str = "gemini-2.5-flash"

    # ------------------------------------------------- Form fetch / engines
    FORM_FETCH_TIMEOUT_SECONDS: float = Field(default=20.0, gt=0)
    HTTP_USER_AGENT: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
    )

    # ------------------------------------------------------ Data generation
    SPSS_PREVIEW_SAMPLE_SIZE: int = Field(default=200, ge=20, le=5000)
    MAX_CAMPAIGN_TARGET: int = Field(default=10000, ge=1)

    @field_validator("HOST")
    @classmethod
    def _loopback_only(cls, value: str) -> str:
        if value not in ("127.0.0.1", "localhost", "::1"):
            raise ValueError("Backend desktop chỉ được nghe trên địa chỉ loopback.")
        return value

    @field_validator("API_V1_PREFIX")
    @classmethod
    def _normalize_prefix(cls, value: str) -> str:
        prefix = "/" + value.strip().strip("/")
        return prefix if prefix != "/" else ""

    @model_validator(mode="after")
    def _resolve_database_url(self) -> Settings:
        url = self.DATABASE_URL.strip()
        if not url:
            url = f"sqlite+aiosqlite:///{(self.DATA_DIR / 'auto_form.db').as_posix()}"
        elif url.startswith("sqlite://"):
            url = "sqlite+aiosqlite://" + url[len("sqlite://"):]
        if not url.startswith("sqlite+aiosqlite://"):
            raise ValueError("DATABASE_URL phải là SQLite async: sqlite+aiosqlite:///đường/dẫn.db")
        self.DATABASE_URL = url
        return self

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"

    @property
    def is_in_memory_db(self) -> bool:
        return ":memory:" in self.DATABASE_URL


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings: Settings = get_settings()
