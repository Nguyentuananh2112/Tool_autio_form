"""Thông báo kết thúc (màn 13): tóm tắt kết quả + "Gửi lại phản hồi lỗi" giữ nguyên nội dung."""

import json
from collections.abc import AsyncIterator
from types import SimpleNamespace
from typing import Any

import httpx
import pytest

from app.core.database import init_db
from app.main import create_app
from app.models.submission_log import EngineUsed
from app.services.campaign_summary import FailureCategory, categorize, failure_reasons
from app.services.form_parser import parse_form_html
from app.workers.submission_types import OutcomeKind, SubmitOutcome, payload_to_json
from tests.api_helpers import confirm_logic, rules_for_sample_form, wait_for_status
from tests.db_helpers import reset_database
from tests.fixtures.sample_form import FINAL_URL, build_html

FORM = parse_form_html(build_html(), FINAL_URL)
API = "/api/v1"


class FlakyHttp:
    """`fail_first` lần đầu: mất mạng (status 0); sau đó luôn thành công. Ghi lại nội dung từng lần gửi."""

    def __init__(self, fail_first: int, kind: OutcomeKind = OutcomeKind.NETWORK, code: int = 0) -> None:
        self.fail_first, self.kind, self.code = fail_first, kind, code
        self.sent: list[tuple[bool, str]] = []

    async def submit(self, structure: Any, payload: Any) -> SubmitOutcome:
        ok = len(self.sent) >= self.fail_first
        self.sent.append((ok, json.dumps(payload_to_json(payload), sort_keys=True, ensure_ascii=False)))
        if ok:
            return SubmitOutcome(OutcomeKind.SUCCESS, 200, EngineUsed.HTTPX)
        return SubmitOutcome(self.kind, self.code, EngineUsed.HTTPX, error="Không kết nối được tới Google Form.")

    async def aclose(self) -> None:
        return None


@pytest.fixture
async def app_client(monkeypatch: pytest.MonkeyPatch) -> AsyncIterator[tuple[httpx.AsyncClient, FlakyHttp]]:
    async def fake_parse(url: str) -> Any:
        return FORM

    monkeypatch.setattr("app.api.form_router.parse_google_form", fake_parse)
    monkeypatch.setattr("app.workers.campaign_runner.NETWORK_RETRIES", 0)  # không tự thử lại để đếm đúng số lỗi
    http = FlakyHttp(fail_first=2)
    await init_db()
    app = create_app(runner_kwargs={"http_factory": lambda _: http})
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        yield client, http
    await reset_database()


async def _run(client: httpx.AsyncClient, total: int = 4) -> str:
    form_id = (await client.post(f"{API}/forms/parse", json={"url": "https://forms.gle/x"})).json()["id"]
    await confirm_logic(client, form_id)
    body = {"form_id": form_id, "name": "Thử", "total_target": total, "rules": rules_for_sample_form(),
            "schedule": {"mode": "BURST", "concurrency": 1}, "use_playwright_fallback": False}
    campaign = (await client.post(f"{API}/campaigns", json=body)).json()
    await client.post(f"{API}/campaigns/{campaign['id']}/start")
    return campaign["id"]


async def test_tom_tat_gom_loi_va_cach_xu_ly(app_client) -> None:
    client, _ = app_client
    cid = await _run(client)
    await wait_for_status(client, cid, "COMPLETED")
    summary = (await client.get(f"{API}/campaigns/{cid}/summary")).json()
    assert (summary["completed_count"], summary["failed_count"], summary["remaining"]) == (2, 2, 0)
    assert summary["status"] == "COMPLETED" and summary["auto_paused"] is False
    [reason] = summary["reasons"]
    assert reason["category"] == "NETWORK" and reason["count"] == 2
    assert "Internet" in reason["fix"] and reason["detail"] == "Không kết nối được tới Google Form."
    assert summary["duration_seconds"] >= 0 and summary["form_title"] == FORM.title


async def test_gui_lai_dung_phan_hoi_loi_giu_nguyen_noi_dung(app_client) -> None:
    client, http = app_client
    cid = await _run(client)
    await wait_for_status(client, cid, "COMPLETED")
    failed_payloads = sorted(p for ok, p in http.sent if not ok)

    response = await client.post(f"{API}/campaigns/{cid}/retry-failed")
    assert response.status_code == 202 and response.json()["retried"] == 2
    done = await wait_for_status(client, cid, "COMPLETED")
    assert (done["completed_count"], done["failed_count"]) == (4, 0)

    assert len(http.sent) == 6  # chỉ gửi thêm đúng 2 phản hồi lỗi, không gửi lại 2 phản hồi đã thành công
    retried = sorted(p for _, p in http.sent[4:])
    assert retried == failed_payloads  # gửi lại đúng nội dung đã lỗi
    logs = (await client.get(f"{API}/campaigns/{cid}/logs")).json()
    assert len(logs) == 4 and all(log["is_success"] for log in logs)


async def test_khong_co_loi_thi_khong_gui_lai(app_client) -> None:
    client, http = app_client
    http.fail_first = 0
    cid = await _run(client, total=2)
    await wait_for_status(client, cid, "COMPLETED")
    response = await client.post(f"{API}/campaigns/{cid}/retry-failed")
    assert response.status_code == 422 and "Không có phản hồi lỗi" in response.json()["detail"]["message"]


async def test_toan_bo_loi_thi_trang_thai_loi_kem_ly_do_luu_lai(app_client) -> None:
    client, http = app_client
    http.fail_first = 99
    cid = await _run(client, total=3)
    done = await wait_for_status(client, cid, "FAILED")
    assert "Không gửi được phản hồi nào" in done["status_reason"]
    summary = (await client.get(f"{API}/campaigns/{cid}/summary")).json()
    assert summary["completed_count"] == 0 and summary["reasons"][0]["count"] == 3


@pytest.mark.parametrize(("code", "detail", "category"), [
    (400, "Câu hỏi bắt buộc", FailureCategory.REJECTED),
    (429, None, FailureCategory.RATE_LIMITED),
    (403, None, FailureCategory.RATE_LIMITED),
    (0, "Trình chờ quá lâu", FailureCategory.NETWORK),
    (400, "Google từ chối dữ liệu (400). Trình duyệt dự phòng: Chưa tải trình duyệt", FailureCategory.BROWSER),
    (200, "Form yêu cầu đăng nhập Google.", FailureCategory.FORM_CLOSED),
    (404, "Form không còn tồn tại hoặc đã ngừng nhận phản hồi.", FailureCategory.FORM_CLOSED),
    (500, "lạ", FailureCategory.OTHER),
])
def test_phan_loai_loi(code: int, detail: str | None, category: FailureCategory) -> None:
    assert categorize(SimpleNamespace(status_code=code, error_detail=detail, is_success=False)) == category


def test_gom_loi_nhieu_nhat_len_dau_bo_qua_thanh_cong() -> None:
    logs = [SimpleNamespace(status_code=400, error_detail="A", is_success=False)] * 3 + [
        SimpleNamespace(status_code=0, error_detail="B", is_success=False),
        SimpleNamespace(status_code=200, error_detail=None, is_success=True),
    ]
    reasons = failure_reasons(logs)
    assert [(r.category, r.count, r.detail) for r in reasons] == [("REJECTED", 3, "A"), ("NETWORK", 1, "B")]
