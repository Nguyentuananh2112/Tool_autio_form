"""Thói quen gõ tiếng Việt trên mạng: viết tắt, gõ không dấu, lỗi gõ nhanh.

Danh sách viết tắt lấy từ cách gõ phổ biến trên Facebook / Zalo / TikTok (teencode nhẹ, ai cũng đọc được);
không dùng teencode nặng kiểu "ck/vk", "iu" để câu trả lời khảo sát vẫn tự nhiên với mọi lứa tuổi.
"""

from __future__ import annotations

import re
import unicodedata

import numpy as np

# Từ (viết thường) → các cách viết tắt hay gặp. Cụm nhiều từ đặt trước để khớp trước.
ABBREVIATIONS: dict[str, tuple[str, ...]] = {
    "thương mại điện tử": ("tmđt",),
    "như thế nào": ("ntn",),
    "mọi người": ("mn", "mng"),
    "bình thường": ("bt", "bthg"),
    "sản phẩm": ("sp",),
    "khách hàng": ("kh",),
    "chất lượng": ("cl",),
    "khuyến mãi": ("km",),
    "facebook": ("fb",),
    "không": ("ko", "k", "hông", "khum"),
    "được": ("dc", "đc"),
    "gì": ("j",),
    "với": ("vs",),
    "rồi": ("r",),
    "vậy": ("v", "z"),
    "biết": ("bít",),
    "nhiều": ("nhìu",),
    "quá": ("qá", "wá"),
    "cũng": ("cg",),
    "người": ("ng",),
    "trước": ("trc",),
    "mình": ("mk", "mik"),
    "ok": ("oke", "okie"),
    "cảm ơn": ("cảm ơn", "thanks"),
}
# Teencode nhẹ hơn một bậc chỉ dùng cho kiểu "teen"
TEEN_EXTRA: dict[str, tuple[str, ...]] = {
    "quá": ("wá", "quáaa"),
    "nhé": ("nha", "nhaa"),
    "nha": ("nhaa", "nhaaa"),
    "luôn": ("lun",),
    "thật": ("thiệt",),
    "dễ thương": ("dth", "cute"),
}

_WORD = r"[0-9A-Za-zÀ-ỹđĐ]"


def strip_diacritics(text: str) -> str:
    """Gõ không dấu: bỏ mọi dấu thanh / dấu mũ, đ → d."""
    decomposed = unicodedata.normalize("NFD", text)
    stripped = "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")
    return unicodedata.normalize("NFC", stripped).replace("đ", "d").replace("Đ", "D")


def abbreviate(text: str, probability: float, rng: np.random.Generator, table: dict[str, tuple[str, ...]] = ABBREVIATIONS) -> str:
    """Thay từng lần xuất hiện của từ trong bảng bằng dạng viết tắt với xác suất `probability`."""
    if probability <= 0:
        return text
    for word, variants in table.items():
        pattern = re.compile(rf"(?<!{_WORD}){re.escape(word)}(?!{_WORD})", re.IGNORECASE)

        def replace(match: re.Match[str], variants: tuple[str, ...] = variants) -> str:
            if rng.random() >= probability:
                return match.group(0)
            return variants[int(rng.integers(len(variants)))]

        text = pattern.sub(replace, text)
    return text


def _typo(word: str, rng: np.random.Generator) -> str:
    letters = [i for i, ch in enumerate(word) if ch.isalpha()]
    if len(letters) < 3:
        return word
    kind = int(rng.integers(4))
    i = letters[int(rng.integers(1, len(letters)))]  # không đụng chữ cái đầu: người ta ít gõ sai chữ đầu
    if kind == 0:  # sót một chữ
        return word[:i] + word[i + 1:]
    if kind == 1:  # gõ đúp một chữ
        return word[:i] + word[i] + word[i:]
    if kind == 2 and i + 1 < len(word) and word[i + 1].isalpha():  # đảo hai chữ cạnh nhau
        return word[:i] + word[i + 1] + word[i] + word[i + 2:]
    return strip_diacritics(word)  # quên bỏ dấu một từ (gõ Telex vội)


def add_typos(text: str, per_word: float, rng: np.random.Generator) -> str:
    if per_word <= 0:
        return text
    words = text.split(" ")
    return " ".join(_typo(w, rng) if w and rng.random() < per_word else w for w in words)
