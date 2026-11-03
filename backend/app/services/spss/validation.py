"""Kiểm tra luật sinh dữ liệu của từng câu hỏi trước khi chạy."""

from __future__ import annotations

import numpy as np

from app.schemas.campaign_schema import QuestionRuleConfig, RuleStrategy
from app.schemas.form_schema import OTHER_OPTION_VALUE, ParsedOption, ParsedQuestion, QuestionType

DEFAULT_CHECKBOX_PROBABILITY = 50.0
MIN_DEFAULT_CHECKBOX_PROBABILITY = 5.0


def default_checkbox_probability(question: ParsedQuestion, rule: QuestionRuleConfig | None) -> float:
    """Xác suất mặc định mỗi ô khi người dùng chưa đặt tỷ lệ.

    Có giới hạn "tối đa N": chọn sao cho số ô được tích trung bình rơi vào giữa [min, max], để số
    ô thay đổi tự nhiên. Nếu cứ 50% mỗi ô với 11 lựa chọn, gần như mọi phản hồi bị cắt về đúng N ô
    (phát hiện khi chạy thật 100 phản hồi — dev-notes BUG-014).
    """
    max_checked = rule.max_checked if rule else None
    fillable = sum(1 for option in question.options if not option.is_other)
    if not max_checked or fillable == 0:
        return DEFAULT_CHECKBOX_PROBABILITY
    min_checked = max(rule.min_checked if rule else 0, 1 if question.is_required else 0)
    expected = (min(min_checked, max_checked) + max_checked) / 2
    percent = round(100.0 * expected / fillable, 1)
    return float(min(max(percent, MIN_DEFAULT_CHECKBOX_PROBABILITY), DEFAULT_CHECKBOX_PROBABILITY))


class GeneratorConfigError(ValueError):
    """Cấu hình sinh dữ liệu không hợp lệ; `errors` chứa danh sách lỗi hiển thị cho người dùng."""

    def __init__(self, errors: list[str]) -> None:
        self.errors = errors
        super().__init__("; ".join(errors))


def resolve_weights(question: ParsedQuestion, rule: QuestionRuleConfig | None) -> tuple[list[ParsedOption], np.ndarray]:
    """Trọng số theo thứ tự option. Không cấu hình: đều nhau (Checkbox: xem default_checkbox_probability),
    "Mục khác" = 0."""
    options = list(question.options)
    if rule and rule.weights:
        weights = np.array([max(float(rule.weights.get(o.value, 0.0)), 0.0) for o in options])
    elif question.is_multi_select:
        default = default_checkbox_probability(question, rule)
        weights = np.array([0.0 if o.is_other else default for o in options])
    else:
        weights = np.array([0.0 if o.is_other else 1.0 for o in options])
    if question.is_multi_select:
        weights = np.clip(weights, 0.0, 100.0)
    return options, weights


def _validate_fixed(question: ParsedQuestion, rule: QuestionRuleConfig, label: str, errors: list[str]) -> None:
    fixed = rule.fixed_value if isinstance(rule.fixed_value, list) else [rule.fixed_value]
    if not question.options:
        return
    valid_values = {option.value for option in question.options}
    invalid = [value for value in fixed if value not in valid_values]
    if invalid:
        errors.append(f"{label}: giá trị cố định {invalid} không có trong danh sách lựa chọn.")
    if not question.is_multi_select and len(fixed) > 1:
        errors.append(f"{label}: câu một lựa chọn chỉ nhận 1 giá trị cố định.")
    if OTHER_OPTION_VALUE in fixed and not rule.other_text_pool:
        errors.append(f"{label}: chọn 'Mục khác' cần nhập other_text_pool.")


def _validate_choice(
    question: ParsedQuestion, rule: QuestionRuleConfig | None, label: str, errors: list[str], warnings: list[str]
) -> None:
    if rule and rule.weights:
        known = {option.value for option in question.options}
        unknown = [key for key in rule.weights if key not in known]
        if unknown:
            warnings.append(f"{label}: bỏ qua trọng số của đáp án không tồn tại {unknown}.")

    options, weights = resolve_weights(question, rule)
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


def validate_question(
    question: ParsedQuestion, rule: QuestionRuleConfig | None, errors: list[str], warnings: list[str]
) -> None:
    label = f"'{question.title}'"
    strategy = rule.strategy if rule else RuleStrategy.AUTO

    if strategy == RuleStrategy.SKIP:
        if question.is_required:
            errors.append(f"{label} là câu bắt buộc, không thể bỏ qua (SKIP).")
        return
    if strategy == RuleStrategy.FIXED:
        assert rule is not None
        _validate_fixed(question, rule, label, errors)
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
    _validate_choice(question, rule, label, errors, warnings)
