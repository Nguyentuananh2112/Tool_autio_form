"""Chạy thử nhóm SPSS trong RAM và báo cáo alpha / mean / SD (endpoint preview-spss)."""

from __future__ import annotations

import math

import numpy as np

from app.schemas.campaign_schema import SpssGroupPreview, SpssItemPreview
from app.services.spss.group_plan import GroupPlan, sample_group_codes
from app.services.spss.statistics import cronbach_alpha, finite_or_none, mean_inter_item_correlation


def _item_previews(plan: GroupPlan, aligned: np.ndarray) -> list[SpssItemPreview]:
    observed = aligned.copy()
    items: list[SpssItemPreview] = []
    for j, question in enumerate(plan.questions):
        is_reversed = question.entry_id in plan.reversed_entries
        if is_reversed:
            observed[:, j] = plan.lo + plan.hi - aligned[:, j]
        values, counts = np.unique(observed[:, j], return_counts=True)
        count_map = dict(zip(values.tolist(), counts.tolist()))
        items.append(SpssItemPreview(
            entry_id=question.entry_id,
            title=question.title,
            is_reversed=is_reversed,
            mean=round(float(observed[:, j].mean()), 4),
            std=round(float(observed[:, j].std(ddof=1)), 4),
            distribution={
                option.label: int(count_map.get(code, 0))
                for option, code in zip(question.choice_options, plan.scale)
            },
        ))
    return items


def _warnings(plan: GroupPlan, alpha: float, achieved_mean: float, achieved_std: float) -> list[str]:
    group = plan.config
    warnings: list[str] = []
    if not math.isfinite(alpha):
        warnings.append("Không tính được Cronbach's Alpha (dữ liệu không có phương sai).")
    elif alpha < 0.7:
        warnings.append(f"Cronbach's Alpha = {alpha:.3f} < 0.7: tăng hệ số tương quan r hoặc số biến quan sát.")
    if group.alpha_target is not None and math.isfinite(alpha) and alpha < group.alpha_target - 0.03:
        warnings.append(f"Alpha dự kiến {alpha:.3f} thấp hơn mục tiêu {group.alpha_target:.2f}.")
    if abs(achieved_mean - group.mean) > 0.15:
        warnings.append(
            f"Mean đạt {achieved_mean:.2f} lệch mục tiêu {group.mean:.2f} (mean quá sát biên thang đo hoặc SD quá lớn)."
        )
    if abs(achieved_std - group.std) > 0.15:
        warnings.append(
            f"SD đạt {achieved_std:.2f} lệch mục tiêu {group.std:.2f}: tổ hợp mean/SD này khó đạt trên thang "
            f"{plan.lo}-{plan.hi}."
        )
    return warnings


def build_group_preview(plan: GroupPlan, n: int, rng: np.random.Generator) -> SpssGroupPreview:
    group = plan.config
    aligned = sample_group_codes(plan, n, rng)
    alpha = cronbach_alpha(aligned)
    achieved_mean = float(aligned.mean())
    achieved_std = float(aligned.std(axis=0, ddof=1).mean())
    return SpssGroupPreview(
        group_id=group.group_id,
        name=group.name,
        n_samples=n,
        n_items=len(plan.questions),
        cronbach_alpha=finite_or_none(alpha),
        alpha_target=group.alpha_target,
        mean_inter_item_r=finite_or_none(mean_inter_item_correlation(aligned)),
        target_r=group.r,
        latent_r=round(plan.latent_r, 4),
        target_mean=group.mean,
        achieved_mean=round(achieved_mean, 4),
        target_std=group.std,
        achieved_std=round(achieved_std, 4),
        items=_item_previews(plan, aligned),
        warnings=_warnings(plan, alpha, achieved_mean, achieved_std),
    )
