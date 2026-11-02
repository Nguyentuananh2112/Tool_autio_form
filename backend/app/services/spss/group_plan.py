"""Lập kế hoạch cho một nhóm tương quan SPSS: kiểm tra biến, hiệu chỉnh, lấy mẫu Likert."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

import numpy as np

from app.schemas.campaign_schema import SpssGroupConfig
from app.schemas.form_schema import ParsedQuestion
from app.services.spss.calibration import calibrate_latent_correlation, calibrate_latent_moments
from app.services.spss.scales import scale_values_for
from app.services.spss.statistics import MAX_LATENT_R, r_from_alpha


@dataclass(slots=True)
class GroupPlan:
    config: SpssGroupConfig
    questions: list[ParsedQuestion]
    scale: list[int]
    reversed_entries: frozenset[str]
    latent_mean: float
    latent_std: float
    latent_r: float

    @property
    def lo(self) -> int:
        return self.scale[0]

    @property
    def hi(self) -> int:
        return self.scale[-1]


def _collect_questions(
    group: SpssGroupConfig,
    questions_by_entry: Mapping[str, ParsedQuestion],
    grouped: dict[str, str],
    errors: list[str],
) -> tuple[list[ParsedQuestion], list[int] | None, bool]:
    label = f"Nhóm '{group.name}'"
    questions: list[ParsedQuestion] = []
    scale: list[int] | None = None
    valid = True
    for entry_id in group.entries:
        if entry_id in grouped:
            errors.append(f"{label}: entry {entry_id} đã thuộc nhóm '{grouped[entry_id]}'.")
            valid = False
            continue
        question = questions_by_entry.get(entry_id)
        if question is None:
            errors.append(f"{label}: không tìm thấy câu hỏi entry {entry_id}.")
            valid = False
            continue
        if not question.is_single_choice:
            errors.append(f"{label}: '{question.title}' không phải câu một lựa chọn kiểu thang đo.")
            valid = False
            continue
        values = scale_values_for(question)
        if len(values) < 2:
            errors.append(f"{label}: '{question.title}' cần ít nhất 2 mức đáp án.")
            valid = False
            continue
        if scale is None:
            scale = values
        elif values != scale:
            errors.append(
                f"{label}: '{question.title}' có thang {values[0]}-{values[-1]} ({len(values)} mức), "
                f"khác thang chung {scale[0]}-{scale[-1]} ({len(scale)} mức)."
            )
            valid = False
            continue
        grouped[entry_id] = group.name
        questions.append(question)
    return questions, scale, valid


def plan_group(
    group: SpssGroupConfig,
    questions_by_entry: Mapping[str, ParsedQuestion],
    grouped: dict[str, str],
    errors: list[str],
) -> GroupPlan | None:
    """Trả về kế hoạch đã hiệu chỉnh, hoặc None (và ghi lỗi vào `errors`)."""
    questions, scale, valid = _collect_questions(group, questions_by_entry, grouped, errors)
    if not valid or scale is None:
        return None
    lo, hi = scale[0], scale[-1]
    if not lo <= group.mean <= hi:
        errors.append(f"Nhóm '{group.name}': mean {group.mean} nằm ngoài thang đo [{lo}, {hi}].")
        return None

    k = len(questions)
    if group.calibrate:
        latent_mean, latent_std = calibrate_latent_moments(group.mean, group.std, lo, hi)
        if group.r is not None:
            latent_r = calibrate_latent_correlation(
                latent_mean=latent_mean, latent_std=latent_std, lo=lo, hi=hi, k=k, target_r=group.r
            )
        else:
            latent_r = calibrate_latent_correlation(
                latent_mean=latent_mean, latent_std=latent_std, lo=lo, hi=hi, k=k,
                target_alpha=group.alpha_target,
            )
    else:
        latent_mean, latent_std = group.mean, group.std
        latent_r = group.r if group.r is not None else r_from_alpha(group.alpha_target or 0.0, k)

    return GroupPlan(
        config=group,
        questions=questions,
        scale=scale,
        reversed_entries=frozenset(group.reversed_entries),
        latent_mean=latent_mean,
        latent_std=latent_std,
        latent_r=float(min(max(latent_r, 0.0), MAX_LATENT_R)),
    )


def sample_group_codes(plan: GroupPlan, n: int, rng: np.random.Generator) -> np.ndarray:
    """Mẫu Likert cùng chiều (chưa đảo item ngược) kích thước (n, k) — Mục 5.2.B bước 3–4."""
    k = len(plan.questions)
    variance = plan.latent_std**2
    mean_vec = np.full(k, plan.latent_mean)
    cov_matrix = np.full((k, k), plan.latent_r * variance)
    np.fill_diagonal(cov_matrix, variance)
    raw_samples = rng.multivariate_normal(mean=mean_vec, cov=cov_matrix, size=n)
    return np.clip(np.round(raw_samples), plan.lo, plan.hi).astype(int)
