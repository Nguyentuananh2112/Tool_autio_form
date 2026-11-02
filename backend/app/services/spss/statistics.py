"""Thống kê độ tin cậy thang đo: Cronbach's Alpha, tương quan trung bình, Spearman-Brown."""

from __future__ import annotations

import math

import numpy as np
from scipy import stats

MAX_LATENT_R = 0.99


def cronbach_alpha(data: np.ndarray) -> float:
    """α = k/(k-1) · (1 - ΣVar(Xi) / Var(ΣXi)). Trả về NaN nếu không xác định."""
    matrix = np.asarray(data, dtype=float)
    if matrix.ndim != 2 or matrix.shape[0] < 2 or matrix.shape[1] < 2:
        return float("nan")
    k = matrix.shape[1]
    item_variance_sum = matrix.var(axis=0, ddof=1).sum()
    total_variance = matrix.sum(axis=1).var(ddof=1)
    if total_variance <= 0:
        return float("nan")
    return float(k / (k - 1) * (1.0 - item_variance_sum / total_variance))


def mean_inter_item_correlation(data: np.ndarray) -> float:
    matrix = np.asarray(data, dtype=float)
    if matrix.ndim != 2 or matrix.shape[0] < 3 or matrix.shape[1] < 2:
        return float("nan")
    with np.errstate(invalid="ignore", divide="ignore"):
        corr = np.corrcoef(matrix, rowvar=False)
    upper = corr[np.triu_indices_from(corr, k=1)]
    upper = upper[np.isfinite(upper)]
    return float(upper.mean()) if upper.size else float("nan")


def r_from_alpha(alpha: float, k: int) -> float:
    """Nghịch đảo công thức Spearman-Brown chuẩn hóa: α = k·r / (1 + (k-1)·r)."""
    if k < 2:
        return 0.0
    denominator = k - (k - 1) * alpha
    if denominator <= 0:
        return MAX_LATENT_R
    return float(min(max(alpha / denominator, 0.0), MAX_LATENT_R))


def alpha_from_r(r: float, k: int) -> float:
    return float(k * r / (1 + (k - 1) * r)) if k >= 2 else float("nan")


def finite_or_none(value: float | None) -> float | None:
    return None if value is None or not math.isfinite(value) else round(float(value), 4)


def discretized_moments(latent_mean: float, latent_std: float, lo: int, hi: int) -> tuple[float, float]:
    """Mean & SD chính xác của clip(round(X), lo, hi) với X ~ N(latent_mean, latent_std²)."""
    values = np.arange(lo, hi + 1, dtype=float)
    upper = stats.norm.cdf((values + 0.5 - latent_mean) / latent_std)
    lower = stats.norm.cdf((values - 0.5 - latent_mean) / latent_std)
    upper[-1] = 1.0
    lower[0] = 0.0
    probabilities = upper - lower
    mean = float((probabilities * values).sum())
    variance = float((probabilities * values**2).sum()) - mean**2
    return mean, math.sqrt(max(variance, 0.0))
