"""Sinh N bộ câu trả lời hoàn chỉnh cho một Google Form (Mục 5.2 SPECIFICATION.md).

Gồm:
    A. Câu hỏi độc lập theo trọng số (Radio/Dropdown/Scale/Grid) và xác suất độc lập (Checkbox).
    B. Nhóm câu hỏi Likert tương quan theo mô hình nhân tố ẩn (Multivariate Normal) để đạt
       Cronbach's Alpha mục tiêu. Có bước hiệu chỉnh tham số ẩn để bù sai lệch do làm tròn
       và cắt biên [scale_min, scale_max] (nếu không, mean bị kéo về giữa thang và alpha giảm).
    C. Tính đường đi rẽ nhánh `pageHistory` và loại bỏ câu trả lời ở các trang không đi qua.

Module thuần CPU: trong code async hãy gọi qua `await asyncio.to_thread(generator.generate, n)`.
"""

from __future__ import annotations

import logging
import math
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date, time, timedelta

import numpy as np
import pandas as pd
from scipy import optimize, stats

from app.schemas.campaign_schema import (
    QuestionRuleConfig,
    RuleStrategy,
    SpssGroupConfig,
    SpssGroupPreview,
    SpssItemPreview,
)
from app.schemas.form_schema import (
    BRANCHING_TYPES,
    OTHER_OPTION_VALUE,
    NavigationAction,
    ParsedFormStructure,
    ParsedOption,
    ParsedQuestion,
    QuestionType,
    decode_jump,
)

logger = logging.getLogger(__name__)

TextMutator = Callable[[str, np.random.Generator], str]

ANSWER_KIND_CHOICE = "CHOICE"
ANSWER_KIND_TEXT = "TEXT"
ANSWER_KIND_DATE = "DATE"
ANSWER_KIND_TIME = "TIME"

DEFAULT_CHECKBOX_PROBABILITY = 50.0
DEFAULT_TIME_START = time(8, 0)
DEFAULT_TIME_END = time(21, 0)
MAX_LATENT_R = 0.99
CALIBRATION_SAMPLES = 4000
CALIBRATION_SEED = 20_241_102


class GeneratorConfigError(ValueError):
    """Cấu hình sinh dữ liệu không hợp lệ; `errors` chứa danh sách lỗi hiển thị cho người dùng."""

    def __init__(self, errors: list[str]) -> None:
        self.errors = errors
        super().__init__("; ".join(errors))


# ============================================================================ output
@dataclass(slots=True)
class Answer:
    values: list[str]
    other_text: str | None = None
    kind: str = ANSWER_KIND_CHOICE
    # Mã số phục vụ xuất SPSS (Likert = điểm, trắc nghiệm = thứ tự lựa chọn từ 1)
    numeric_value: float | None = None


@dataclass(slots=True)
class GeneratedResponse:
    sequence_number: int
    answers: dict[str, Answer]
    page_history: list[int] = field(default_factory=lambda: [0])

    @property
    def page_history_str(self) -> str:
        return ",".join(map(str, self.page_history))


def build_payload_tuples(response: GeneratedResponse, fbzx: str | None) -> list[tuple[str, str]]:
    """Đóng gói thành list[tuple] cho POST /formResponse (Mục 5.4.A)."""
    payload: list[tuple[str, str]] = []
    for entry_id, answer in response.answers.items():
        key = f"entry.{entry_id}"
        if answer.kind == ANSWER_KIND_DATE:
            year, month, day = answer.values[0].split("-")
            payload.extend(
                [(f"{key}_year", str(int(year))), (f"{key}_month", str(int(month))), (f"{key}_day", str(int(day)))]
            )
            continue
        if answer.kind == ANSWER_KIND_TIME:
            hour, minute = answer.values[0].split(":")[:2]
            payload.extend([(f"{key}_hour", hour.zfill(2)), (f"{key}_minute", minute.zfill(2))])
            continue
        for value in answer.values:
            payload.append((key, value))
        if answer.other_text is not None:
            payload.append((f"{key}.other_option_response", answer.other_text))
    payload.append(("fvv", "1"))
    payload.append(("pageHistory", response.page_history_str))
    if fbzx:
        payload.append(("fbzx", fbzx))
    return payload


# ======================================================================== statistics
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


def _finite_or_none(value: float) -> float | None:
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


def scale_values_for(question: ParsedQuestion) -> list[int]:
    """Giá trị số của thang đo: dùng giá trị thật nếu là dãy số nguyên liên tiếp, ngược lại mã 1..K."""
    options = question.choice_options
    try:
        numbers = [int(option.value.strip()) for option in options]
    except ValueError:
        numbers = []
    if numbers and all(b - a == 1 for a, b in zip(numbers, numbers[1:])):
        return numbers
    return list(range(1, len(options) + 1))


# ===================================================================== group planning
@dataclass(slots=True)
class _GroupPlan:
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


# ========================================================================= generator
class SurveyDataGenerator:
    def __init__(
        self,
        structure: ParsedFormStructure,
        rules: Sequence[QuestionRuleConfig] | Mapping[str, QuestionRuleConfig] | None = None,
        spss_groups: Sequence[SpssGroupConfig] | None = None,
        *,
        seed: int | None = None,
        text_mutator: TextMutator | None = None,
    ) -> None:
        self.structure = structure
        if rules is None:
            self._rules: dict[str, QuestionRuleConfig] = {}
        elif isinstance(rules, Mapping):
            self._rules = {rule.entry_id: rule for rule in rules.values()}
        else:
            self._rules = {rule.entry_id: rule for rule in rules}
        self._groups: list[SpssGroupConfig] = list(spss_groups or [])
        self._seed = seed
        self._rng = np.random.default_rng(seed)
        self._text_mutator = text_mutator

        self._questions: dict[str, ParsedQuestion] = {q.entry_id: q for q in structure.questions}
        self._questions_by_page: dict[int, list[ParsedQuestion]] = {}
        for question in structure.questions:
            self._questions_by_page.setdefault(question.page_index, []).append(question)
        self._sections_by_page = {section.page_index: section for section in structure.sections}
        self._page_of_section: dict[int, int] = {
            s.section_item_id: s.page_index for s in structure.sections if s.section_item_id is not None
        }
        self._option_jumps: dict[str, dict[str, int | None]] = {
            q.entry_id: {o.value: o.jump_to_section_id for o in q.options}
            for q in structure.questions
            if q.type_id in BRANCHING_TYPES
        }

        self._plans: list[_GroupPlan] | None = None
        self.warnings: list[str] = []

    # ------------------------------------------------------------------ validation
    def validate(self) -> list[str]:
        """Kiểm tra cấu hình, hiệu chỉnh các nhóm SPSS. Raise GeneratorConfigError nếu có lỗi."""
        errors: list[str] = []
        warnings: list[str] = []

        for entry_id in self._rules:
            if entry_id not in self._questions:
                warnings.append(f"Luật cho entry {entry_id} không khớp câu hỏi nào trong form, sẽ bị bỏ qua.")

        grouped: dict[str, str] = {}
        plans: list[_GroupPlan] = []
        group_ids: set[str] = set()
        for group in self._groups:
            if group.group_id in group_ids:
                errors.append(f"Trùng group_id '{group.group_id}'.")
                continue
            group_ids.add(group.group_id)
            plan = self._plan_group(group, grouped, errors)
            if plan is not None:
                plans.append(plan)

        for question in self.structure.questions:
            if question.entry_id in grouped:
                continue
            self._validate_question(question, self._rules.get(question.entry_id), errors, warnings)

        if errors:
            raise GeneratorConfigError(errors)
        self._plans = plans
        self.warnings = warnings
        return warnings

    def _plan_group(
        self, group: SpssGroupConfig, grouped: dict[str, str], errors: list[str]
    ) -> _GroupPlan | None:
        label = f"Nhóm '{group.name}'"
        questions: list[ParsedQuestion] = []
        scale: list[int] | None = None
        valid = True
        for entry_id in group.entries:
            if entry_id in grouped:
                errors.append(f"{label}: entry {entry_id} đã thuộc nhóm '{grouped[entry_id]}'.")
                valid = False
                continue
            question = self._questions.get(entry_id)
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

        if not valid or scale is None:
            return None
        lo, hi = scale[0], scale[-1]
        if not lo <= group.mean <= hi:
            errors.append(f"{label}: mean {group.mean} nằm ngoài thang đo [{lo}, {hi}].")
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

        return _GroupPlan(
            config=group,
            questions=questions,
            scale=scale,
            reversed_entries=frozenset(group.reversed_entries),
            latent_mean=latent_mean,
            latent_std=latent_std,
            latent_r=float(min(max(latent_r, 0.0), MAX_LATENT_R)),
        )

    def _validate_question(
        self,
        question: ParsedQuestion,
        rule: QuestionRuleConfig | None,
        errors: list[str],
        warnings: list[str],
    ) -> None:
        label = f"'{question.title}'"
        strategy = rule.strategy if rule else RuleStrategy.AUTO

        if strategy == RuleStrategy.SKIP:
            if question.is_required:
                errors.append(f"{label} là câu bắt buộc, không thể bỏ qua (SKIP).")
            return

        if strategy == RuleStrategy.FIXED:
            assert rule is not None
            fixed = rule.fixed_value if isinstance(rule.fixed_value, list) else [rule.fixed_value]
            if question.options:
                valid_values = {option.value for option in question.options}
                invalid = [value for value in fixed if value not in valid_values]
                if invalid:
                    errors.append(f"{label}: giá trị cố định {invalid} không có trong danh sách lựa chọn.")
                if not question.is_multi_select and len(fixed) > 1:
                    errors.append(f"{label}: câu một lựa chọn chỉ nhận 1 giá trị cố định.")
                if OTHER_OPTION_VALUE in fixed and not rule.other_text_pool:
                    errors.append(f"{label}: chọn 'Mục khác' cần nhập other_text_pool.")
            return

        if question.is_text:
            if not (rule and rule.text_pool):
                if question.is_required:
                    errors.append(f"{label} là câu tự luận bắt buộc nhưng chưa có câu trả lời mẫu (text_pool / AI pool).")
                else:
                    warnings.append(f"{label} chưa có câu trả lời mẫu, sẽ bỏ trống.")
            return

        if question.type_id in (QuestionType.DATE, QuestionType.TIME):
            return

        if rule and rule.weights:
            known = {option.value for option in question.options}
            unknown = [key for key in rule.weights if key not in known]
            if unknown:
                warnings.append(f"{label}: bỏ qua trọng số của đáp án không tồn tại {unknown}.")

        options, weights = self._resolve_weights(question, rule)
        other_index = next((i for i, option in enumerate(options) if option.is_other), None)
        other_weight = weights[other_index] if other_index is not None else 0.0
        if other_weight > 0 and not (rule and rule.other_text_pool):
            errors.append(f"{label}: 'Mục khác' có trọng số > 0 nhưng chưa nhập other_text_pool.")

        if question.is_multi_select:
            if rule and rule.min_checked > len(options):
                errors.append(f"{label}: min_checked vượt quá số lựa chọn ({len(options)}).")
        elif weights.sum() <= 0:
            if question.is_required:
                errors.append(f"{label}: tổng trọng số bằng 0 cho câu bắt buộc.")
            else:
                warnings.append(f"{label}: tổng trọng số bằng 0, câu này sẽ bị bỏ trống.")
        elif rule and rule.weights and abs(weights.sum() - 100.0) > 0.5:
            warnings.append(f"{label}: tổng trọng số = {weights.sum():.1f} (khác 100), sẽ được chuẩn hóa.")

    # ----------------------------------------------------------------- generation
    def _ensure_plans(self) -> list[_GroupPlan]:
        if self._plans is None:
            self.validate()
        assert self._plans is not None
        return self._plans

    def generate(self, n: int, *, start_sequence: int = 1) -> list[GeneratedResponse]:
        if n < 1:
            raise ValueError("Số mẫu cần sinh phải >= 1")
        plans = self._ensure_plans()

        columns: dict[str, list[Answer | None]] = {}
        for plan in plans:
            columns.update(self._generate_group_columns(plan, n))
        for question in self.structure.questions:
            if question.entry_id not in columns:
                columns[question.entry_id] = self._generate_question_column(
                    question, self._rules.get(question.entry_id), n
                )

        responses: list[GeneratedResponse] = []
        ordered_entries = [q.entry_id for q in self.structure.questions]
        for i in range(n):
            raw_answers = {
                entry_id: columns[entry_id][i]
                for entry_id in ordered_entries
                if columns[entry_id][i] is not None
            }
            pages = self.build_page_history(raw_answers)  # type: ignore[arg-type]
            visited = set(pages)
            answers: dict[str, Answer] = {
                entry_id: answer  # type: ignore[misc]
                for entry_id, answer in raw_answers.items()
                if self._questions[entry_id].page_index in visited
            }
            responses.append(GeneratedResponse(sequence_number=start_sequence + i, answers=answers, page_history=pages))
        return responses

    def _sample_group_codes(self, plan: _GroupPlan, n: int, rng: np.random.Generator) -> np.ndarray:
        """Mẫu Likert cùng chiều (chưa đảo item ngược) kích thước (n, k)."""
        k = len(plan.questions)
        variance = plan.latent_std**2
        mean_vec = np.full(k, plan.latent_mean)
        cov_matrix = np.full((k, k), plan.latent_r * variance)
        np.fill_diagonal(cov_matrix, variance)
        raw_samples = rng.multivariate_normal(mean=mean_vec, cov=cov_matrix, size=n)
        return np.clip(np.round(raw_samples), plan.lo, plan.hi).astype(int)

    def _generate_group_columns(self, plan: _GroupPlan, n: int) -> dict[str, list[Answer | None]]:
        codes = self._sample_group_codes(plan, n, self._rng)
        columns: dict[str, list[Answer | None]] = {}
        for j, question in enumerate(plan.questions):
            column = codes[:, j]
            if question.entry_id in plan.reversed_entries:
                column = plan.lo + plan.hi - column
            options = question.choice_options
            columns[question.entry_id] = [
                Answer(values=[options[int(code) - plan.lo].value], numeric_value=float(code))
                for code in column
            ]
        return columns

    def _generate_question_column(
        self, question: ParsedQuestion, rule: QuestionRuleConfig | None, n: int
    ) -> list[Answer | None]:
        strategy = rule.strategy if rule else RuleStrategy.AUTO
        if strategy == RuleStrategy.SKIP:
            return [None] * n
        if strategy == RuleStrategy.FIXED:
            assert rule is not None
            return self._fixed_column(question, rule, n)

        mask = self._answer_mask(question, rule, n)
        if question.is_text:
            return self._text_column(rule, mask)
        if question.type_id == QuestionType.DATE:
            return self._date_column(rule, mask)
        if question.type_id == QuestionType.TIME:
            return self._time_column(rule, mask)
        if question.is_multi_select:
            return self._checkbox_column(question, rule, mask)
        return self._single_choice_column(question, rule, mask)

    def _answer_mask(self, question: ParsedQuestion, rule: QuestionRuleConfig | None, n: int) -> np.ndarray:
        if question.is_required or rule is None or rule.answer_rate >= 100.0:
            return np.ones(n, dtype=bool)
        return self._rng.uniform(0.0, 100.0, size=n) < rule.answer_rate

    def _resolve_weights(
        self, question: ParsedQuestion, rule: QuestionRuleConfig | None
    ) -> tuple[list[ParsedOption], np.ndarray]:
        options = list(question.options)
        if rule and rule.weights:
            weights = np.array([max(float(rule.weights.get(o.value, 0.0)), 0.0) for o in options])
        elif question.is_multi_select:
            weights = np.array([0.0 if o.is_other else DEFAULT_CHECKBOX_PROBABILITY for o in options])
        else:
            weights = np.array([0.0 if o.is_other else 1.0 for o in options])
        if question.is_multi_select:
            weights = np.clip(weights, 0.0, 100.0)
        return options, weights

    def _numeric_codes(self, question: ParsedQuestion) -> dict[str, float]:
        choice_options = question.choice_options
        values = scale_values_for(question)
        codes = {option.value: float(value) for option, value in zip(choice_options, values)}
        codes[OTHER_OPTION_VALUE] = float(len(choice_options) + 1)
        return codes

    def _pick_text(self, pool: list[str]) -> str:
        text = pool[int(self._rng.integers(len(pool)))]
        if self._text_mutator is not None:
            text = self._text_mutator(text, self._rng)
        return text

    def _single_choice_column(
        self, question: ParsedQuestion, rule: QuestionRuleConfig | None, mask: np.ndarray
    ) -> list[Answer | None]:
        n = mask.size
        options, weights = self._resolve_weights(question, rule)
        total = weights.sum()
        if total <= 0:
            return [None] * n
        probabilities = weights / total
        picks = self._rng.choice(len(options), size=n, p=probabilities)
        codes = self._numeric_codes(question)
        other_pool = rule.other_text_pool if rule else []

        column: list[Answer | None] = []
        for i in range(n):
            if not mask[i]:
                column.append(None)
                continue
            option = options[int(picks[i])]
            if option.is_other:
                column.append(
                    Answer(
                        values=[OTHER_OPTION_VALUE],
                        other_text=self._pick_text(other_pool),
                        numeric_value=codes[OTHER_OPTION_VALUE],
                    )
                )
            else:
                column.append(Answer(values=[option.value], numeric_value=codes.get(option.value)))
        return column

    def _checkbox_column(
        self, question: ParsedQuestion, rule: QuestionRuleConfig | None, mask: np.ndarray
    ) -> list[Answer | None]:
        n = mask.size
        options, probabilities = self._resolve_weights(question, rule)
        k = len(options)
        other_pool = rule.other_text_pool if rule else []
        fillable = np.array([not (o.is_other and not other_pool) for o in options])

        min_checked = rule.min_checked if rule else 0
        if question.is_required:
            min_checked = max(min_checked, 1)
        min_checked = min(min_checked, int(fillable.sum()))
        max_checked = min(rule.max_checked if rule and rule.max_checked else k, k)
        max_checked = max(max_checked, min_checked)

        draws = self._rng.uniform(0.0, 100.0, size=(n, k))
        selected = draws < probabilities  # 0% không bao giờ chọn, 100% luôn chọn

        column: list[Answer | None] = []
        for i in range(n):
            if not mask[i]:
                column.append(None)
                continue
            chosen = [j for j in np.flatnonzero(selected[i]) if fillable[j]]

            if len(chosen) < min_checked:
                # Lấy bù theo trọng số cao nhất (hòa thì ngẫu nhiên)
                remaining = [j for j in range(k) if fillable[j] and j not in chosen]
                tie_breaker = self._rng.random(k)
                remaining.sort(key=lambda j: (-probabilities[j], tie_breaker[j]))
                chosen.extend(remaining[: min_checked - len(chosen)])
            if len(chosen) > max_checked:
                chosen = list(self._rng.choice(chosen, size=max_checked, replace=False))

            if not chosen:
                column.append(None)
                continue
            chosen_sorted = sorted(int(j) for j in chosen)
            values = [options[j].value for j in chosen_sorted]
            other_text = (
                self._pick_text(other_pool) if any(options[j].is_other for j in chosen_sorted) else None
            )
            column.append(Answer(values=values, other_text=other_text))
        return column

    def _text_column(self, rule: QuestionRuleConfig | None, mask: np.ndarray) -> list[Answer | None]:
        pool = rule.text_pool if rule else []
        if not pool:
            return [None] * mask.size
        return [
            Answer(values=[self._pick_text(pool)], kind=ANSWER_KIND_TEXT) if mask[i] else None
            for i in range(mask.size)
        ]

    def _date_column(self, rule: QuestionRuleConfig | None, mask: np.ndarray) -> list[Answer | None]:
        end = rule.date_end if rule and rule.date_end else date.today()
        start = rule.date_start if rule and rule.date_start else end - timedelta(days=365)
        span = (end - start).days
        offsets = self._rng.integers(0, span + 1, size=mask.size)
        return [
            Answer(values=[(start + timedelta(days=int(offsets[i]))).isoformat()], kind=ANSWER_KIND_DATE)
            if mask[i] else None
            for i in range(mask.size)
        ]

    def _time_column(self, rule: QuestionRuleConfig | None, mask: np.ndarray) -> list[Answer | None]:
        start = rule.time_start if rule and rule.time_start else DEFAULT_TIME_START
        end = rule.time_end if rule and rule.time_end else DEFAULT_TIME_END
        start_minutes = start.hour * 60 + start.minute
        end_minutes = end.hour * 60 + end.minute
        picks = self._rng.integers(start_minutes, end_minutes + 1, size=mask.size)
        return [
            Answer(values=[f"{int(picks[i]) // 60:02d}:{int(picks[i]) % 60:02d}"], kind=ANSWER_KIND_TIME)
            if mask[i] else None
            for i in range(mask.size)
        ]

    def _fixed_column(self, question: ParsedQuestion, rule: QuestionRuleConfig, n: int) -> list[Answer | None]:
        fixed = rule.fixed_value if isinstance(rule.fixed_value, list) else [str(rule.fixed_value)]
        if question.is_text:
            kind = ANSWER_KIND_TEXT
        elif question.type_id == QuestionType.DATE:
            kind = ANSWER_KIND_DATE
        elif question.type_id == QuestionType.TIME:
            kind = ANSWER_KIND_TIME
        else:
            kind = ANSWER_KIND_CHOICE
        codes = self._numeric_codes(question) if question.options else {}
        has_other = OTHER_OPTION_VALUE in fixed
        column: list[Answer | None] = []
        for _ in range(n):
            other_text = self._pick_text(rule.other_text_pool) if has_other and rule.other_text_pool else None
            numeric = codes.get(fixed[0]) if len(fixed) == 1 and not question.is_multi_select else None
            column.append(Answer(values=list(fixed), other_text=other_text, kind=kind, numeric_value=numeric))
        return column

    # ------------------------------------------------------------- page history
    def _next_page_action(
        self, page_index: int, answers: Mapping[str, Answer]
    ) -> tuple[NavigationAction, int | None]:
        jump: int | None = None
        for question in self._questions_by_page.get(page_index, []):
            jumps = self._option_jumps.get(question.entry_id)
            answer = answers.get(question.entry_id)
            if not jumps or answer is None or not answer.values:
                continue
            option_jump = jumps.get(answer.values[0])
            if option_jump is not None:
                jump = option_jump  # Google Forms áp dụng câu rẽ nhánh cuối cùng trong trang
        if jump is not None:
            return decode_jump(jump)
        section = self._sections_by_page.get(page_index)
        if section is None:
            return NavigationAction.NEXT_PAGE, None
        return section.navigation_action, section.jump_to_section_id

    def build_page_history(self, answers: Mapping[str, Answer]) -> list[int]:
        """Mô phỏng người điền đi qua các trang theo luật rẽ nhánh (Mục 5.2.C)."""
        total_pages = self.structure.total_pages
        current = 0
        visited = [0]
        visited_set = {0}
        while True:
            action, target = self._next_page_action(current, answers)
            if action == NavigationAction.SUBMIT:
                break
            next_page = current + 1
            if action == NavigationAction.GO_TO_PAGE and target is not None:
                resolved = self._page_of_section.get(target)
                if resolved is None:
                    logger.warning("Section đích %s không tồn tại, chuyển sang trang kế tiếp", target)
                else:
                    next_page = resolved
            if next_page >= total_pages or next_page in visited_set:
                # Hết trang, hoặc nhảy ngược về trang đã đi qua (tránh vòng lặp vô hạn) -> nộp
                break
            visited.append(next_page)
            visited_set.add(next_page)
            current = next_page
        return visited

    # ------------------------------------------------------------------- preview
    def preview_spss_groups(self, n: int = 200) -> list[SpssGroupPreview]:
        """Chạy thử n mẫu trong RAM (không ảnh hưởng RNG sinh thật) và báo cáo alpha/mean/SD."""
        if n < 3:
            raise ValueError("Cần ít nhất 3 mẫu để tính thống kê")
        plans = self._ensure_plans()
        rng = np.random.default_rng(self._seed)
        previews: list[SpssGroupPreview] = []

        for plan in plans:
            group = plan.config
            aligned = self._sample_group_codes(plan, n, rng)
            observed = aligned.copy()
            items: list[SpssItemPreview] = []
            for j, question in enumerate(plan.questions):
                is_reversed = question.entry_id in plan.reversed_entries
                if is_reversed:
                    observed[:, j] = plan.lo + plan.hi - aligned[:, j]
                values, counts = np.unique(observed[:, j], return_counts=True)
                count_map = dict(zip(values.tolist(), counts.tolist()))
                distribution = {
                    option.label: int(count_map.get(code, 0))
                    for option, code in zip(question.choice_options, plan.scale)
                }
                items.append(
                    SpssItemPreview(
                        entry_id=question.entry_id,
                        title=question.title,
                        is_reversed=is_reversed,
                        mean=round(float(observed[:, j].mean()), 4),
                        std=round(float(observed[:, j].std(ddof=1)), 4),
                        distribution=distribution,
                    )
                )

            alpha = cronbach_alpha(aligned)
            inter_r = mean_inter_item_correlation(aligned)
            achieved_mean = float(aligned.mean())
            achieved_std = float(aligned.std(axis=0, ddof=1).mean())

            warnings: list[str] = []
            if not math.isfinite(alpha):
                warnings.append("Không tính được Cronbach's Alpha (dữ liệu không có phương sai).")
            elif alpha < 0.7:
                warnings.append(f"Cronbach's Alpha = {alpha:.3f} < 0.7: tăng hệ số tương quan r hoặc số biến quan sát.")
            if group.alpha_target is not None and math.isfinite(alpha) and alpha < group.alpha_target - 0.03:
                warnings.append(f"Alpha dự kiến {alpha:.3f} thấp hơn mục tiêu {group.alpha_target:.2f}.")
            if abs(achieved_mean - group.mean) > 0.15:
                warnings.append(
                    f"Mean đạt {achieved_mean:.2f} lệch mục tiêu {group.mean:.2f} "
                    "(mean quá sát biên thang đo hoặc SD quá lớn)."
                )
            if abs(achieved_std - group.std) > 0.15:
                warnings.append(
                    f"SD đạt {achieved_std:.2f} lệch mục tiêu {group.std:.2f}: tổ hợp mean/SD này khó đạt trên thang "
                    f"{plan.lo}-{plan.hi}."
                )

            previews.append(
                SpssGroupPreview(
                    group_id=group.group_id,
                    name=group.name,
                    n_samples=n,
                    n_items=len(plan.questions),
                    cronbach_alpha=_finite_or_none(alpha),
                    alpha_target=group.alpha_target,
                    mean_inter_item_r=_finite_or_none(inter_r),
                    target_r=group.r,
                    latent_r=round(plan.latent_r, 4),
                    target_mean=group.mean,
                    achieved_mean=round(achieved_mean, 4),
                    target_std=group.std,
                    achieved_std=round(achieved_std, 4),
                    items=items,
                    warnings=warnings,
                )
            )
        return previews


# ============================================================================ export
def responses_to_dataframe(
    structure: ParsedFormStructure, responses: Sequence[GeneratedResponse], *, numeric: bool = True
) -> pd.DataFrame:
    """Bảng dữ liệu kiểu SPSS: 1 dòng / phản hồi; Checkbox tách thành các biến nhị phân 0/1."""
    used_names: set[str] = set()

    def column_name(base: str, entry_id: str) -> str:
        name = base if base not in used_names else f"{base} ({entry_id})"
        used_names.add(name)
        return name

    column_specs: list[tuple[str, ParsedQuestion, ParsedOption | None]] = []
    for question in structure.questions:
        if question.is_multi_select:
            for option in question.options:
                column_specs.append((column_name(f"{question.title} [{option.label}]", question.entry_id), question, option))
        else:
            column_specs.append((column_name(question.title, question.entry_id), question, None))

    records: list[dict[str, object]] = []
    for response in responses:
        record: dict[str, object] = {
            "sequence_number": response.sequence_number,
            "page_history": response.page_history_str,
        }
        for name, question, option in column_specs:
            answer = response.answers.get(question.entry_id)
            if answer is None:
                record[name] = None
            elif option is not None:
                record[name] = 1 if option.value in answer.values else 0
            elif numeric and answer.numeric_value is not None:
                record[name] = answer.numeric_value
            elif answer.values and answer.values[0] == OTHER_OPTION_VALUE:
                record[name] = answer.other_text
            else:
                record[name] = ", ".join(answer.values)
        records.append(record)

    return pd.DataFrame.from_records(records, columns=["sequence_number", "page_history"] + [c[0] for c in column_specs])


def generate_responses(
    structure: ParsedFormStructure,
    rules: Sequence[QuestionRuleConfig] | None,
    spss_groups: Sequence[SpssGroupConfig] | None,
    n: int,
    *,
    seed: int | None = None,
    text_mutator: TextMutator | None = None,
) -> list[GeneratedResponse]:
    generator = SurveyDataGenerator(structure, rules, spss_groups, seed=seed, text_mutator=text_mutator)
    return generator.generate(n)


def preview_spss(
    structure: ParsedFormStructure,
    rules: Sequence[QuestionRuleConfig] | None,
    spss_groups: Sequence[SpssGroupConfig],
    n: int = 200,
    *,
    seed: int | None = None,
) -> list[SpssGroupPreview]:
    generator = SurveyDataGenerator(structure, rules, spss_groups, seed=seed)
    return generator.preview_spss_groups(n)


__all__ = [
    "Answer",
    "GeneratedResponse",
    "GeneratorConfigError",
    "SurveyDataGenerator",
    "alpha_from_r",
    "build_payload_tuples",
    "calibrate_latent_correlation",
    "calibrate_latent_moments",
    "cronbach_alpha",
    "discretized_moments",
    "generate_responses",
    "mean_inter_item_correlation",
    "preview_spss",
    "r_from_alpha",
    "responses_to_dataframe",
    "scale_values_for",
]
