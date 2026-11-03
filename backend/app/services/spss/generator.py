"""Bộ điều phối sinh N phản hồi hoàn chỉnh (Mục 5.2 spec).

Module thuần CPU: trong code async hãy gọi qua `await asyncio.to_thread(generator.generate, n)`.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import TYPE_CHECKING

import numpy as np

from app.schemas.campaign_schema import QuestionRuleConfig, SpssGroupConfig, SpssGroupPreview
from app.schemas.form_schema import ParsedFormStructure, ParsedQuestion
from app.schemas.logic_schema import LogicMap
from app.services.spss.answers import Answer, GeneratedResponse
from app.services.spss.columns import Column, ColumnBuilder, TextMutator
from app.services.spss.group_plan import GroupPlan, plan_group
from app.services.spss.page_navigator import PageNavigator
from app.services.spss.preview import build_group_preview
from app.services.spss.validation import GeneratorConfigError, validate_question

if TYPE_CHECKING:
    from app.services.logic.plan import FilterStats, LogicPlan


class SurveyDataGenerator:
    def __init__(
        self,
        structure: ParsedFormStructure,
        rules: Sequence[QuestionRuleConfig] | Mapping[str, QuestionRuleConfig] | None = None,
        spss_groups: Sequence[SpssGroupConfig] | None = None,
        *,
        seed: int | None = None,
        text_mutator: TextMutator | None = None,
        logic: LogicMap | None = None,
    ) -> None:
        self.structure = structure
        rule_list = list(rules.values()) if isinstance(rules, Mapping) else list(rules or [])
        self._rules: dict[str, QuestionRuleConfig] = {rule.entry_id: rule for rule in rule_list}
        self._groups: list[SpssGroupConfig] = list(spss_groups or [])
        self._seed = seed
        self._columns = ColumnBuilder(np.random.default_rng(seed), text_mutator)
        self._questions: dict[str, ParsedQuestion] = {q.entry_id: q for q in structure.questions}
        self._navigator = PageNavigator(structure)
        self._plans: list[GroupPlan] | None = None
        self.warnings: list[str] = []
        self._logic: LogicPlan | None = None
        if logic is not None:
            from app.services.logic.plan import LogicPlan  # tránh vòng import spss ↔ logic

            self._logic = LogicPlan(structure, logic, self._rules)
        # Kết quả lượt soát cuối cùng của generate() (None nếu không soát logic)
        self.filter_stats: FilterStats | None = None

    def _plan_groups(self, errors: list[str]) -> tuple[list[GroupPlan], dict[str, str]]:
        grouped: dict[str, str] = {}
        plans: list[GroupPlan] = []
        group_ids: set[str] = set()
        for group in self._groups:
            if group.group_id in group_ids:
                errors.append(f"Trùng group_id '{group.group_id}'.")
                continue
            group_ids.add(group.group_id)
            plan = plan_group(group, self._questions, grouped, errors)
            if plan is not None:
                plans.append(plan)
        return plans, grouped

    def validate(self) -> list[str]:
        """Kiểm tra cấu hình, hiệu chỉnh các nhóm SPSS. Raise GeneratorConfigError nếu có lỗi."""
        errors: list[str] = []
        warnings = [
            f"Luật cho entry {entry_id} không khớp câu hỏi nào trong form, sẽ bị bỏ qua."
            for entry_id in self._rules
            if entry_id not in self._questions
        ]
        plans, grouped = self._plan_groups(errors)

        for question in self.structure.questions:
            if question.entry_id not in grouped:
                validate_question(question, self._rules.get(question.entry_id), errors, warnings)

        if errors:
            raise GeneratorConfigError(errors)
        self._plans = plans
        self.warnings = warnings
        return warnings

    def _ensure_plans(self) -> list[GroupPlan]:
        if self._plans is None:
            self.validate()
        assert self._plans is not None
        return self._plans

    def generate(self, n: int, *, start_sequence: int = 1) -> list[GeneratedResponse]:
        if n < 1:
            raise ValueError("Số mẫu cần sinh phải >= 1")
        if self._logic is None:
            responses = self._generate_raw(n)
        else:
            responses, self.filter_stats = self._logic.select(self._generate_raw, n, self._columns.rng)
        for offset, response in enumerate(responses):
            response.sequence_number = start_sequence + offset
        return responses

    def _generate_raw(self, n: int) -> list[GeneratedResponse]:
        logic = self._logic
        factors = logic.factors(n, self._columns.rng) if logic else {}
        columns: dict[str, Column] = {}
        for plan in self._ensure_plans():
            shared = logic.shared_for(plan, factors) if logic else None
            columns.update(self._columns.for_group(plan, n, shared, logic.loading if logic else 0.0))
        for question in self.structure.questions:
            if question.entry_id not in columns:
                columns[question.entry_id] = self._columns.for_question(
                    question, self._rules.get(question.entry_id), n, logic.input_for(question, factors) if logic else None
                )

        ordered_entries = [q.entry_id for q in self.structure.questions]
        responses: list[GeneratedResponse] = []
        for i in range(n):
            raw: dict[str, Answer] = {
                entry_id: answer for entry_id in ordered_entries if (answer := columns[entry_id][i]) is not None
            }
            if logic is not None:
                logic.repair(raw, self._columns.rng)
            pages = self._navigator.page_history(raw)
            visited = set(pages)
            answers = {e: a for e, a in raw.items() if self._questions[e].page_index in visited}
            responses.append(GeneratedResponse(sequence_number=i + 1, answers=answers, page_history=pages))
        return responses

    def build_page_history(self, answers: Mapping[str, Answer]) -> list[int]:
        return self._navigator.page_history(answers)

    def preview_spss_groups(self, n: int = 200) -> list[SpssGroupPreview]:
        """Chạy thử n mẫu trong RAM (RNG riêng, không ảnh hưởng dữ liệu sinh thật)."""
        if n < 3:
            raise ValueError("Cần ít nhất 3 mẫu để tính thống kê")
        # Chỉ kiểm tra các nhóm: câu khác chưa cấu hình xong không được chặn việc chạy thử nhóm
        errors: list[str] = []
        plans, _ = self._plan_groups(errors)
        if errors:
            raise GeneratorConfigError(errors)
        rng = np.random.default_rng(self._seed)
        return [build_group_preview(plan, n, rng) for plan in plans]


def generate_responses(
    structure: ParsedFormStructure,
    rules: Sequence[QuestionRuleConfig] | None,
    spss_groups: Sequence[SpssGroupConfig] | None,
    n: int,
    *,
    seed: int | None = None,
    text_mutator: TextMutator | None = None,
    logic: LogicMap | None = None,
) -> list[GeneratedResponse]:
    return SurveyDataGenerator(
        structure, rules, spss_groups, seed=seed, text_mutator=text_mutator, logic=logic
    ).generate(n)


def preview_spss(
    structure: ParsedFormStructure,
    rules: Sequence[QuestionRuleConfig] | None,
    spss_groups: Sequence[SpssGroupConfig],
    n: int = 200,
    *,
    seed: int | None = None,
) -> list[SpssGroupPreview]:
    return SurveyDataGenerator(structure, rules, spss_groups, seed=seed).preview_spss_groups(n)
