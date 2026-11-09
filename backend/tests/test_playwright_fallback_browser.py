"""Trình duyệt dự phòng chạy Chromium THẬT trên trang giả lập cấu trúc Google Form (BUG-017, BUG-018).

Không ra mạng: mọi request tới docs.google.com bị chặn và trả về HTML dựng sẵn. Máy chưa tải
Chromium (VD CI) thì bỏ qua.
"""

import unicodedata
from typing import Any

import pytest

from app.schemas.form_schema import ParsedFormStructure, QuestionType
from app.services.spss.answers import Answer, GeneratedResponse
from app.workers.form_page import FormButton, label_matches
from app.workers.playwright_fallback import PlaywrightSubmitter
from app.workers.submission_types import OutcomeKind
from tests.unit.spss_factories import form, option, question, section

BASE = "https://docs.google.com/forms/d/e/TEST"
# Google viết chữ trên nút ở dạng TÁCH DẤU — đúng như trang thật (đo 2026-11-09)
GUI = unicodedata.normalize("NFD", "Gửi")
TIEP = unicodedata.normalize("NFD", "Tiếp")

RATING_JS = """<script>
document.querySelectorAll('[role=radio]').forEach(r => r.addEventListener('click', () => {
  r.parentElement.querySelectorAll('[role=radio]').forEach(o => o.setAttribute('aria-checked', 'false'));
  r.setAttribute('aria-checked', 'true'); window.__rating = r.dataset.value;
}));
</script>"""


def _page(body: str, *, fbzx: bool = True, history: str = "0") -> str:
    hidden = f'<input type="hidden" name="fbzx" value="1"><input type="hidden" name="pageHistory" value="{history}">' if fbzx else ""
    return f"<html><body><form>{hidden}{body}</form></body></html>"


def _rating_item() -> str:
    radios = "".join(f'<div role="radio" data-value="{i}" aria-checked="false">{i}</div>' for i in range(1, 6))
    return f'<div role="listitem"><input type="hidden" name="entry.77_sentinel"><span>{radios}</span></div>{RATING_JS}'


def _pages(*, next_fails: bool = False, submit_fails: bool = False) -> dict[str, str]:
    on_next = "" if next_fails else f"location.href='{BASE}/formResponse?step=2'"
    next_alert = '<div role="alert">Câu hỏi bắt buộc</div>' if next_fails else ""
    on_submit = "" if submit_fails else f"location.href='{BASE}/formResponse?done=1'"
    return {
        "viewform": _page(
            _rating_item() + next_alert
            + f'<div role="button" jsname="OCpkoe" onclick="window.__ratingOnNext = window.__rating; {on_next}"><span>{TIEP}</span></div>'
        ),
        # Trang 2: URL ĐÃ là /formResponse nhưng CHƯA gửi (còn fbzx) — BUG-018
        "step=2": _page(f'<div role="button" aria-label="{GUI}" onclick="{on_submit}"><span>{GUI}</span></div>', history="0,1"),
        "done=1": _page("<p>Câu trả lời của bạn đã được ghi lại.</p>", fbzx=False),
    }


def _structure() -> ParsedFormStructure:
    structure = form(
        [section(0, None), section(1, 2)],
        [
            question("77", QuestionType.RATING, [option(str(i)) for i in range(1, 6)], required=True),
            question("88", QuestionType.MULTIPLE_CHOICE, [option("A"), option("B")], page=1),
        ],
    )
    return structure.model_copy(update={"view_url": f"{BASE}/viewform", "submit_url": f"{BASE}/formResponse"})


def _response() -> GeneratedResponse:
    return GeneratedResponse(sequence_number=1, answers={"77": Answer(values=["4"]), "88": Answer(values=["B"])}, page_history=[0, 1])


async def _submit(pages: dict[str, str]) -> tuple[Any, list[str]]:
    submitter = PlaywrightSubmitter(timeout_ms=5_000)
    try:
        await submitter.start()
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"Chưa có Chromium cho Playwright: {exc}")
    visited: list[str] = []
    original = submitter._browser.new_context

    async def new_context(**kwargs: Any) -> Any:
        context = await original(**kwargs)

        async def handle(route: Any) -> None:
            url = route.request.url
            visited.append(url)
            key = next((k for k in pages if k in url), None)
            await route.fulfill(status=200 if key else 404, content_type="text/html; charset=utf-8", body=pages.get(key, ""))

        await context.route("https://docs.google.com/**", handle)
        return context

    submitter._browser.new_context = new_context
    try:
        return await submitter.submit(_structure(), _response()), visited
    finally:
        await submitter.close()


def test_chu_nut_tach_dau_van_khop() -> None:
    assert GUI != "Gửi"  # dạng tách dấu khác chuỗi dựng sẵn — đúng nguyên nhân BUG-017
    assert label_matches(FormButton.SUBMIT, GUI) and label_matches(FormButton.NEXT, TIEP)
    assert label_matches(FormButton.SUBMIT, " Submit\xa0") and label_matches(FormButton.NEXT, "Next")
    assert not label_matches(FormButton.SUBMIT, "Xóa hết câu trả lời")


async def test_di_qua_hai_trang_bam_sao_roi_gui_thanh_cong() -> None:
    outcome, visited = await _submit(_pages())
    assert outcome.kind == OutcomeKind.SUCCESS, outcome.error
    assert any("entry.88=B" in url for url in visited)  # link điền sẵn mang câu trả lời
    assert visited[-1].endswith("done=1")


async def test_bam_tiep_ma_khong_sang_trang_bao_loi_cua_google() -> None:
    outcome, _ = await _submit(_pages(next_fails=True))
    assert outcome.kind == OutcomeKind.VALIDATION and outcome.error == "Câu hỏi bắt buộc"


async def test_url_formresponse_nhung_chua_gui_khong_tinh_thanh_cong() -> None:
    """BUG-018: trước đây thấy /formResponse sau khi bấm Tiếp là báo thành công dù chưa bấm Gửi."""
    outcome, _ = await _submit(_pages(submit_fails=True))
    assert outcome.kind == OutcomeKind.VALIDATION
    assert "không xác nhận" in (outcome.error or "")
