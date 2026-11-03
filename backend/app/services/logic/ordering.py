"""Thứ tự đáp án từ tiêu cực → tích cực và vị trí 0..1 của một đáp án trong thứ tự đó."""

from __future__ import annotations

from dataclasses import dataclass

from app.schemas.form_schema import ParsedFormStructure, ParsedQuestion
from app.schemas.logic_schema import AttitudeItem, LogicMap

# Chỉ so độ lệch giữa các câu CHẤM ĐIỂM (thang số ≥ 5 mức: 1–5, 1–7, 1–10…). Câu chữ ít mức
# (VD tần suất mua) có tỷ lệ riêng; ép chúng gần câu điểm làm lệch tỷ lệ người dùng đặt (ISS-008).
MIN_RATING_LEVELS = 5
# Câu chữ có thứ bậc (≥ 3 mức) chỉ bị coi là mâu thuẫn khi hai câu ở HAI ĐẦU ngược nhau
# (VD "Hoàn toàn không nhận diện được" nhưng "Luôn nhận ra quảng cáo").
MIN_ORDINAL_LEVELS = 3


@dataclass(frozen=True, slots=True)
class SpreadItem:
    entry_id: str
    positions: dict[str, float]
    rating: bool  # câu chấm điểm: so độ lệch theo ngưỡng; câu chữ: chỉ chặn hai đầu ngược nhau


SpreadItems = list[SpreadItem]


def ordered_values(question: ParsedQuestion, item: AttitudeItem) -> list[str]:
    """Giá trị các lựa chọn thường (bỏ "Mục khác"), xếp từ tiêu cực nhất → tích cực nhất."""
    values = [option.value for option in question.choice_options]
    return values if item.positive_high else values[::-1]


def positions(question: ParsedQuestion, item: AttitudeItem) -> dict[str, float]:
    """value → vị trí 0 (tiêu cực nhất) .. 1 (tích cực nhất). Câu < 2 mức: rỗng."""
    values = ordered_values(question, item)
    if len(values) < 2:
        return {}
    last = len(values) - 1
    return {value: index / last for index, value in enumerate(values)}


def is_rating_scale(question: ParsedQuestion) -> bool:
    if not question.is_single_choice:
        return False
    try:
        numbers = [int(option.value.strip()) for option in question.choice_options]
    except ValueError:
        return False
    return len(numbers) >= MIN_RATING_LEVELS and all(b - a == 1 for a, b in zip(numbers, numbers[1:]))


def spread_groups(structure: ParsedFormStructure, logic: LogicMap) -> list[tuple[str, SpreadItems]]:
    """Mỗi nhóm thái độ → các câu có thứ bậc kèm bảng vị trí 0..1 (đã theo chiều tích cực)."""
    questions = {q.entry_id: q for q in structure.questions}
    result = []
    for group in logic.attitude_groups:
        items = []
        for item in group.items:
            question = questions.get(item.entry_id)
            if question is None or not question.is_single_choice:
                continue
            pos = positions(question, item)
            if len(pos) >= MIN_ORDINAL_LEVELS:
                items.append(SpreadItem(item.entry_id, pos, is_rating_scale(question)))
        result.append((group.group_id, items))
    return result
