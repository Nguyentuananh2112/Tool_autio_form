"""Gửi phản hồi bằng POST /formResponse (Mục 5.4.A spec).

Khác spec có chủ đích (dev-notes SPEC-012): một User-Agent cố định, trung thực; tối đa một
proxy cố định do người dùng cấu hình cho mạng của họ — không xoay vòng để lách giới hạn.
"""

from __future__ import annotations

import email.utils
import time
from collections.abc import Sequence
from datetime import UTC, datetime
from types import TracebackType
from urllib.parse import urlencode

import httpx

from app.models.submission_log import EngineUsed
from app.schemas.form_schema import ParsedFormStructure
from app.workers.submission_types import OutcomeKind, SubmitOutcome

DEFAULT_TIMEOUT_SECONDS = 30.0
# Đã kiểm chứng với Google thật (dev-notes RISK-009, 2026-11-03):
# - Gửi thành công → 200, trang xác nhận KHÔNG có ô ẩn của form (fbzx, pageHistory); câu xác nhận
#   có thể bị chủ form đổi tuỳ ý nên KHÔNG được dựa vào câu chữ.
# - Bị từ chối (thiếu câu bắt buộc...) → 400, Google trả lại trang form CÓ các ô ẩn đó.
FORM_INPUT_MARKERS: tuple[str, ...] = ('name="pageHistory"', 'name="fbzx"')


def parse_retry_after(value: str | None) -> float | None:
    if not value:
        return None
    value = value.strip()
    if value.isdigit():
        return float(value)
    try:
        moment = email.utils.parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=UTC)
    return max(0.0, (moment - datetime.now(UTC)).total_seconds())


def classify_response(status_code: int, body: str, headers: httpx.Headers) -> SubmitOutcome:
    engine = EngineUsed.HTTPX
    if status_code == 200:
        if not any(marker in body for marker in FORM_INPUT_MARKERS):
            return SubmitOutcome(OutcomeKind.SUCCESS, status_code, engine)
        return SubmitOutcome(
            OutcomeKind.VALIDATION, status_code, engine,
            error="Google trả lại trang form thay vì xác nhận: có câu trả lời không hợp lệ.",
        )
    if status_code in (429, 403):
        return SubmitOutcome(
            OutcomeKind.BLOCKED, status_code, engine,
            error="Google đang giới hạn số lần gửi.", retry_after=parse_retry_after(headers.get("Retry-After")),
        )
    if status_code == 400:
        return SubmitOutcome(OutcomeKind.VALIDATION, status_code, engine, error="Google từ chối dữ liệu (400).")
    if status_code == 401:
        return SubmitOutcome(OutcomeKind.FATAL, status_code, engine, error="Form yêu cầu đăng nhập Google.")
    if status_code in (404, 410):
        return SubmitOutcome(OutcomeKind.FATAL, status_code, engine, error="Form không còn tồn tại hoặc đã ngừng nhận phản hồi.")
    if status_code >= 500:
        return SubmitOutcome(OutcomeKind.SERVER, status_code, engine, error=f"Máy chủ Google lỗi ({status_code}).")
    return SubmitOutcome(OutcomeKind.UNKNOWN, status_code, engine, error=f"Phản hồi không mong đợi ({status_code}).")


class HttpSubmitter:
    def __init__(
        self,
        *,
        user_agent: str,
        proxy: str | None = None,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._owns_client = client is None
        self._client = client or httpx.AsyncClient(
            proxy=proxy, timeout=httpx.Timeout(timeout), follow_redirects=True,
            headers={"User-Agent": user_agent, "Accept-Language": "vi-VN,vi;q=0.9,en;q=0.8"},
        )

    async def __aenter__(self) -> HttpSubmitter:
        return self

    async def __aexit__(
        self, exc_type: type[BaseException] | None, exc: BaseException | None, tb: TracebackType | None
    ) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def submit(self, structure: ParsedFormStructure, payload: Sequence[tuple[str, str]]) -> SubmitOutcome:
        # urlencode giữ nguyên thứ tự và khóa lặp (checkbox nhiều lựa chọn)
        body = urlencode(list(payload)).encode("utf-8")
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Referer": structure.view_url,
            "Origin": "https://docs.google.com",
        }
        started = time.monotonic()
        try:
            response = await self._client.post(structure.submit_url, content=body, headers=headers)
        except httpx.TimeoutException:
            return SubmitOutcome(OutcomeKind.NETWORK, 0, EngineUsed.HTTPX, error="Hết thời gian chờ Google phản hồi.")
        except httpx.HTTPError as exc:
            return SubmitOutcome(OutcomeKind.NETWORK, 0, EngineUsed.HTTPX, error=f"Lỗi kết nối: {exc}")
        outcome = classify_response(response.status_code, response.text, response.headers)
        if outcome.kind == OutcomeKind.UNKNOWN:
            outcome.error = f"{outcome.error} sau {time.monotonic() - started:.1f} giây"
        return outcome
