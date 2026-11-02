"""Micro-Mutation (Mục 5.3 spec): biến thể nhẹ cho câu trả lời tự luận bốc lại từ pool.

Khi cần nhiều phản hồi hơn số câu trong pool, mỗi lần bốc được biến đổi ngẫu nhiên
(viết hoa/thường chữ đầu, thêm/bỏ dấu chấm cuối, ghép hai câu ngắn) để giảm trùng lặp 100%.
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np

CASE_TOGGLE_PROBABILITY = 0.35
TRAILING_PERIOD_PROBABILITY = 0.30
MERGE_PROBABILITY = 0.15
MAX_WORDS_TO_MERGE = 12
JOINERS: tuple[str, ...] = (", ", " và ", ". ")


def _toggle_first_letter(text: str) -> str:
    for index, char in enumerate(text):
        if char.isalpha():
            swapped = char.lower() if char.isupper() else char.upper()
            return text[:index] + swapped + text[index + 1:]
    return text


def _lower_first_letter(text: str) -> str:
    for index, char in enumerate(text):
        if char.isalpha():
            return text[:index] + char.lower() + text[index + 1:]
    return text


def _toggle_trailing_period(text: str) -> str:
    if text.endswith("."):
        return text.rstrip(".").rstrip()
    if text[-1:].isalnum():
        return text + "."
    return text


def _merge(first: str, second: str, joiner: str) -> str:
    head = first.rstrip(" .")
    tail = second.strip()
    if joiner != ". ":
        tail = _lower_first_letter(tail)
    return f"{head}{joiner}{tail}"


def micro_mutate(text: str, rng: np.random.Generator, pool: Sequence[str] = ()) -> str:
    original = " ".join(text.split())
    if not original:
        return text
    result = original

    if pool and len(pool) > 1 and rng.random() < MERGE_PROBABILITY:
        partner = pool[int(rng.integers(len(pool)))]
        partner = " ".join(partner.split())
        short_enough = len(result.split()) + len(partner.split()) <= MAX_WORDS_TO_MERGE * 2
        if partner and partner != result and short_enough and len(result.split()) <= MAX_WORDS_TO_MERGE:
            result = _merge(result, partner, JOINERS[int(rng.integers(len(JOINERS)))])

    if rng.random() < CASE_TOGGLE_PROBABILITY:
        result = _toggle_first_letter(result)
    if rng.random() < TRAILING_PERIOD_PROBABILITY:
        result = _toggle_trailing_period(result)

    return result or original
