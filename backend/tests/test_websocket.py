from typing import Any

import pytest
from starlette.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.core.config import get_settings
from app.main import create_app
from app.services.form_parser import parse_form_html
from tests.api_helpers import FakeHttp, rules_for_sample_form
from tests.fixtures.sample_form import FINAL_URL, build_html

FORM = parse_form_html(build_html(), FINAL_URL)
API = "/api/v1"


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> Any:
    async def fake_parse(url: str) -> Any:
        return FORM

    monkeypatch.setattr("app.api.form_router.parse_google_form", fake_parse)
    with TestClient(create_app(runner_kwargs={"http_factory": lambda _: FakeHttp()})) as test_client:
        yield test_client


def _campaign_id(client: TestClient) -> str:
    form_id = client.post(f"{API}/forms/parse", json={"url": "https://forms.gle/x"}).json()["id"]
    body = {"form_id": form_id, "name": "WS", "total_target": 3, "rules": rules_for_sample_form()}
    return client.post(f"{API}/campaigns", json=body).json()["id"]


def test_streams_snapshot_and_progress(client: TestClient) -> None:
    cid = _campaign_id(client)
    with client.websocket_connect(f"/ws/campaigns/{cid}") as ws:
        snapshot = ws.receive_json()
        assert snapshot["event"] == "SNAPSHOT" and snapshot["campaign"]["status"] == "IDLE"
        client.post(f"{API}/campaigns/{cid}/start")
        events: list[dict[str, Any]] = []
        while not (events and events[-1].get("status") == "COMPLETED"):
            events.append(ws.receive_json())
    updates = [e for e in events if e["event"] == "SUBMISSION_UPDATE"]
    assert [u["completed_count"] for u in updates] == [1, 2, 3]
    assert updates[0]["engine_used"] == "HTTPX" and updates[0]["page_history"].startswith("0")


def test_rejects_missing_token(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    cid = _campaign_id(client)
    monkeypatch.setattr(get_settings(), "APP_TOKEN", "secret")
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect(f"/ws/campaigns/{cid}") as ws:
            ws.receive_json()
    with client.websocket_connect(f"/ws/campaigns/{cid}?token=secret") as ws:
        assert ws.receive_json()["event"] == "SNAPSHOT"
