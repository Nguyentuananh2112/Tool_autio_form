"""Thái độ chung của từng người điền (Gaussian copula).

Mỗi nhóm thái độ có một nhân tố F ~ N(0, 1) cho mỗi người. Câu thuộc nhóm lấy biến ẩn
z = √λ·F + √(1−λ)·ε rồi đổi sang đáp án theo phân vị của trọng số người dùng đặt,
nên **tỷ lệ % từng đáp án giữ nguyên** mà các câu vẫn cùng cao / cùng thấp.
λ (phần chung với thái độ) lấy theo độ đồng đều người dùng chọn.
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
from scipy.stats import norm

from app.schemas.form_schema import ParsedOption
from app.schemas.logic_schema import Consistency, TextSentiment

LOADING: dict[Consistency, float] = {
    Consistency.VARIED: 0.3,
    Consistency.MODERATE: 0.55,
    Consistency.UNIFORM: 0.8,
}
# Ngưỡng nhân tố chia ba nhóm cảm xúc gần bằng nhau (Φ(±0,43) ≈ 1/3, 2/3)
SENTIMENT_CUT = 0.43


def item_latent(factor: np.ndarray, loading: float, rng: np.random.Generator) -> np.ndarray:
    noise = rng.standard_normal(factor.size)
    return np.sqrt(loading) * factor + np.sqrt(1.0 - loading) * noise


def copula_picks(
    options: Sequence[ParsedOption],
    weights: np.ndarray,
    ordered_index: Sequence[int],
    latent: np.ndarray,
    rng: np.random.Generator,
) -> np.ndarray | None:
    """Chỉ số option cho từng người. `ordered_index`: option thường xếp tiêu cực → tích cực.

    "Mục khác" không có thứ bậc: bốc độc lập theo đúng tỷ lệ của nó. Trả None nếu tổng trọng số = 0.
    """
    total = float(weights.sum())
    if total <= 0:
        return None
    other_index = next((i for i, option in enumerate(options) if option.is_other), None)
    ordered = np.asarray(ordered_index, dtype=int)
    ordered_weights = weights[ordered] if ordered.size else np.zeros(0)
    picks = np.full(latent.size, -1, dtype=int)
    if ordered_weights.sum() > 0:
        cumulative = np.cumsum(ordered_weights) / ordered_weights.sum()
        slot = np.searchsorted(cumulative, norm.cdf(latent), side="right")
        picks = ordered[np.minimum(slot, ordered.size - 1)]
    if other_index is not None and weights[other_index] > 0:
        is_other = rng.uniform(size=latent.size) < weights[other_index] / total
        picks = np.where(is_other | (picks < 0), other_index, picks)
    return picks


def sentiment_of(factor_value: float) -> TextSentiment:
    if factor_value > SENTIMENT_CUT:
        return TextSentiment.POSITIVE
    if factor_value < -SENTIMENT_CUT:
        return TextSentiment.NEGATIVE
    return TextSentiment.NEUTRAL


def pool_for(
    pool: Sequence[str], labels: dict[str, TextSentiment], wanted: TextSentiment
) -> list[str]:
    """Câu mẫu hợp cảm xúc; thiếu thì lùi về trung lập, rồi cả pool."""
    exact = [text for text in pool if labels.get(text, TextSentiment.NEUTRAL) == wanted]
    if exact:
        return exact
    neutral = [text for text in pool if labels.get(text, TextSentiment.NEUTRAL) == TextSentiment.NEUTRAL]
    return neutral or list(pool)
