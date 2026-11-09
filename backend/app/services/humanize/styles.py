"""Kiểu gõ của từng người điền. Mỗi người chỉ có MỘT kiểu, dùng cho mọi câu tự luận của họ.

Tỷ lệ dựa trên: người thật khác nhau nhiều hơn AI (độ dài, dấu câu, chữ hoa — các nghiên cứu nhận diện
văn bản LLM); trả lời trên điện thoại ngắn hơn máy tính (Pew: ~80 so với ~113 ký tự); câu "không có / không
biết" là câu trả lời hợp lệ (DISQO, GESIS); người Việt gõ mạng hay viết tắt, bỏ dấu (ViLexNorm).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TypingStyle:
    name: str
    weight: float  # tỷ lệ người dùng kiểu này
    capitalize_start: float  # xác suất viết hoa chữ đầu câu
    final_period: float  # xác suất có dấu chấm cuối câu
    drop_commas: float  # xác suất bỏ hết dấu phẩy trong câu
    abbreviate: float  # xác suất viết tắt mỗi từ có trong bảng
    typo_per_word: float
    strip_diacritics: bool = False
    first_clause_only: float = 0.0  # lười: chỉ gõ vế đầu
    teen: bool = False


STYLES: tuple[TypingStyle, ...] = (
    # Gõ cẩn thận (hay trên máy tính): vẫn không hoàn hảo như AI
    TypingStyle("CAREFUL", 0.25, capitalize_start=0.85, final_period=0.45, drop_commas=0.1, abbreviate=0.0, typo_per_word=0.005),
    # Gõ thường ngày trên điện thoại
    TypingStyle("CASUAL", 0.40, capitalize_start=0.25, final_period=0.12, drop_commas=0.45, abbreviate=0.3, typo_per_word=0.012),
    # Lười / vội: ngắn, chữ thường, viết tắt nhiều
    TypingStyle("LAZY", 0.20, capitalize_start=0.05, final_period=0.03, drop_commas=0.8, abbreviate=0.65,
                typo_per_word=0.02, first_clause_only=0.5),
    # Gõ không dấu (bàn phím chưa bật tiếng Việt / quen gõ vậy)
    TypingStyle("NO_DIACRITICS", 0.10, capitalize_start=0.15, final_period=0.05, drop_commas=0.6, abbreviate=0.5,
                typo_per_word=0.01, strip_diacritics=True),
    # Teencode nhẹ (giới trẻ)
    TypingStyle("TEEN", 0.05, capitalize_start=0.0, final_period=0.0, drop_commas=0.7, abbreviate=0.8,
                typo_per_word=0.015, teen=True),
)


def style_weights() -> list[float]:
    total = sum(style.weight for style in STYLES)
    return [style.weight / total for style in STYLES]
