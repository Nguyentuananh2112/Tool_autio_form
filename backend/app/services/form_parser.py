"""Bóc tách cấu trúc Google Form công khai (Mục 5.1 spec) — điểm vào chính của luồng.

Các phần được tách riêng: `form_url` (link), `fb_data_parser` (giải mã dữ liệu),
`form_errors` (lỗi). Module này lo tải HTML và ghép các bước lại.
"""

from __future__ import annotations

import logging

import httpx

from app.schemas.form_schema import ParsedFormStructure
from app.services.fb_data_parser import extract_fb_public_load_data, extract_fbzx, parse_fb_public_load_data
from app.services.form_errors import (
    FormClosedError,
    FormFetchError,
    FormParserError,
    FormRequiresLoginError,
    FormStructureError,
    InvalidFormUrlError,
)
from app.services.form_url import build_form_urls, ensure_public_final_url, normalize_form_url

logger = logging.getLogger(__name__)

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
)
DEFAULT_HEADERS: dict[str, str] = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
}



async def fetch_form_html(
    url: str,
    *,
    client: httpx.AsyncClient | None = None,
    timeout: float | None = None,
) -> tuple[str, str]:
    """Tải HTML của form. Trả về (html, final_url)."""
    normalized = normalize_form_url(url)

    user_agent = DEFAULT_USER_AGENT
    if timeout is None:
        from app.core.config import get_settings

        app_settings = get_settings()
        timeout = app_settings.FORM_FETCH_TIMEOUT_SECONDS
        user_agent = app_settings.HTTP_USER_AGENT

    headers = {**DEFAULT_HEADERS, "User-Agent": user_agent}

    owns_client = client is None
    http_client = client or httpx.AsyncClient(
        follow_redirects=True, timeout=httpx.Timeout(timeout), headers=headers
    )
    try:
        response = await http_client.get(normalized, headers=headers, follow_redirects=True)
    except httpx.TimeoutException as exc:
        raise FormFetchError("Hết thời gian chờ khi tải Google Form.") from exc
    except httpx.HTTPError as exc:
        raise FormFetchError(f"Không thể tải Google Form: {exc}") from exc
    finally:
        if owns_client:
            await http_client.aclose()

    final_url = str(response.url)
    ensure_public_final_url(final_url)

    if response.status_code == 404:
        raise FormFetchError("Không tìm thấy biểu mẫu (404). Kiểm tra lại link.")
    if response.status_code in (401, 403):
        raise FormRequiresLoginError("Biểu mẫu không công khai hoặc yêu cầu quyền truy cập.")
    if response.status_code >= 400:
        raise FormFetchError(f"Google Forms trả về mã lỗi HTTP {response.status_code}.")

    return response.text, final_url


def parse_form_html(html: str, final_url: str) -> ParsedFormStructure:
    """Phân tích HTML đã tải (thuần đồng bộ, dễ unit test)."""
    view_url, submit_url = build_form_urls(final_url)
    raw_data = extract_fb_public_load_data(html)
    fbzx = extract_fbzx(html, raw_data)
    return parse_fb_public_load_data(raw_data, view_url=view_url, submit_url=submit_url, fbzx=fbzx)


async def parse_google_form(
    url: str, *, client: httpx.AsyncClient | None = None, timeout: float | None = None
) -> ParsedFormStructure:
    """Điểm vào chính: tải và phân tích một link Google Form công khai."""
    html, final_url = await fetch_form_html(url, client=client, timeout=timeout)
    structure = parse_form_html(html, final_url)
    logger.info(
        "Đã phân tích form '%s': %d trang, %d câu hỏi",
        structure.title, structure.total_pages, len(structure.questions),
    )
    return structure


__all__ = [
    "FormClosedError",
    "FormFetchError",
    "FormParserError",
    "FormRequiresLoginError",
    "FormStructureError",
    "InvalidFormUrlError",
    "build_form_urls",
    "extract_fb_public_load_data",
    "extract_fbzx",
    "fetch_form_html",
    "normalize_form_url",
    "parse_fb_public_load_data",
    "parse_form_html",
    "parse_google_form",
]
