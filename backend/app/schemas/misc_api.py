"""DTO cho API AI, cài đặt và lỗi chung."""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.services.gemini_service import DEFAULT_PERSONA, MAX_POOL_SIZE


class GeneratePoolRequest(BaseModel):
    question_title: str = Field(min_length=1, max_length=2000)
    survey_context: str = Field(default="", max_length=2000)
    count: int = Field(default=50, ge=1, le=MAX_POOL_SIZE)
    persona: str = Field(default=DEFAULT_PERSONA, max_length=500)


class GeneratePoolResponse(BaseModel):
    answers: list[str]


class AppSettingsRead(BaseModel):
    app_version: str
    data_dir: str
    gemini_model: str
    gemini_key_configured: bool


class GeminiKeyUpdate(BaseModel):
    api_key: str = Field(min_length=10, max_length=255)


class HealthRead(BaseModel):
    status: str
    app_version: str
    database_ok: bool


class ErrorBody(BaseModel):
    """Thân lỗi thống nhất: `message` cho người dùng, `errors` chi tiết (nếu có)."""

    message: str
    errors: list[str] = Field(default_factory=list)
