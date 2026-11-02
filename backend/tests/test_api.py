import io
import json
from collections.abc import AsyncIterator
from typing import Any

import httpx
import pandas as pd
import pytest

from app.core.config import get_settings
from app.core.database import init_db
from app.main import create_app
from app.services.form_parser import parse_form_html
from tests.api_helpers import FakeHttp, rules_for_sample_form, wait_for_status
from tests.db_helpers import reset_database
from tests.fixtures.sample_form import FINAL_URL, build_html

FORM = parse_form_html(build_html(), FINAL_URL)
API = "/api/v1"


@pytest.fixture
async def http() -> FakeHttp:
    return FakeHttp()


@pytest.fixture
async def client(http: FakeHttp, monkeypatch: pytest.MonkeyPatch) -> AsyncIterator[httpx.AsyncClient]:
    async def fake_parse(url: str) -> Any:
        return FORM

    monkeypatch.setattr("app.api.form_router.parse_google_form", fake_parse)
    await init_db()
    app = create_app(runner_kwargs={"http_factory": lambda _: http})
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as c:
        yield c
    await reset_database()


async def _create_form(client: httpx.AsyncClient) -> str:
    response = await client.post(f"{API}/forms/parse", json={"url": "https://forms.gle/abc"})
    assert response.status_code == 201, response.text
    return response.json()["id"]


async def _create_campaign(client: httpx.AsyncClient, form_id: str, **extra: Any) -> dict[str, Any]:
    body = {"form_id": form_id, "name": "Thử", "total_target": 5, "rules": rules_for_sample_form(), **extra}
    response = await client.post(f"{API}/campaigns", json=body)
    assert response.status_code == 201, response.text
    return response.json()


async def test_health_and_token(client: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    assert (await client.get(f"{API}/health")).json()["database_ok"] is True
    monkeypatch.setattr(get_settings(), "APP_TOKEN", "secret-token")
    assert (await client.get(f"{API}/forms")).status_code == 401
    assert (await client.get(f"{API}/forms", headers={"X-App-Token": "secret-token"})).status_code == 200
    assert (await client.get(f"{API}/health")).status_code == 200


async def test_production_without_token_fails_closed(client: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(get_settings(), "ENVIRONMENT", "production")
    assert (await client.get(f"{API}/forms")).status_code == 401


async def test_form_endpoints(client: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    form_id = await _create_form(client)
    listed = (await client.get(f"{API}/forms")).json()
    assert listed[0]["question_count"] == 9 and listed[0]["total_pages"] == 3
    assert (await client.get(f"{API}/forms/{form_id}")).json()["structure"]["fbzx"] == "-987"

    from app.services.form_parser import parse_google_form
    monkeypatch.setattr("app.api.form_router.parse_google_form", parse_google_form)
    bad = await client.post(f"{API}/forms/parse", json={"url": "https://docs.google.com/forms/d/X/edit"})
    assert bad.status_code == 400 and "chỉnh sửa" in bad.json()["detail"]["message"]


async def test_invalid_campaign_lists_errors(client: httpx.AsyncClient) -> None:
    form_id = await _create_form(client)
    rules = [{"entry_id": "1001", "question_type": 2, "weights": {"Nam": 50, "__other_option__": 50}}]
    response = await client.post(f"{API}/campaigns", json={"form_id": form_id, "name": "x", "total_target": 5, "rules": rules})
    assert response.status_code == 422
    assert any("Mục khác" in e for e in response.json()["detail"]["errors"])


async def test_preview_spss(client: httpx.AsyncClient) -> None:
    form_id = await _create_form(client)
    body = {
        "form_id": form_id, "rules": rules_for_sample_form(),
        "spss_groups": [{"group_id": "g", "name": "HL", "mean": 4, "std": 0.7, "alpha_target": 0.8,
                         "entries": ["1003", "1004", "1005", "1006"]}],
    }
    result = (await client.post(f"{API}/campaigns/preview-spss", json=body)).json()
    assert result["groups"][0]["cronbach_alpha"] > 0.7


async def test_run_campaign_end_to_end(client: httpx.AsyncClient, http: FakeHttp) -> None:
    form_id = await _create_form(client)
    campaign = await _create_campaign(client, form_id)
    assert (await client.post(f"{API}/campaigns/{campaign['id']}/start")).status_code == 202
    done = await wait_for_status(client, campaign["id"], "COMPLETED")
    assert done["completed_count"] == 5 and http.calls == 5
    assert len((await client.get(f"{API}/campaigns/{campaign['id']}/logs")).json()) == 5
    assert (await client.post(f"{API}/campaigns/{campaign['id']}/start")).status_code == 409

    xlsx = await client.get(f"{API}/campaigns/{campaign['id']}/export")
    sheets = pd.read_excel(io.BytesIO(xlsx.content), sheet_name=None)
    assert set(sheets) == {"Dữ liệu", "SPSS (mã số)"} and len(sheets["Dữ liệu"]) == 5
    csv = await client.get(f"{API}/campaigns/{campaign['id']}/export", params={"format": "csv"})
    assert csv.content.startswith("﻿".encode()) and "Giới tính" in csv.content.decode("utf-8-sig")


async def test_pause_resume_and_stop(client: httpx.AsyncClient, http: FakeHttp) -> None:
    http.delay = 0.05
    form_id = await _create_form(client)
    campaign = await _create_campaign(client, form_id, total_target=40, schedule={"mode": "BURST", "concurrency": 1})
    cid = campaign["id"]
    assert (await client.post(f"{API}/campaigns/{cid}/pause")).status_code == 409  # chưa chạy
    await client.post(f"{API}/campaigns/{cid}/start")
    await wait_for_status(client, cid, "RUNNING")
    await client.post(f"{API}/campaigns/{cid}/pause")
    paused = await wait_for_status(client, cid, "PAUSED")
    assert paused["pause_reason"] == "Bạn đã tạm dừng chiến dịch."
    await client.post(f"{API}/campaigns/{cid}/resume")
    await wait_for_status(client, cid, "RUNNING")
    stopped = (await client.post(f"{API}/campaigns/{cid}/stop")).json()
    assert stopped["status"] == "PAUSED" and not stopped["is_active"] and stopped["completed_count"] < 40
    http.delay = 0.0
    await client.post(f"{API}/campaigns/{cid}/resume")
    assert (await wait_for_status(client, cid, "COMPLETED"))["completed_count"] == 40


async def test_excel_flow_and_trial_submit(client: httpx.AsyncClient, http: FakeHttp) -> None:
    form_id = await _create_form(client)
    frame = pd.DataFrame({"Giới tính": ["Nam", "Nữ"], "Có dùng sản phẩm?": ["Không", "Không"]})
    buffer = io.BytesIO()
    frame.to_excel(buffer, index=False)
    files = {"file": ("data.xlsx", buffer.getvalue(), "application/octet-stream")}
    preview = (await client.post(f"{API}/forms/{form_id}/parse-excel", files=files)).json()
    assert preview["row_count"] == 2
    converted = (await client.post(
        f"{API}/forms/{form_id}/excel-convert", files=files, data={"mappings": json.dumps(preview["mappings"])},
    )).json()
    assert converted["report"]["valid_rows"] == 2
    campaign = await _create_campaign(client, form_id, data_source="EXCEL", total_target=None,
                                      rules=[], excel_records=converted["records"])
    assert campaign["total_target"] == 2

    trial = (await client.post(f"{API}/campaigns/trial-submit", json={"form_id": form_id, "rules": rules_for_sample_form()})).json()
    assert trial["success"] is True and trial["payload_sent"]["fvv"] == "1"


async def test_distribution_and_log_paths(client: httpx.AsyncClient) -> None:
    form_id = await _create_form(client)
    campaign = await _create_campaign(client, form_id)
    await client.post(f"{API}/campaigns/{campaign['id']}/start")
    await wait_for_status(client, campaign["id"], "COMPLETED")
    logs = (await client.get(f"{API}/campaigns/{campaign['id']}/logs")).json()
    assert all(log["page_history"].startswith("0") for log in logs)
    dist = {d["entry_id"]: d for d in (await client.get(f"{API}/campaigns/{campaign['id']}/distribution")).json()}
    gender = dist["1001"]
    assert gender["answered"] == 5 and sum(o["sent_count"] for o in gender["options"]) == 5
    assert [o["target_pct"] for o in gender["options"]] == [50.0, 50.0, 0.0]


async def test_datetimes_are_utc_aware(client: httpx.AsyncClient) -> None:
    form_id = await _create_form(client)
    created = (await client.get(f"{API}/forms/{form_id}")).json()["created_at"]
    assert created.endswith("Z") or created.endswith("+00:00")


async def test_preview_spss_ignores_unrelated_missing_questions(client: httpx.AsyncClient) -> None:
    form_id = await _create_form(client)
    body = {
        "form_id": form_id,
        "rules": [{"entry_id": "1001", "question_type": 2, "weights": {"Nam": 50, "__other_option__": 50}}],
        "spss_groups": [{"group_id": "g", "name": "HL", "mean": 4, "std": 0.7, "r": 0.5, "entries": ["1003", "1004"]}],
    }
    response = await client.post(f"{API}/campaigns/preview-spss", json=body)
    assert response.status_code == 200 and response.json()["groups"][0]["n_items"] == 2
