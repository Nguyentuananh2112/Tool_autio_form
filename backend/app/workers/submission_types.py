"""Kiểu dữ liệu chung cho kết quả một lần gửi phản hồi (HTTPX hoặc trình duyệt)."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum

from app.models.submission_log import EngineUsed


class OutcomeKind(StrEnum):
    SUCCESS = "SUCCESS"
    BLOCKED = "BLOCKED"  # 429 / 403: Google đang giới hạn → giãn nhịp, quá nhiều lần thì tạm dừng
    VALIDATION = "VALIDATION"  # 400 hoặc Google trả lại form: dữ liệu không hợp lệ
    NETWORK = "NETWORK"  # mất mạng, hết thời gian chờ: thử lại
    SERVER = "SERVER"  # 5xx: thử lại
    FATAL = "FATAL"  # form đã đóng / không tồn tại / cần đăng nhập: dừng chiến dịch
    UNKNOWN = "UNKNOWN"


RETRYABLE_KINDS = frozenset({OutcomeKind.NETWORK, OutcomeKind.SERVER})


@dataclass(slots=True)
class SubmitOutcome:
    kind: OutcomeKind
    status_code: int
    engine: EngineUsed
    error: str | None = None
    retry_after: float | None = None

    @property
    def ok(self) -> bool:
        return self.kind == OutcomeKind.SUCCESS


def payload_to_json(payload: Sequence[tuple[str, str]]) -> dict[str, list[str] | str]:
    """list[tuple] → dict để lưu `submission_logs.payload_sent`; khóa lặp (checkbox) gom thành list."""
    grouped: dict[str, list[str]] = {}
    for key, value in payload:
        grouped.setdefault(key, []).append(value)
    return {key: values[0] if key in ("fvv", "pageHistory", "fbzx") else values for key, values in grouped.items()}
