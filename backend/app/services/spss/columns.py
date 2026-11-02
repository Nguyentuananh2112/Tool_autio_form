"""Sinh cả cột N câu trả lời cho một câu hỏi (vector hóa bằng numpy, dev-notes PERF-001)."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from datetime import date, time, timedelta

import numpy as np

from app.schemas.campaign_schema import QuestionRuleConfig, RuleStrategy
from app.schemas.form_schema import OTHER_OPTION_VALUE, ParsedQuestion, QuestionType
from app.services.spss.answers import ANSWER_KIND_CHOICE, ANSWER_KIND_DATE, ANSWER_KIND_TEXT, ANSWER_KIND_TIME, Answer
from app.services.spss.group_plan import GroupPlan, sample_group_codes
from app.services.spss.scales import numeric_codes
from app.services.spss.validation import resolve_weights

# (câu được bốc, rng, toàn bộ pool của câu hỏi) -> câu đã biến thể; xem services/text_mutation.py
TextMutator = Callable[[str, np.random.Generator, Sequence[str]], str]
Column = list[Answer | None]

DEFAULT_TIME_START = time(8, 0)
DEFAULT_TIME_END = time(21, 0)


class ColumnBuilder:
    def __init__(self, rng: np.random.Generator, text_mutator: TextMutator | None = None) -> None:
        self._rng = rng
        self._text_mutator = text_mutator

    # ---------------------------------------------------------------- entry
    def for_group(self, plan: GroupPlan, n: int) -> dict[str, Column]:
        codes = sample_group_codes(plan, n, self._rng)
        columns: dict[str, Column] = {}
        for j, question in enumerate(plan.questions):
            column = codes[:, j]
            if question.entry_id in plan.reversed_entries:
                column = plan.lo + plan.hi - column
            options = question.choice_options
            columns[question.entry_id] = [
                Answer(values=[options[int(code) - plan.lo].value], numeric_value=float(code)) for code in column
            ]
        return columns

    def for_question(self, question: ParsedQuestion, rule: QuestionRuleConfig | None, n: int) -> Column:
        strategy = rule.strategy if rule else RuleStrategy.AUTO
        if strategy == RuleStrategy.SKIP:
            return [None] * n
        if strategy == RuleStrategy.FIXED:
            assert rule is not None
            return self._fixed(question, rule, n)

        mask = self._answer_mask(question, rule, n)
        if question.is_text:
            return self._text(rule, mask)
        if question.type_id == QuestionType.DATE:
            return self._date(rule, mask)
        if question.type_id == QuestionType.TIME:
            return self._time(rule, mask)
        if question.is_multi_select:
            return self._checkbox(question, rule, mask)
        return self._single_choice(question, rule, mask)

    # -------------------------------------------------------------- helpers
    def _answer_mask(self, question: ParsedQuestion, rule: QuestionRuleConfig | None, n: int) -> np.ndarray:
        if question.is_required or rule is None or rule.answer_rate >= 100.0:
            return np.ones(n, dtype=bool)
        return self._rng.uniform(0.0, 100.0, size=n) < rule.answer_rate

    def pick_text(self, pool: list[str]) -> str:
        text = pool[int(self._rng.integers(len(pool)))]
        if self._text_mutator is not None:
            text = self._text_mutator(text, self._rng, pool)
        return text

    # ---------------------------------------------------------------- types
    def _single_choice(self, question: ParsedQuestion, rule: QuestionRuleConfig | None, mask: np.ndarray) -> Column:
        n = mask.size
        options, weights = resolve_weights(question, rule)
        total = weights.sum()
        if total <= 0:
            return [None] * n
        picks = self._rng.choice(len(options), size=n, p=weights / total)
        codes = numeric_codes(question)
        other_pool = rule.other_text_pool if rule else []

        column: Column = []
        for i in range(n):
            if not mask[i]:
                column.append(None)
                continue
            option = options[int(picks[i])]
            if option.is_other:
                column.append(Answer(
                    values=[OTHER_OPTION_VALUE], other_text=self.pick_text(other_pool),
                    numeric_value=codes[OTHER_OPTION_VALUE],
                ))
            else:
                column.append(Answer(values=[option.value], numeric_value=codes.get(option.value)))
        return column

    def _checkbox(self, question: ParsedQuestion, rule: QuestionRuleConfig | None, mask: np.ndarray) -> Column:
        n = mask.size
        options, probabilities = resolve_weights(question, rule)
        k = len(options)
        other_pool = rule.other_text_pool if rule else []
        fillable = np.array([not (o.is_other and not other_pool) for o in options])

        min_checked = rule.min_checked if rule else 0
        if question.is_required:
            min_checked = max(min_checked, 1)
        min_checked = min(min_checked, int(fillable.sum()))
        max_checked = min(rule.max_checked if rule and rule.max_checked else k, k)
        max_checked = max(max_checked, min_checked)

        selected = self._rng.uniform(0.0, 100.0, size=(n, k)) < probabilities  # 0% không bao giờ, 100% luôn chọn

        column: Column = []
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
            other_text = self.pick_text(other_pool) if any(options[j].is_other for j in chosen_sorted) else None
            column.append(Answer(values=[options[j].value for j in chosen_sorted], other_text=other_text))
        return column

    def _text(self, rule: QuestionRuleConfig | None, mask: np.ndarray) -> Column:
        pool = rule.text_pool if rule else []
        if not pool:
            return [None] * mask.size
        return [Answer(values=[self.pick_text(pool)], kind=ANSWER_KIND_TEXT) if mask[i] else None for i in range(mask.size)]

    def _date(self, rule: QuestionRuleConfig | None, mask: np.ndarray) -> Column:
        end = rule.date_end if rule and rule.date_end else date.today()
        start = rule.date_start if rule and rule.date_start else end - timedelta(days=365)
        offsets = self._rng.integers(0, (end - start).days + 1, size=mask.size)
        return [
            Answer(values=[(start + timedelta(days=int(offsets[i]))).isoformat()], kind=ANSWER_KIND_DATE)
            if mask[i] else None
            for i in range(mask.size)
        ]

    def _time(self, rule: QuestionRuleConfig | None, mask: np.ndarray) -> Column:
        start = rule.time_start if rule and rule.time_start else DEFAULT_TIME_START
        end = rule.time_end if rule and rule.time_end else DEFAULT_TIME_END
        picks = self._rng.integers(start.hour * 60 + start.minute, end.hour * 60 + end.minute + 1, size=mask.size)
        return [
            Answer(values=[f"{int(picks[i]) // 60:02d}:{int(picks[i]) % 60:02d}"], kind=ANSWER_KIND_TIME)
            if mask[i] else None
            for i in range(mask.size)
        ]

    def _fixed(self, question: ParsedQuestion, rule: QuestionRuleConfig, n: int) -> Column:
        fixed = rule.fixed_value if isinstance(rule.fixed_value, list) else [str(rule.fixed_value)]
        if question.is_text:
            kind = ANSWER_KIND_TEXT
        elif question.type_id == QuestionType.DATE:
            kind = ANSWER_KIND_DATE
        elif question.type_id == QuestionType.TIME:
            kind = ANSWER_KIND_TIME
        else:
            kind = ANSWER_KIND_CHOICE
        codes = numeric_codes(question) if question.options else {}
        has_other = OTHER_OPTION_VALUE in fixed
        numeric = codes.get(fixed[0]) if len(fixed) == 1 and not question.is_multi_select else None
        return [
            Answer(
                values=list(fixed), kind=kind, numeric_value=numeric,
                other_text=self.pick_text(rule.other_text_pool) if has_other and rule.other_text_pool else None,
            )
            for _ in range(n)
        ]
