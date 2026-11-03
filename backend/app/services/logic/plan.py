"""Áp bản đồ logic vào bộ sinh: nhân tố thái độ cho mỗi người, đầu vào cho từng câu, và lọc phản hồi.

Lượt 2 (sinh theo thái độ) + lượt 3 (đọc lại từng phản hồi, mâu thuẫn thì sinh lại).
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass, field

import numpy as np

from app.schemas.form_schema import ParsedFormStructure, ParsedQuestion
from app.schemas.logic_schema import LogicMap
from app.services.logic.attitude import LOADING
from app.schemas.campaign_schema import QuestionRuleConfig
from app.services.logic.checker import ResponseChecker, Violation
from app.services.logic.repair import ResponseRepairer
from app.services.spss.answers import Answer
from app.services.spss.answers import GeneratedResponse
from app.services.spss.columns import LogicInput
from app.services.spss.group_plan import GroupPlan

MAX_ROUNDS = 12
OVERSAMPLE = 1.6


@dataclass(slots=True)
class FilterStats:
    generated: int = 0
    rejected: int = 0
    repaired: int = 0  # phản hồi có ít nhất một câu được sửa cho khớp
    rejected: int = 0  # phản hồi sửa không được, phải sinh lại
    residual: int = 0  # vẫn còn mâu thuẫn sau nhiều lần sinh lại (hiếm) — vẫn phải dùng để đủ số lượng
    by_kind: Counter[str] = field(default_factory=Counter)  # mâu thuẫn đã bắt được theo loại
    by_key: Counter[str] = field(default_factory=Counter)  # … theo rule_id / entry_id / group_id


class LogicPlan:
    def __init__(
        self, structure: ParsedFormStructure, logic: LogicMap, rules: dict[str, QuestionRuleConfig] | None = None
    ) -> None:
        self.logic = logic
        self.loading = LOADING[logic.consistency]
        self.checker = ResponseChecker(structure, logic)
        self.repairer = ResponseRepairer(structure, logic, rules or {})
        self.stats = FilterStats()
        self._exclusive: dict[str, frozenset[str]] = {}
        for option in logic.exclusive_options:
            self._exclusive[option.entry_id] = self._exclusive.get(option.entry_id, frozenset()) | {option.value}
        self._text = {text.entry_id: text for text in logic.text_attitudes}

    def factors(self, n: int, rng: np.random.Generator) -> dict[str, np.ndarray]:
        return {group.group_id: rng.standard_normal(n) for group in self.logic.attitude_groups}

    def shared_for(self, plan: GroupPlan, factors: dict[str, np.ndarray]) -> np.ndarray | None:
        """Nhóm SPSS gắn với nhóm thái độ chứa nhiều câu của nó nhất."""
        votes: Counter[str] = Counter()
        for question in plan.questions:
            found = self.logic.group_of(question.entry_id)
            if found is not None:
                votes[found[0].group_id] += 1
        if not votes:
            return None
        return factors[votes.most_common(1)[0][0]]

    def input_for(self, question: ParsedQuestion, factors: dict[str, np.ndarray]) -> LogicInput | None:
        exclusive = self._exclusive.get(question.entry_id, frozenset())
        text = self._text.get(question.entry_id)
        if text is not None and question.is_text:
            return LogicInput(factor=factors[text.group_id], loading=self.loading, text_labels=dict(text.labels))
        found = self.logic.group_of(question.entry_id)
        if found is not None and question.is_single_choice and len(question.choice_options) >= 2:
            group, item = found
            return LogicInput(factor=factors[group.group_id], loading=self.loading, item=item, exclusive=exclusive)
        return LogicInput(exclusive=exclusive) if exclusive else None

    def repair(self, raw: dict[str, Answer], rng: np.random.Generator) -> None:
        """Sửa câu trả lời thô của một người (trước khi tính rẽ nhánh)."""
        fixed = self.repairer.repair(raw, rng)
        if fixed:
            self.stats.repaired += 1
            _count(self.stats, fixed)

    def select(
        self, make_batch: Callable[[int], list[GeneratedResponse]], n: int, rng: np.random.Generator
    ) -> tuple[list[GeneratedResponse], FilterStats]:
        """Sinh (đã sửa tại chỗ), đọc lại từng phản hồi; phản hồi còn mâu thuẫn thì sinh lại."""
        stats = self.stats = FilterStats()
        accepted: list[GeneratedResponse] = []
        rejected: list[tuple[int, GeneratedResponse]] = []
        for _ in range(MAX_ROUNDS):
            missing = n - len(accepted)
            if missing <= 0:
                break
            batch = make_batch(missing if not rejected else max(int(missing * OVERSAMPLE) + 8, 16))
            stats.generated += len(batch)
            for response in batch:
                problems = self.checker.blocking(response.answers)
                if problems:
                    rejected.append((len(problems), response))
                elif len(accepted) < n:
                    accepted.append(response)
        stats.rejected = len(rejected)
        if len(accepted) < n:
            rejected.sort(key=lambda pair: pair[0])
            fill = [response for _, response in rejected[: n - len(accepted)]]
            stats.residual = len(fill)
            accepted.extend(fill)
        return accepted, stats


def _count(stats: FilterStats, problems: list[Violation]) -> None:
    for problem in problems:
        stats.by_kind[problem.kind.value] += 1
        stats.by_key[problem.key] += 1
