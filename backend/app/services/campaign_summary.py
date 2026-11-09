"""Tóm tắt kết quả chiến dịch cho thông báo kết thúc (màn 13): đếm, thời gian, lỗi gom theo lý do + cách xử lý."""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from enum import StrEnum

from app.models import Campaign, SubmissionLog
from app.schemas.campaign_api import CampaignSummary, FailureReason
from app.services.campaign_service import is_auto_paused


class FailureCategory(StrEnum):
    REJECTED = "REJECTED"  # 400 / Google trả lại form: dữ liệu không hợp lệ
    RATE_LIMITED = "RATE_LIMITED"  # 429 / 403
    NETWORK = "NETWORK"  # mất mạng, quá thời gian
    BROWSER = "BROWSER"  # trình duyệt dự phòng chưa sẵn sàng / lỗi
    FORM_CLOSED = "FORM_CLOSED"  # form đóng, cần đăng nhập…
    OTHER = "OTHER"


CATEGORY_TEXT: dict[FailureCategory, tuple[str, str]] = {
    FailureCategory.REJECTED: (
        "Google từ chối dữ liệu",
        "Form có câu bắt buộc chưa được trả lời hoặc câu hỏi đã đổi. Bấm \"Phân tích lại\" link ở bước Cấu hình, "
        "soát logic rồi gửi lại.",
    ),
    FailureCategory.RATE_LIMITED: (
        "Google giới hạn số lần gửi",
        "Chờ 15–30 phút rồi gửi lại; lần sau chọn \"Rải đều tự nhiên\" với thời gian dài hơn.",
    ),
    FailureCategory.NETWORK: (
        "Mất kết nối mạng",
        "Kiểm tra Internet / proxy rồi gửi lại — app chỉ gửi lại các phản hồi lỗi.",
    ),
    FailureCategory.BROWSER: (
        "Trình duyệt dự phòng gặp lỗi",
        "Vào Cài đặt → Trình duyệt dự phòng để tải lại trình duyệt, hoặc tắt tuỳ chọn trình duyệt dự phòng.",
    ),
    FailureCategory.FORM_CLOSED: (
        "Form không còn nhận câu trả lời",
        "Mở Google Form, bật lại \"Chấp nhận phản hồi\" (và tắt yêu cầu đăng nhập nếu có) rồi gửi lại.",
    ),
    FailureCategory.OTHER: ("Lỗi khác", "Xem chi tiết trong Nhật ký gửi; gửi lại sau ít phút."),
}


def categorize(log: SubmissionLog) -> FailureCategory:
    detail = (log.error_detail or "").casefold()
    if any(key in detail for key in ("ngừng nhận", "không còn tồn tại", "đăng nhập", "đã đóng")):
        return FailureCategory.FORM_CLOSED
    if "trình duyệt dự phòng" in detail or "lỗi trình duyệt" in detail:
        return FailureCategory.BROWSER
    if log.status_code in (429, 403):
        return FailureCategory.RATE_LIMITED
    if log.status_code == 400:
        return FailureCategory.REJECTED
    if log.status_code == 0:
        return FailureCategory.NETWORK
    return FailureCategory.OTHER


def failure_reasons(logs: Sequence[SubmissionLog]) -> list[FailureReason]:
    """Gom lỗi theo (loại, chi tiết Google báo), nhiều nhất lên đầu."""
    counts: Counter[tuple[FailureCategory, str]] = Counter(
        (categorize(log), (log.error_detail or "").strip()) for log in logs if not log.is_success
    )
    reasons = []
    for (category, detail), count in counts.most_common():
        title, fix = CATEGORY_TEXT[category]
        reasons.append(FailureReason(category=category.value, title=title, fix=fix, count=count, detail=detail or None))
    return reasons


def build_summary(campaign: Campaign, logs: Sequence[SubmissionLog]) -> CampaignSummary:
    times = sorted(log.executed_at for log in logs if log.executed_at is not None)
    duration = (times[-1] - times[0]).total_seconds() if len(times) >= 2 else 0.0
    return CampaignSummary(
        campaign_id=campaign.id,
        name=campaign.name,
        form_id=campaign.form_id,
        form_title=campaign.form.title,
        status=campaign.status,
        status_reason=campaign.status_reason,
        auto_paused=is_auto_paused(campaign.status, campaign.status_reason),
        total_target=campaign.total_target,
        completed_count=campaign.completed_count,
        failed_count=campaign.failed_count,
        remaining=max(campaign.total_target - campaign.completed_count - campaign.failed_count, 0),
        started_at=times[0] if times else None,
        finished_at=times[-1] if times else None,
        duration_seconds=round(duration, 1),
        reasons=failure_reasons(logs),
    )
