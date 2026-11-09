"""Thao tác trên trang Google Form trong trình duyệt dự phòng: tìm nút Tiếp/Gửi, chọn câu Đánh giá.

BUG-017: Google viết chữ trên nút ở dạng Unicode TÁCH DẤU ("Gửi" = G + ư + dấu hỏi rời + i), so chuỗi
dựng sẵn "Gửi" không bao giờ khớp → không tìm thấy nút. Ưu tiên `jsname` cố định của Google,
dự phòng bằng chữ đã chuẩn hoá NFC (không phụ thuộc ngôn ngữ giao diện).
"""

from __future__ import annotations

import re
import unicodedata
from enum import StrEnum
from typing import Any

from app.schemas.form_schema import ParsedFormStructure, QuestionType
from app.services.spss.answers import GeneratedResponse

RENDER_TIMEOUT_MS = 15_000


class FormButton(StrEnum):
    SUBMIT = "SUBMIT"
    NEXT = "NEXT"


BUTTON_JSNAME: dict[FormButton, str] = {FormButton.SUBMIT: "M2UYVd", FormButton.NEXT: "OCpkoe"}
BUTTON_TEXT: dict[FormButton, re.Pattern[str]] = {
    FormButton.SUBMIT: re.compile(r"^\s*(gửi|submit|enviar|envoyer|senden|送信|提交)\s*$", re.IGNORECASE),
    FormButton.NEXT: re.compile(r"^\s*(tiếp|tiếp theo|next|siguiente|suivant|weiter|次へ|下一步)\s*$", re.IGNORECASE),
}


def normalize_label(text: str | None) -> str:
    return unicodedata.normalize("NFC", (text or "").replace("\xa0", " ")).strip()


def label_matches(button: FormButton, text: str | None) -> bool:
    return bool(BUTTON_TEXT[button].match(normalize_label(text)))


async def wait_until_rendered(page: Any) -> None:
    """Trang form vẽ nút bằng JavaScript: chờ có ít nhất một nút trước khi tìm."""
    await page.locator("[role=button]").first.wait_for(state="attached", timeout=RENDER_TIMEOUT_MS)


async def find_button(page: Any, button: FormButton) -> Any | None:
    by_jsname = page.locator(f'[role=button][jsname="{BUTTON_JSNAME[button]}"]')
    if await by_jsname.count():
        return by_jsname.first
    for candidate in await page.locator("[role=button]").all():
        if label_matches(button, await candidate.get_attribute("aria-label")) or label_matches(button, await candidate.inner_text()):
            return candidate
    return None


async def fill_ratings(page: Any, structure: ParsedFormStructure, response: GeneratedResponse) -> None:
    """Câu Đánh giá (sao) không nhận giá trị từ link điền sẵn → bấm đúng mức trên trang đang mở."""
    for question in structure.questions:
        answer = response.answers.get(question.entry_id)
        if question.type_id != QuestionType.RATING or answer is None or not answer.values:
            continue
        container = page.locator(f'[role=listitem]:has(input[name="entry.{question.entry_id}_sentinel"])')
        if not await container.count():
            continue  # câu nằm ở trang khác
        option = container.first.locator(f'[role=radio][data-value="{answer.values[0]}"]')
        if await option.count() and await option.first.get_attribute("aria-checked") != "true":
            await option.first.click()


async def is_confirmation(page: Any) -> bool:
    """Đã gửi xong: trang xác nhận không còn ô ẩn fbzx (cùng dấu hiệu với gửi trực tiếp — BUG-007).

    KHÔNG dựa vào URL: form nhiều trang đổi sang /formResponse ngay khi bấm "Tiếp" ở trang 1 (BUG-018).
    """
    return "/formResponse" in page.url and await page.locator('input[name="fbzx"]').count() == 0


async def page_history(page: Any) -> str | None:
    """Các trang đã đi qua ("0,1,3") — đổi khi sang trang sau, giữ nguyên khi Google báo lỗi."""
    field = page.locator('input[name="pageHistory"]')
    return await field.first.get_attribute("value") if await field.count() else None
