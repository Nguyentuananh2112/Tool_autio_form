"""Kiểm tra bản đồ logic người dùng sửa tay có khớp form không (câu / đáp án phải tồn tại)."""

from __future__ import annotations

from app.schemas.form_schema import ParsedFormStructure, ParsedQuestion
from app.schemas.logic_schema import LogicMap


class LogicMapInvalidError(ValueError):
    def __init__(self, errors: list[str]) -> None:
        self.errors = errors
        super().__init__("Bản đồ logic chưa hợp lệ.")


def _label(question: ParsedQuestion | None, entry_id: str) -> str:
    return f"'{question.row_label or question.title}'" if question else f"entry {entry_id}"


def validate_logic(structure: ParsedFormStructure, logic: LogicMap) -> list[str]:
    questions = {q.entry_id: q for q in structure.questions}
    errors: list[str] = []

    def values_ok(question: ParsedQuestion, values: list[str], where: str) -> None:
        known = {option.value for option in question.options}
        unknown = [v for v in values if v not in known]
        if unknown:
            errors.append(f"{where}: {_label(question, question.entry_id)} không có đáp án {unknown}.")

    for group in logic.attitude_groups:
        for item in group.items:
            question = questions.get(item.entry_id)
            if question is None:
                errors.append(f"Nhóm '{group.name}': không tìm thấy {_label(None, item.entry_id)}.")
            elif not question.is_single_choice or len(question.choice_options) < 2:
                errors.append(f"Nhóm '{group.name}': {_label(question, item.entry_id)} không phải câu chọn một có thứ bậc.")

    for rule in logic.rules:
        where = f"Ràng buộc {rule.rule_id}"
        if_q, then_q = questions.get(rule.if_entry), questions.get(rule.then_entry)
        if if_q is None or then_q is None:
            missing = rule.if_entry if if_q is None else rule.then_entry
            errors.append(f"{where}: không tìm thấy {_label(None, missing)}.")
            continue
        values_ok(if_q, rule.if_values, where)
        values_ok(then_q, rule.then_values, where)

    for option in logic.exclusive_options:
        question = questions.get(option.entry_id)
        if question is None or not question.is_multi_select:
            errors.append(f"Ô loại trừ: {_label(question, option.entry_id)} không phải câu hộp kiểm.")
        else:
            values_ok(question, [option.value], "Ô loại trừ")

    for text in logic.text_attitudes:
        question = questions.get(text.entry_id)
        if question is None or not question.is_text:
            errors.append(f"Tự luận theo thái độ: {_label(question, text.entry_id)} không phải câu tự luận.")
    return errors


def ensure_valid(structure: ParsedFormStructure, logic: LogicMap) -> None:
    errors = validate_logic(structure, logic)
    if errors:
        raise LogicMapInvalidError(errors)
