"""Áp kiểu gõ của MỘT người lên mọi câu tự luận của họ trong một phản hồi.

Chạy trong bộ sinh với RNG theo seed chiến dịch → "Gửi lại phản hồi lỗi" sinh ra đúng câu cũ.
"""

from __future__ import annotations

import re
from collections.abc import MutableMapping

import numpy as np

from app.services.humanize.styles import STYLES, TypingStyle, style_weights
from app.services.humanize.vietnamese import TEEN_EXTRA, abbreviate, add_typos, strip_diacritics
from app.services.spss.answers import ANSWER_KIND_TEXT, Answer

_END_PUNCT = re.compile(r"[.!?…]+$")
_CLAUSE_SPLIT = re.compile(r"\s*[,;.]\s+|\s+(?:và|nhưng|vì|nên)\s+")
MIN_FIRST_CLAUSE_WORDS = 2


def pick_style(rng: np.random.Generator) -> TypingStyle:
    return STYLES[int(rng.choice(len(STYLES), p=style_weights()))]


def _set_first_letter(text: str, upper: bool) -> str:
    for index, char in enumerate(text):
        if char.isalpha():
            return text[:index] + (char.upper() if upper else char.lower()) + text[index + 1:]
    return text


def style_text(text: str, style: TypingStyle, rng: np.random.Generator) -> str:
    result = " ".join(text.split())
    if not result:
        return text
    if style.first_clause_only and rng.random() < style.first_clause_only:
        first = _CLAUSE_SPLIT.split(result, maxsplit=1)[0]
        if len(first.split()) >= MIN_FIRST_CLAUSE_WORDS:
            result = first
    result = abbreviate(result, style.abbreviate, rng)
    if style.teen:
        result = abbreviate(result, 0.6, rng, TEEN_EXTRA)
    if style.strip_diacritics:
        result = strip_diacritics(result)
    result = add_typos(result, style.typo_per_word, rng)
    if rng.random() < style.drop_commas:
        result = re.sub(r"\s*,\s*", " ", result)
    result = _END_PUNCT.sub("", result).rstrip()
    if rng.random() < style.final_period:
        result += "."
    if style.teen:
        result = result.lower()
    result = _set_first_letter(result, upper=rng.random() < style.capitalize_start)
    return " ".join(result.split()) or text


def humanize_answers(answers: MutableMapping[str, Answer], rng: np.random.Generator) -> TypingStyle:
    """Chọn kiểu gõ cho người này rồi áp lên câu tự luận và chữ ở ô "Mục khác"."""
    style = pick_style(rng)
    for entry_id, answer in list(answers.items()):
        if answer.kind == ANSWER_KIND_TEXT and answer.values:
            answers[entry_id] = Answer(values=[style_text(answer.values[0], style, rng)], kind=answer.kind,
                                       numeric_value=answer.numeric_value)
        elif answer.other_text:
            answer.other_text = style_text(answer.other_text, style, rng)
    return style
