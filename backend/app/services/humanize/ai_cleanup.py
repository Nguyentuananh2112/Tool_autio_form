"""Gỡ dấu vết văn phong AI khỏi câu Gemini sinh, TRƯỚC khi lưu vào pool.

AI hay: gạch đầu dòng / đánh số, ngoặc kép bao cả câu, gạch ngang dài (—), mở đầu sáo rỗng ("Theo tôi,",
"Tôi nghĩ rằng"), kết bằng dấu chấm than / nhiều câu hoàn chỉnh. Người trả lời khảo sát gần như không làm vậy.
"""

from __future__ import annotations

import re

_LEADING_MARKERS = re.compile(r"^\s*(?:[-*•–—]+|\d+[.)]|[a-zA-Z][.)])\s+")
_WRAPPING_QUOTES = re.compile(r'^\s*["“”\'‘’«»]+(.*?)["“”\'‘’«»]+\s*$', re.DOTALL)
_STOCK_OPENERS = re.compile(
    r"^(?:theo (?:tôi|mình|em|ý kiến của (?:tôi|mình|em))|tôi (?:nghĩ|thấy|cho) (?:rằng|là)|"
    r"cá nhân (?:tôi|mình|em)|ý kiến của (?:tôi|mình|em) là|đối với (?:tôi|mình|em))\s*[,:]?\s*",
    re.IGNORECASE,
)


def clean_ai_text(text: str) -> str:
    cleaned = " ".join(text.split())
    cleaned = _LEADING_MARKERS.sub("", cleaned)
    quoted = _WRAPPING_QUOTES.match(cleaned)
    if quoted:
        cleaned = quoted.group(1).strip()
    cleaned = cleaned.replace(" — ", ", ").replace("—", ", ").replace(" – ", ", ")
    cleaned = cleaned.replace("…", "...").replace("!!", "!")
    opener = _STOCK_OPENERS.match(cleaned)
    if opener and len(cleaned) - opener.end() > 8:  # bỏ "Theo tôi," nếu sau đó vẫn còn nội dung
        rest = cleaned[opener.end():]
        cleaned = rest[:1].upper() + rest[1:]
    return cleaned.strip(" ,;")
