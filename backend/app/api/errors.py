"""Chuyển lỗi nghiệp vụ thành HTTP response thống nhất `{"message", "errors"}` (tiếng Việt)."""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.services.campaign_service import InvalidCampaignError, NotFoundError
from app.services.excel_reader import ExcelReadError
from app.services.form_errors import (
    FormClosedError,
    FormFetchError,
    FormParserError,
    FormRequiresLoginError,
    InvalidFormUrlError,
)
from app.services.gemini_keys import AiKeysUnavailableError, AiUnreachableError
from app.services.gemini_service import GeminiKeyMissingError, GeminiServiceError
from app.services.logic.validation import LogicMapInvalidError
from app.services.secret_store import SecretStoreError
from app.services.spss_generator import GeneratorConfigError
from app.workers.campaign_runner import CampaignAlreadyRunningError

logger = logging.getLogger(__name__)


class ConflictError(RuntimeError):
    """Thao tác không hợp lệ với trạng thái hiện tại (VD tạm dừng chiến dịch chưa chạy)."""


def _body(message: str, errors: list[str] | None = None, **extra: object) -> dict[str, object]:
    return {"detail": {"message": message, "errors": errors or [], **extra}}


STATUS_BY_ERROR: tuple[tuple[type[Exception], int], ...] = (
    (NotFoundError, status.HTTP_404_NOT_FOUND),
    (InvalidFormUrlError, status.HTTP_400_BAD_REQUEST),
    (FormRequiresLoginError, status.HTTP_400_BAD_REQUEST),
    (FormClosedError, status.HTTP_400_BAD_REQUEST),
    (FormFetchError, status.HTTP_502_BAD_GATEWAY),
    (FormParserError, status.HTTP_422_UNPROCESSABLE_CONTENT),
    (ExcelReadError, status.HTTP_400_BAD_REQUEST),
    (AiUnreachableError, status.HTTP_503_SERVICE_UNAVAILABLE),
    (GeminiKeyMissingError, status.HTTP_400_BAD_REQUEST),
    (GeminiServiceError, status.HTTP_502_BAD_GATEWAY),
    (CampaignAlreadyRunningError, status.HTTP_409_CONFLICT),
    (ConflictError, status.HTTP_409_CONFLICT),
    (SecretStoreError, status.HTTP_500_INTERNAL_SERVER_ERROR),
)


def register_error_handlers(app: FastAPI) -> None:
    async def handle_known(_: Request, exc: Exception) -> JSONResponse:
        for error_type, code in STATUS_BY_ERROR:
            if isinstance(exc, error_type):
                return JSONResponse(status_code=code, content=_body(str(exc)))
        logger.exception("Lỗi không phân loại", exc_info=exc)
        return JSONResponse(status_code=500, content=_body("Lỗi không mong đợi."))

    async def handle_invalid(_: Request, exc: Exception) -> JSONResponse:
        errors = getattr(exc, "errors", [])
        message = str(exc) if isinstance(exc, (InvalidCampaignError, LogicMapInvalidError)) else "Cấu hình câu trả lời chưa hợp lệ."
        return JSONResponse(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, content=_body(message, list(errors)))

    async def handle_keys(_: Request, exc: Exception) -> JSONResponse:
        # Giao diện nhận code này để mở hộp thoại "Hết lượt AI — dán key của bạn" (màn 12)
        attempts = [{"slot": a.slot.value, "state": a.state.value} for a in getattr(exc, "attempts", [])]
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content=_body(str(exc), code="AI_KEYS_UNAVAILABLE", keys=attempts),
        )

    for error_type, _ in STATUS_BY_ERROR:
        app.add_exception_handler(error_type, handle_known)
    app.add_exception_handler(AiKeysUnavailableError, handle_keys)
    app.add_exception_handler(InvalidCampaignError, handle_invalid)
    app.add_exception_handler(GeneratorConfigError, handle_invalid)
    app.add_exception_handler(LogicMapInvalidError, handle_invalid)
