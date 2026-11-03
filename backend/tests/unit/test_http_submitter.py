"""Kiểm thử bộ gửi HTTPX (app/workers/http_submitter.py) — chỉ dùng httpx.MockTransport, không gọi mạng."""

import email.utils
from datetime import UTC, datetime, timedelta
from urllib.parse import parse_qsl

import httpx
import pytest

from app.models.submission_log import EngineUsed
from app.schemas.form_schema import ParsedFormStructure, ParsedSection
from app.workers.http_submitter import HttpSubmitter, classify_response, parse_retry_after
from app.workers.submission_types import OutcomeKind

VIEW_URL = "https://docs.google.com/forms/d/e/ABC/viewform"
SUBMIT_URL = "https://docs.google.com/forms/d/e/ABC/formResponse"
FORM_PAGE = '<form><input type="hidden" name="pageHistory" value="0"></form>'
FBZX_PAGE = '<form><input type="hidden" name="fbzx" value="-1"></form>'
CONFIRM_PAGE = "<html><body><div>Cảm ơn bạn đã tham gia!</div></body></html>"


def _structure() -> ParsedFormStructure:
    return ParsedFormStructure(
        title="Thử", view_url=VIEW_URL, submit_url=SUBMIT_URL, total_pages=1,
        sections=[ParsedSection(page_index=0, title="Thử")], questions=[],
    )


# ---------- parse_retry_after ----------

@pytest.mark.parametrize("value", [None, "", "   ", "abc", "-5", "1.5", "Mon, 99 Foo 2024"])
def test_retry_after_khong_hop_le_tra_ve_none(value: str | None) -> None:
    assert parse_retry_after(value) is None


@pytest.mark.parametrize(("value", "expected"), [("0", 0.0), ("120", 120.0), (" 30 ", 30.0)])
def test_retry_after_dang_so_giay(value: str, expected: float) -> None:
    assert parse_retry_after(value) == expected


def test_retry_after_dang_ngay_trong_tuong_lai() -> None:
    moment = datetime.now(UTC) + timedelta(seconds=120)
    result = parse_retry_after(email.utils.format_datetime(moment, usegmt=True))
    assert result is not None and 100 <= result <= 121


def test_retry_after_dang_ngay_trong_qua_khu_tra_ve_0() -> None:
    moment = datetime.now(UTC) - timedelta(hours=1)
    assert parse_retry_after(email.utils.format_datetime(moment, usegmt=True)) == 0.0


def test_retry_after_ngay_khong_mui_gio_coi_la_utc() -> None:
    moment = datetime.now(UTC) + timedelta(seconds=300)
    # "-0000" → parsedate_to_datetime trả về datetime không có tzinfo
    raw = moment.strftime("%a, %d %b %Y %H:%M:%S -0000")
    result = parse_retry_after(raw)
    assert result is not None and 280 <= result <= 301


# ---------- classify_response ----------

def test_200_trang_xac_nhan_khong_co_o_an_la_thanh_cong() -> None:
    outcome = classify_response(200, CONFIRM_PAGE, httpx.Headers())
    assert outcome.kind == OutcomeKind.SUCCESS and outcome.ok
    assert outcome.engine == EngineUsed.HTTPX and outcome.error is None


def test_200_cau_xac_nhan_tu_dat_van_thanh_cong() -> None:
    """Không dựa vào câu chữ: chủ form đổi câu xác nhận vẫn là thành công."""
    assert classify_response(200, "<p>Xong rồi nhé</p>", httpx.Headers()).kind == OutcomeKind.SUCCESS
    assert classify_response(200, "", httpx.Headers()).kind == OutcomeKind.SUCCESS


@pytest.mark.parametrize("body", [FORM_PAGE, FBZX_PAGE])
def test_200_tra_lai_trang_form_la_loi_du_lieu(body: str) -> None:
    outcome = classify_response(200, body, httpx.Headers())
    assert outcome.kind == OutcomeKind.VALIDATION
    assert outcome.status_code == 200 and outcome.error


@pytest.mark.parametrize("status", [429, 403])
def test_429_403_la_bi_chan_kem_retry_after(status: int) -> None:
    outcome = classify_response(status, "", httpx.Headers({"Retry-After": "45"}))
    assert outcome.kind == OutcomeKind.BLOCKED
    assert outcome.retry_after == 45.0 and outcome.status_code == status


def test_bi_chan_khong_co_retry_after() -> None:
    outcome = classify_response(429, "", httpx.Headers())
    assert outcome.kind == OutcomeKind.BLOCKED and outcome.retry_after is None


@pytest.mark.parametrize(
    ("status", "kind"),
    [
        (400, OutcomeKind.VALIDATION),
        (401, OutcomeKind.FATAL),
        (404, OutcomeKind.FATAL),
        (410, OutcomeKind.FATAL),
        (500, OutcomeKind.SERVER),
        (502, OutcomeKind.SERVER),
        (503, OutcomeKind.SERVER),
        (599, OutcomeKind.SERVER),
        (302, OutcomeKind.UNKNOWN),
        (204, OutcomeKind.UNKNOWN),
        (405, OutcomeKind.UNKNOWN),
        (418, OutcomeKind.UNKNOWN),
    ],
)
def test_phan_loai_theo_ma_trang_thai(status: int, kind: OutcomeKind) -> None:
    outcome = classify_response(status, FORM_PAGE, httpx.Headers())
    assert outcome.kind == kind
    assert outcome.status_code == status
    assert outcome.error
    assert outcome.retry_after is None


def test_loi_may_chu_ghi_ma_trong_thong_bao() -> None:
    assert "503" in (classify_response(503, "", httpx.Headers()).error or "")


# ---------- HttpSubmitter.submit qua MockTransport ----------

async def _submit(handler, payload=(("entry.1", "A"),)):
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    async with HttpSubmitter(user_agent="UA", client=client) as submitter:
        outcome = await submitter.submit(_structure(), list(payload))
    await client.aclose()
    return outcome


async def test_gui_post_dung_url_header_va_than_giu_khoa_lap() -> None:
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["method"] = request.method
        seen["url"] = str(request.url)
        seen["headers"] = request.headers
        seen["body"] = parse_qsl(request.content.decode("utf-8"), keep_blank_values=True)
        return httpx.Response(200, text=CONFIRM_PAGE)

    payload = [("entry.1", "Nữ"), ("entry.2", "A"), ("entry.2", "B & C"), ("fvv", "1"), ("pageHistory", "0")]
    outcome = await _submit(handler, payload)
    assert outcome.kind == OutcomeKind.SUCCESS
    assert seen["method"] == "POST" and seen["url"] == SUBMIT_URL
    headers = seen["headers"]
    assert isinstance(headers, httpx.Headers)
    assert headers["Content-Type"] == "application/x-www-form-urlencoded"
    assert headers["Referer"] == VIEW_URL
    assert headers["Origin"] == "https://docs.google.com"
    assert seen["body"] == payload


async def test_gui_bi_tra_lai_form_la_loi_du_lieu() -> None:
    outcome = await _submit(lambda request: httpx.Response(400, text=FORM_PAGE))
    assert outcome.kind == OutcomeKind.VALIDATION


async def test_gui_bi_chan_doc_retry_after() -> None:
    outcome = await _submit(lambda request: httpx.Response(429, headers={"Retry-After": "10"}))
    assert outcome.kind == OutcomeKind.BLOCKED and outcome.retry_after == 10.0


async def test_gui_het_thoi_gian_cho_la_loi_mang() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("chậm", request=request)

    outcome = await _submit(handler)
    assert outcome.kind == OutcomeKind.NETWORK and outcome.status_code == 0
    assert "thời gian" in (outcome.error or "")


async def test_gui_mat_ket_noi_la_loi_mang() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("không kết nối", request=request)

    outcome = await _submit(handler)
    assert outcome.kind == OutcomeKind.NETWORK and outcome.status_code == 0
    assert "Lỗi kết nối" in (outcome.error or "")


async def test_phan_hoi_la_ghi_them_thoi_gian() -> None:
    outcome = await _submit(lambda request: httpx.Response(302, text=""))
    assert outcome.kind == OutcomeKind.UNKNOWN
    assert "giây" in (outcome.error or "")


async def test_khong_dong_client_duoc_truyen_vao() -> None:
    client = httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(200)))
    async with HttpSubmitter(user_agent="UA", client=client):
        pass
    assert not client.is_closed
    await client.aclose()


async def test_tu_tao_client_thi_tu_dong() -> None:
    submitter = HttpSubmitter(user_agent="UA-Test")
    inner = submitter._client
    assert inner.headers["User-Agent"] == "UA-Test"
    await submitter.aclose()
    assert inner.is_closed
