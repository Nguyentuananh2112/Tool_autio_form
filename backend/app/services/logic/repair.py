"""Lượt 3: sửa đúng câu bị mâu thuẫn thay vì bỏ cả phản hồi.

Bỏ cả phản hồi rồi sinh lại làm lệch tỷ lệ người dùng đặt (VD bớt hẳn người "Dưới 18",
ít người đi nhánh có nhiều câu đánh giá) — đo trên form Tiki, dev-notes ISS-008. Sửa tại chỗ:

- Ràng buộc NẾU…THÌ: đổi câu "THÌ" sang đáp án hợp lệ (bốc theo trọng số người dùng đặt).
  "Thường" chỉ sửa với xác suất USUALLY_RATE, phần còn lại là ngoại lệ tự nhiên.
- Độ lệch trong nhóm thái độ: câu nằm quá xa mức chung của người đó được kéo về mức gần nhất
  trong khoảng cho phép quanh trung vị.

Chạy trên câu trả lời THÔ (trước khi tính rẽ nhánh) để đường đi qua các trang luôn khớp đáp án.
"""

from __future__ import annotations

from collections.abc import Mapping

import numpy as np

from app.schemas.campaign_schema import QuestionRuleConfig
from app.schemas.form_schema import ParsedFormStructure, ParsedQuestion
from app.schemas.logic_schema import USUALLY_RATE, LogicMap, LogicRule, RuleStrength, ThenOp
from app.services.logic.checker import (
    SPREAD_LIMIT,
    Violation,
    ViolationKind,
    answered_positions,
    opposite_ends,
    rating_gap_too_wide,
    spread_conflict,
)
from app.services.logic.ordering import SpreadItem, SpreadItems, spread_groups
from app.services.spss.answers import Answer
from app.services.spss.scales import numeric_codes
from app.services.spss.validation import resolve_weights

MAX_PASSES = 3


class ResponseRepairer:
    def __init__(
        self, structure: ParsedFormStructure, logic: LogicMap, rules: Mapping[str, QuestionRuleConfig]
    ) -> None:
        self._logic = logic
        self._questions = {q.entry_id: q for q in structure.questions}
        self._rules = rules
        self._limit = SPREAD_LIMIT[logic.consistency]
        self._groups = spread_groups(structure, logic)

    def repair(self, answers: dict[str, Answer], rng: np.random.Generator) -> list[Violation]:
        """Sửa tại chỗ; trả về các mâu thuẫn đã sửa (để thống kê)."""
        fixed: list[Violation] = []
        exempt: set[str] = set()  # ràng buộc "Thường" đã tung xác suất cho người này: không tung lại
        for _ in range(MAX_PASSES):
            changed = False
            for rule in self._logic.rules:
                if rule.rule_id not in exempt and self._fix_rule(rule, answers, rng, exempt):
                    fixed.append(Violation(ViolationKind.RULE, rule.rule_id))
                    changed = True
            for group_id, items in self._groups:
                if self._fix_spread(items, answers):
                    fixed.append(Violation(ViolationKind.SPREAD, group_id))
                    changed = True
            if not changed:
                break
        return fixed

    # ------------------------------------------------------------------ rules
    def _fix_rule(
        self, rule: LogicRule, answers: dict[str, Answer], rng: np.random.Generator, exempt: set[str]
    ) -> bool:
        condition = answers.get(rule.if_entry)
        outcome = answers.get(rule.then_entry)
        question = self._questions.get(rule.then_entry)
        if condition is None or outcome is None or question is None or not question.options:
            return False
        if not set(condition.values) & set(rule.if_values):
            return False
        hit = bool(set(outcome.values) & set(rule.then_values))
        if hit == (rule.then_op == ThenOp.IS):
            return False
        if rule.strength == RuleStrength.USUALLY and rng.uniform() >= USUALLY_RATE:
            exempt.add(rule.rule_id)  # ngoại lệ tự nhiên, giữ nguyên cho người này
            return False
        replacement = self._replacement(question, rule, outcome, rng)
        if replacement is None:
            return False
        answers[rule.then_entry] = replacement
        return True

    def _replacement(
        self, question: ParsedQuestion, rule: LogicRule, outcome: Answer, rng: np.random.Generator
    ) -> Answer | None:
        options, weights = resolve_weights(question, self._rules.get(question.entry_id))
        banned = set(rule.then_values) if rule.then_op == ThenOp.IS_NOT else set()
        allowed = [
            i for i, option in enumerate(options)
            if not option.is_other and (option.value in rule.then_values if rule.then_op == ThenOp.IS else option.value not in banned)
        ]
        if not allowed:
            return None
        pick_weights = np.array([max(float(weights[i]), 0.0) for i in allowed])
        pick_weights = pick_weights if pick_weights.sum() > 0 else np.ones(len(allowed))
        chosen = options[allowed[int(rng.choice(len(allowed), p=pick_weights / pick_weights.sum()))]].value
        if question.is_multi_select:
            kept = [v for v in outcome.values if v not in banned and v not in rule.then_values]
            values = [o.value for o in options if o.value in {*kept, chosen}]
            return Answer(values=values, other_text=outcome.other_text, kind=outcome.kind)
        return Answer(values=[chosen], kind=outcome.kind, numeric_value=numeric_codes(question).get(chosen))

    # ----------------------------------------------------------------- spread
    def _window(self, values: list[float]) -> tuple[float, float]:
        """Khoảng rộng `limit` phải dịch chuyển ít nhất (giữ tối đa sự đa dạng tự nhiên).

        Hoà thì chọn khoảng gần trung vị của người đó hơn.
        """
        limit = self._limit
        median = float(np.median(values))
        candidates = {round(p, 9) for p in values} | {round(p - limit, 9) for p in values}

        def cost(start: float) -> tuple[float, float]:
            moved = sum(max(start - p, 0.0) + max(p - start - limit, 0.0) for p in values)
            return moved, abs(start + limit / 2 - median)

        start = min(candidates, key=cost)
        return start, start + limit

    def _fix_spread(self, items: SpreadItems, answers: dict[str, Answer]) -> bool:
        current = answered_positions(items, answers)
        if not spread_conflict(current, self._limit):
            return False
        if rating_gap_too_wide(current, self._limit):
            low, high = self._window([p for item, p in current if item.rating])
            for item, position in current:
                if item.rating and not low - 1e-9 <= position <= high + 1e-9:
                    self._set(answers, item, self._nearest(item, position, low, high))
            current = answered_positions(items, answers)
        if opposite_ends(current):
            # Kéo câu xa trung vị nhất (ưu tiên câu chữ) vào trong một mức
            median = float(np.median([p for _, p in current]))
            item, position = max(current, key=lambda pair: (abs(pair[1] - median), not pair[0].rating))
            levels = sorted(item.positions.values())
            step = levels[1] if position <= 1e-9 else levels[-2]
            self._set(answers, item, next(v for v, p in item.positions.items() if abs(p - step) < 1e-9))
        return True

    @staticmethod
    def _nearest(item: SpreadItem, position: float, low: float, high: float) -> str:
        inside = [(abs(p - position), value) for value, p in item.positions.items() if low - 1e-9 <= p <= high + 1e-9]
        if not inside:  # thang thưa hơn độ rộng cửa sổ: lấy mức gần cửa sổ nhất
            target = min(high, max(low, position))
            inside = [(abs(p - target), value) for value, p in item.positions.items()]
        return min(inside)[1]

    def _set(self, answers: dict[str, Answer], item: SpreadItem, value: str) -> None:
        answers[item.entry_id] = Answer(values=[value], numeric_value=numeric_codes(self._questions[item.entry_id]).get(value))
