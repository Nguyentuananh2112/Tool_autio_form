"""Mã hóa số cho đáp án: dùng cho nhóm SPSS, xuất dữ liệu và nhập từ Excel."""

from __future__ import annotations

from app.schemas.form_schema import OTHER_OPTION_VALUE, ParsedQuestion


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


def numeric_codes(question: ParsedQuestion) -> dict[str, float]:
    """option value → mã số; "Mục khác" = K + 1."""
    choice_options = question.choice_options
    values = scale_values_for(question)
    codes = {option.value: float(value) for option, value in zip(choice_options, values)}
    codes[OTHER_OPTION_VALUE] = float(len(choice_options) + 1)
    return codes
