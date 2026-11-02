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
from app.services.gemini_service import GeminiKeyMissingError, GeminiServiceError
from app.services.secret_store import SecretStoreError
from app.services.spss_generator import GeneratorConfigError
from app.workers.campaign_runner import CampaignAlreadyRunningError

logger = logging.getLogger(__name__)


class ConflictError(RuntimeError):
    """Thao tác không hợp lệ với trạng thái hiện tại (VD tạm dừng chiến dịch chưa chạy)."""


def _body(message: str, errors: list[str] | None = None) -> dict[str, object]:
    return {"detail": {"message": message, "errors": errors or []}}


STATUS_BY_ERROR: tuple[tuple[type[Exception], int], ...] = (
    (NotFoundError, status.HTTP_404_NOT_FOUND),
    (InvalidFormUrlError, status.HTTP_400_BAD_REQUEST),
    (FormRequiresLoginError, status.HTTP_400_BAD_REQUEST),
    (FormClosedError, status.HTTP_400_BAD_REQUEST),
    (FormFetchError, status.HTTP_502_BAD_GATEWAY),
    (FormParserError, status.HTTP_422_UNPROCESSABLE_CONTENT),
    (ExcelReadError, status.HTTP_400_BAD_REQUEST),
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
        message = str(exc) if isinstance(exc, InvalidCampaignError) else "Cấu hình câu trả lời chưa hợp lệ."
        return JSONResponse(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, content=_body(message, list(errors)))

    for error_type, _ in STATUS_BY_ERROR:
        app.add_exception_handler(error_type, handle_known)
    app.add_exception_handler(InvalidCampaignError, handle_invalid)
    app.add_exception_handler(GeneratorConfigError, handle_invalid)
