"""Trình duyệt dự phòng (Mục 5.4.C bước 3) cho form có kiểm tra dữ liệu phức tạp (lỗi 400).

Cách làm: mở link điền sẵn (`viewform?usp=pp_url&entry.X=...`) rồi chỉ bấm "Tiếp"/"Gửi" —
Google tự đi đúng nhánh, không cần tìm và click từng ô. KHÔNG dùng để lách lỗi 429/403
(dev-notes SPEC-012). Chromium được tải riêng khi người dùng bật tính năng (RISK-006).
"""

from __future__ import annotations

import logging
import re
from typing import Any
from urllib.parse import urlencode

from app.models.submission_log import EngineUsed
from app.schemas.form_schema import ParsedFormStructure
from app.services.spss_generator import ANSWER_KIND_DATE, ANSWER_KIND_TIME, GeneratedResponse
from app.workers.submission_types import OutcomeKind, SubmitOutcome

logger = logging.getLogger(__name__)

SUBMIT_BUTTON = re.compile(r"^\s*(Gửi|Submit)\s*$", re.IGNORECASE)
NEXT_BUTTON = re.compile(r"^\s*(Tiếp|Next)\s*$", re.IGNORECASE)
DEFAULT_TIMEOUT_MS = 30_000


class FallbackUnavailableError(RuntimeError):
    pass


def build_prefill_url(structure: ParsedFormStructure, response: GeneratedResponse) -> str:
    pairs: list[tuple[str, str]] = [("usp", "pp_url")]
    for entry_id, answer in response.answers.items():
        key = f"entry.{entry_id}"
        if answer.kind in (ANSWER_KIND_DATE, ANSWER_KIND_TIME):
            pairs.append((key, answer.values[0]))
            continue
        pairs.extend((key, value) for value in answer.values)
        if answer.other_text is not None:
            pairs.append((f"{key}.other_option_response", answer.other_text))
    return f"{structure.view_url}?{urlencode(pairs)}"


class PlaywrightSubmitter:
    def __init__(self, *, headless: bool = True, timeout_ms: int = DEFAULT_TIMEOUT_MS, proxy: str | None = None) -> None:
        self._headless = headless
        self._timeout_ms = timeout_ms
        self._proxy = proxy
        self._playwright: Any = None
        self._browser: Any = None

    async def start(self) -> None:
        if self._browser is not None:
            return
        try:
            from playwright.async_api import Error as PlaywrightError
            from playwright.async_api import async_playwright
        except ImportError as exc:
            raise FallbackUnavailableError("Chưa cài thư viện Playwright.") from exc
        try:
            self._playwright = await async_playwright().start()
            launch_args: dict[str, Any] = {"headless": self._headless}
            if self._proxy:
                launch_args["proxy"] = {"server": self._proxy}
            self._browser = await self._playwright.chromium.launch(**launch_args)
        except PlaywrightError as exc:
            await self.close()
            raise FallbackUnavailableError(
                "Chưa tải trình duyệt Chromium. Bật lại tính năng trong Cài đặt để tải (~150 MB)."
            ) from exc

    async def close(self) -> None:
        if self._browser is not None:
            await self._browser.close()
            self._browser = None
        if self._playwright is not None:
            await self._playwright.stop()
            self._playwright = None

    async def submit(self, structure: ParsedFormStructure, response: GeneratedResponse) -> SubmitOutcome:
        await self.start()
        from playwright.async_api import Error as PlaywrightError
        from playwright.async_api import TimeoutError as PlaywrightTimeoutError

        context = await self._browser.new_context(locale="vi-VN")
        page = await context.new_page()
        page.set_default_timeout(self._timeout_ms)
        try:
            await page.goto(build_prefill_url(structure, response), wait_until="domcontentloaded")
            for _ in range(structure.total_pages + 2):
                if "/formResponse" in page.url:
                    return SubmitOutcome(OutcomeKind.SUCCESS, 200, EngineUsed.PLAYWRIGHT)
                submit_button = page.get_by_role("button", name=SUBMIT_BUTTON)
                next_button = page.get_by_role("button", name=NEXT_BUTTON)
                if await submit_button.count():
                    await submit_button.first.click()
                    await page.wait_for_url(re.compile(r"/formResponse"), timeout=self._timeout_ms)
                    continue
                if await next_button.count():
                    before = page.url
                    await next_button.first.click()
                    await page.wait_for_load_state("domcontentloaded")
                    error = await self._visible_error(page)
                    if error and page.url == before:
                        return SubmitOutcome(OutcomeKind.VALIDATION, 400, EngineUsed.PLAYWRIGHT, error=error)
                    continue
                break
            error = await self._visible_error(page)
            return SubmitOutcome(
                OutcomeKind.VALIDATION, 400, EngineUsed.PLAYWRIGHT,
                error=error or "Không tìm thấy nút Tiếp/Gửi trên trang form.",
            )
        except PlaywrightTimeoutError:
            error = await self._visible_error(page)
            return SubmitOutcome(
                OutcomeKind.VALIDATION if error else OutcomeKind.NETWORK, 0, EngineUsed.PLAYWRIGHT,
                error=error or "Trình duyệt chờ trang form quá lâu.",
            )
        except PlaywrightError as exc:
            return SubmitOutcome(OutcomeKind.NETWORK, 0, EngineUsed.PLAYWRIGHT, error=f"Lỗi trình duyệt: {exc}")
        finally:
            await context.close()

    @staticmethod
    async def _visible_error(page: Any) -> str | None:
        alerts = page.locator('[role="alert"]')
        try:
            for index in range(await alerts.count()):
                text = (await alerts.nth(index).inner_text()).strip()
                if text:
                    return text
        except Exception:  # noqa: BLE001 — chỉ để lấy thông báo, không được làm hỏng luồng chính
            logger.debug("Không đọc được thông báo lỗi trên trang", exc_info=True)
        return None
