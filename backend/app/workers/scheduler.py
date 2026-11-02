"""Poisson Jitter Scheduler (Mục 5.4.B spec): khoảng nghỉ phân phối mũ, tổng khớp thời lượng."""

from __future__ import annotations

import numpy as np


def poisson_delays(n: int, total_seconds: float, rng: np.random.Generator) -> np.ndarray:
    if n <= 0:
        return np.zeros(0)
    if total_seconds <= 0:
        return np.zeros(n)
    scale = total_seconds / n
    delays = rng.exponential(scale=scale, size=n)
    total = float(delays.sum())
    if total <= 0:
        return np.full(n, scale)
    return delays * (total_seconds / total)


def remaining_duration_seconds(duration_minutes: float, total_target: int, remaining: int) -> float:
    """Khi chạy tiếp sau tạm dừng: chỉ rải phần còn lại theo tỷ lệ số phản hồi chưa gửi."""
    if total_target <= 0 or remaining <= 0:
        return 0.0
    return duration_minutes * 60.0 * min(remaining, total_target) / total_target
