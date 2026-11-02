"""Hiệu chỉnh tham số ẩn để bù sai lệch do làm tròn + cắt biên thang Likert (dev-notes SPEC-002)."""

from __future__ import annotations

import math

import numpy as np
from scipy import optimize

from app.services.spss.statistics import MAX_LATENT_R, cronbach_alpha, discretized_moments, mean_inter_item_correlation

CALIBRATION_SAMPLES = 4000
CALIBRATION_SEED = 20_241_102


def calibrate_latent_moments(
    target_mean: float, target_std: float, lo: int, hi: int, *, max_iter: int = 40, tol: float = 1e-4
) -> tuple[float, float]:
    """Tìm (μ_ẩn, σ_ẩn) sao cho sau khi làm tròn + cắt biên, mean/SD quan sát ≈ mục tiêu.

    Nếu SD mục tiêu không khả thi (VD mean 4.8 với SD 1.2 trên thang 1-5) sẽ trả về
    nghiệm gần nhất có thể.
    """
    epsilon = 1e-3
    mean_goal = min(max(target_mean, lo + epsilon), hi - epsilon)
    latent_std = max(target_std, 0.05)
    latent_mean = mean_goal

    for _ in range(max_iter):
        def mean_gap(mu: float, s: float = latent_std) -> float:
            return discretized_moments(mu, s, lo, hi)[0] - mean_goal

        bound = 10.0 * latent_std + 10.0
        latent_mean = float(optimize.brentq(mean_gap, lo - bound, hi + bound, xtol=1e-7))
        _, observed_std = discretized_moments(latent_mean, latent_std, lo, hi)
        if observed_std <= 1e-9 or abs(observed_std - target_std) < tol:
            break
        next_std = min(max(latent_std * target_std / observed_std, 0.05), 10.0)
        if abs(next_std - latent_std) < 1e-7:
            break
        latent_std = next_std

    return latent_mean, latent_std


def calibrate_latent_correlation(
    *,
    latent_mean: float,
    latent_std: float,
    lo: int,
    hi: int,
    k: int,
    target_alpha: float | None = None,
    target_r: float | None = None,
    n_samples: int = CALIBRATION_SAMPLES,
    seed: int = CALIBRATION_SEED,
) -> float:
    """Tìm r_ẩn để alpha (hoặc tương quan trung bình) của dữ liệu Likert rời rạc ≈ mục tiêu.

    Dùng Common Random Numbers theo mô hình nhân tố X_i = μ + σ(√r·F + √(1-r)·E_i),
    tương đương phân phối của ma trận hiệp phương sai đối xứng hợp chất ở Mục 5.2.B,
    nên chỉ số mục tiêu đơn điệu theo r và có thể tìm bằng chia đôi.
    """
    if target_alpha is None and target_r is None:
        raise ValueError("Cần target_alpha hoặc target_r")
    rng = np.random.default_rng(seed)
    factor = rng.standard_normal((n_samples, 1))
    noise = rng.standard_normal((n_samples, k))

    def metric(r: float) -> float:
        latent = latent_mean + latent_std * (math.sqrt(r) * factor + math.sqrt(1.0 - r) * noise)
        codes = np.clip(np.round(latent), lo, hi)
        if target_alpha is not None:
            return cronbach_alpha(codes)
        return mean_inter_item_correlation(codes)

    goal = float(target_alpha if target_alpha is not None else target_r)  # type: ignore[arg-type]
    low, high = 0.0, MAX_LATENT_R
    metric_high = metric(high)
    if not math.isfinite(metric_high) or metric_high < goal:
        return high
    metric_low = metric(low)
    if math.isfinite(metric_low) and metric_low >= goal:
        return low
    for _ in range(40):
        middle = (low + high) / 2.0
        value = metric(middle)
        if not math.isfinite(value) or value < goal:
            low = middle
        else:
            high = middle
        if high - low < 1e-4:
            break
    return (low + high) / 2.0
