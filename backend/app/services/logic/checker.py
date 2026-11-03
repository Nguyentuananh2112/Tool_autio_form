"""Lượt 3: đọc lại TOÀN BỘ một phản hồi, tìm mâu thuẫn trước khi gửi.

- RULE: vi phạm ràng buộc NẾU…THÌ.
- EXCLUSIVE: ô loại trừ ("Không có…") đi kèm ô khác.
- SPREAD: trong một nhóm thái độ, câu này rất tích cực mà câu kia rất tiêu cực
  (VD uy tín 4/5 nhưng chất lượng 1/5) — ngưỡng theo độ đồng đều.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum

from app.schemas.form_schema import ParsedFormStructure
from app.schemas.logic_schema import Consistency, LogicMap, LogicRule, RuleStrength, ThenOp
from app.services.logic.ordering import SpreadItem, SpreadItems, spread_groups
from app.services.spss.answers import Answer

# Khoảng cách vị trí (0..1) tối đa giữa hai câu cùng nhóm thái độ của một người
SPREAD_LIMIT: dict[Consistency, float] = {
    Consistency.VARIED: 0.75,  # thang 1–5: chỉ cấm 5 với 1; thang 1–10: lệch ≥ 7
    Consistency.MODERATE: 0.55,  # thang 1–5: lệch tối đa 2 điểm (≥ 3 là mâu thuẫn); thang 1–10: tối đa 4
    Consistency.UNIFORM: 0.3,  # thang 1–5: lệch tối đa 1 điểm; thang 1–10: tối đa 2
}


class ViolationKind(StrEnum):
    RULE = "RULE"
    EXCLUSIVE = "EXCLUSIVE"
    SPREAD = "SPREAD"


@dataclass(frozen=True, slots=True)
class Violation:
    kind: ViolationKind
    key: str  # rule_id / entry_id / group_id — để thống kê
    soft: bool = False  # ràng buộc "Thường": vi phạm vẫn có thể giữ lại


class ResponseChecker:
    def __init__(self, structure: ParsedFormStructure, logic: LogicMap) -> None:
        self._logic = logic
        self._limit = SPREAD_LIMIT[logic.consistency]
        self._spread = spread_groups(structure, logic)
        self._exclusive: dict[str, set[str]] = {}
        for option in logic.exclusive_options:
            self._exclusive.setdefault(option.entry_id, set()).add(option.value)

    # ------------------------------------------------------------------ public
    def violations(self, answers: Mapping[str, Answer]) -> list[Violation]:
        found = [v for rule in self._logic.rules if (v := self._check_rule(rule, answers))]
        found += self._check_exclusive(answers)
        found += self._check_spread(answers)
        return found

    def blocking(self, answers: Mapping[str, Answer]) -> list[Violation]:
        """Mâu thuẫn buộc sinh lại. Vi phạm ràng buộc "Thường" là ngoại lệ tự nhiên (repair đã quyết định)."""
        return [v for v in self.violations(answers) if not v.soft]

    # ----------------------------------------------------------------- checks
    @staticmethod
    def _check_rule(rule: LogicRule, answers: Mapping[str, Answer]) -> Violation | None:
        condition = answers.get(rule.if_entry)
        outcome = answers.get(rule.then_entry)
        if condition is None or outcome is None:
            return None  # câu chưa được trả lời / trang không đi qua → ràng buộc không áp dụng
        if not set(condition.values) & set(rule.if_values):
            return None
        hit = bool(set(outcome.values) & set(rule.then_values))
        ok = hit if rule.then_op == ThenOp.IS else not hit
        if ok:
            return None
        return Violation(ViolationKind.RULE, rule.rule_id, soft=rule.strength == RuleStrength.USUALLY)

    def _check_exclusive(self, answers: Mapping[str, Answer]) -> list[Violation]:
        found = []
        for entry_id, exclusive in self._exclusive.items():
            answer = answers.get(entry_id)
            if answer is not None and len(answer.values) > 1 and exclusive & set(answer.values):
                found.append(Violation(ViolationKind.EXCLUSIVE, entry_id))
        return found

    def _check_spread(self, answers: Mapping[str, Answer]) -> list[Violation]:
        found = []
        for group_id, items in self._spread:
            current = answered_positions(items, answers)
            if spread_conflict(current, self._limit):
                found.append(Violation(ViolationKind.SPREAD, group_id))
        return found


def answered_positions(items: SpreadItems, answers: Mapping[str, Answer]) -> list[tuple[SpreadItem, float]]:
    return [
        (item, item.positions[answer.values[0]])
        for item in items
        if (answer := answers.get(item.entry_id)) is not None and answer.values and answer.values[0] in item.positions
    ]


def rating_gap_too_wide(current: list[tuple[SpreadItem, float]], limit: float) -> bool:
    rating = [p for item, p in current if item.rating]
    return len(rating) >= 2 and max(rating) - min(rating) > limit + 1e-9


def opposite_ends(current: list[tuple[SpreadItem, float]]) -> bool:
    """Có câu ở đầu tiêu cực nhất VÀ câu ở đầu tích cực nhất (tính cả câu chữ)."""
    values = [p for _, p in current]
    return len(values) >= 2 and min(values) <= 1e-9 and max(values) >= 1 - 1e-9


def spread_conflict(current: list[tuple[SpreadItem, float]], limit: float) -> bool:
    return rating_gap_too_wide(current, limit) or opposite_ends(current)
