"""Cấu hình ứng dụng, đọc từ biến môi trường / file `.env` bằng Pydantic Settings."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR: Path = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(str(BACKEND_DIR / ".env"),),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ------------------------------------------------------------------ App
    APP_NAME: str = "Smart Survey Auto-Filler"
    ENVIRONMENT: Literal["development", "staging", "production"] = "development"
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"
    # Danh sách origin cách nhau bởi dấu phẩy, VD: "http://localhost:5173,https://app.example.com"
    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"

    # ------------------------------------------------------------- Database
    DATABASE_URL: str = Field(
        ...,
        description="VD: postgresql+asyncpg://user:pass@localhost:5432/auto_form",
    )
    DB_ECHO: bool = False
    DB_POOL_SIZE: int = Field(default=10, ge=1, le=200)
    DB_MAX_OVERFLOW: int = Field(default=20, ge=0, le=500)
    DB_POOL_TIMEOUT_SECONDS: int = Field(default=30, ge=1)
    DB_POOL_RECYCLE_SECONDS: int = Field(default=1800, ge=60)

    # ---------------------------------------------------------------- Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # ------------------------------------------------------------- Security
    JWT_SECRET_KEY: str = Field(..., min_length=32)
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=60 * 24, ge=5)

    # --------------------------------------------------------------- Gemini
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

    @field_validator("DATABASE_URL")
    @classmethod
    def _normalize_database_url(cls, value: str) -> str:
        url = value.strip()
        if url.startswith("postgres://"):
            url = "postgresql+asyncpg://" + url[len("postgres://"):]
        elif url.startswith("postgresql://"):
            url = "postgresql+asyncpg://" + url[len("postgresql://"):]
        if not url.startswith("postgresql+asyncpg://"):
            raise ValueError("DATABASE_URL phải dùng driver async: postgresql+asyncpg://...")
        return url

    @field_validator("API_V1_PREFIX")
    @classmethod
    def _normalize_prefix(cls, value: str) -> str:
        prefix = "/" + value.strip().strip("/")
        return prefix if prefix != "/" else ""

    @model_validator(mode="after")
    def _check_production_safety(self) -> Settings:
        if self.ENVIRONMENT == "production" and self.DEBUG:
            raise ValueError("Không được bật DEBUG trong môi trường production.")
        return self

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]  # các trường bắt buộc được nạp từ môi trường


settings: Settings = get_settings()
