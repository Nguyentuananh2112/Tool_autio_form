"""API Soát logic + ràng buộc "phải soát trước khi chạy" (quy tắc 6, SPEC-020)."""

import uuid
from collections.abc import AsyncIterator
from typing import Any

import httpx
import pytest
from sqlalchemy import text

from app.core.database import AsyncSessionLocal, engine, init_db
from app.main import create_app
from app.models import Campaign
from app.schemas.logic_schema import AttitudeGroup, AttitudeItem, LogicMap, LogicRule
from app.services.form_parser import parse_form_html
from app.services.gemini_keys import AiKeysUnavailableError, KeyAttempt, KeySlot, KeyState
from tests.api_helpers import FakeHttp, rules_for_sample_form
from tests.db_helpers import reset_database
from tests.fixtures.sample_form import FINAL_URL, SATISFACTION_ENTRIES, build_html

FORM = parse_form_html(build_html(), FINAL_URL)
API = "/api/v1"
AI_LOGIC = LogicMap(
    attitude_groups=[AttitudeGroup(group_id="g1", name="Hài lòng", items=[
        *(AttitudeItem(entry_id=e) for e in SATISFACTION_ENTRIES), AttitudeItem(entry_id="1009"),
    ])],
    rules=[LogicRule(rule_id="r1", if_entry="1002", if_values=["Không"], then_entry="1001", then_values=["Nữ"])],
    model="gemini-test",
)


@pytest.fixture
async def client(monkeypatch: pytest.MonkeyPatch) -> AsyncIterator[httpx.AsyncClient]:
    async def fake_parse(url: str) -> Any:
        return FORM

    monkeypatch.setattr("app.api.form_router.parse_google_form", fake_parse)
    await init_db()
    app = create_app(runner_kwargs={"http_factory": lambda _: FakeHttp()})
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as c:
        yield c
    await reset_database()


@pytest.fixture
def ai(monkeypatch: pytest.MonkeyPatch) -> list[int]:
    calls: list[int] = []

    async def fake_run_with_keys(call: Any) -> LogicMap:
        calls.append(1)
        return AI_LOGIC.model_copy(deep=True)

    monkeypatch.setattr("app.services.logic_service.run_with_keys", fake_run_with_keys)
    return calls


async def _form(client: httpx.AsyncClient) -> str:
    return (await client.post(f"{API}/forms/parse", json={"url": "https://forms.gle/x"})).json()["id"]


async def test_form_moi_chua_co_ban_do(client: httpx.AsyncClient) -> None:
    form_id = await _form(client)
    response = await client.get(f"{API}/forms/{form_id}/logic")
    assert response.status_code == 200 and response.json() is None


async def test_doc_cau_hoi_luu_ban_do_chua_xac_nhan(client: httpx.AsyncClient, ai: list[int]) -> None:
    form_id = await _form(client)
    logic = (await client.post(f"{API}/forms/{form_id}/logic/analyze")).json()
    assert ai == [1] and logic["confirmed"] is False and logic["model"] == "gemini-test"
    stored = (await client.get(f"{API}/forms/{form_id}/logic")).json()
    assert stored["attitude_groups"][0]["items"][0]["entry_id"] == SATISFACTION_ENTRIES[0]


async def test_doc_lai_giu_do_dong_deu_nguoi_dung_chon(client: httpx.AsyncClient, ai: list[int]) -> None:
    form_id = await _form(client)
    logic = (await client.post(f"{API}/forms/{form_id}/logic/analyze")).json()
    await client.put(f"{API}/forms/{form_id}/logic", json={**logic, "consistency": "UNIFORM"})
    again = (await client.post(f"{API}/forms/{form_id}/logic/analyze")).json()
    assert again["consistency"] == "UNIFORM" and again["confirmed"] is False


async def test_het_luot_ai_tra_429_kem_trang_thai_key(client: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    async def exhausted(call: Any) -> Any:
        raise AiKeysUnavailableError([KeyAttempt(KeySlot.USER, KeyState.MISSING), KeyAttempt(KeySlot.SHARED, KeyState.EXHAUSTED)])

    monkeypatch.setattr("app.services.logic_service.run_with_keys", exhausted)
    form_id = await _form(client)
    response = await client.post(f"{API}/forms/{form_id}/logic/analyze")
    assert response.status_code == 429
    detail = response.json()["detail"]
    assert detail["code"] == "AI_KEYS_UNAVAILABLE" and "dán API key" in detail["message"]
    assert detail["keys"] == [{"slot": "USER", "state": "MISSING"}, {"slot": "SHARED", "state": "EXHAUSTED"}]


async def test_luu_ban_do_sai_tra_422_liet_ke_loi(client: httpx.AsyncClient) -> None:
    form_id = await _form(client)
    bad_rule = LogicRule(rule_id="r", if_entry="1002", if_values=["Có lẽ"], then_entry="1001", then_values=["Nữ"])
    bad = AI_LOGIC.model_copy(update={"rules": [bad_rule]})
    response = await client.put(f"{API}/forms/{form_id}/logic", json=bad.model_dump(mode="json"))
    assert response.status_code == 422
    assert any("Có lẽ" in e for e in response.json()["detail"]["errors"])


async def test_soat_mau_thu_bao_ket_qua(client: httpx.AsyncClient, ai: list[int]) -> None:
    form_id = await _form(client)
    await client.post(f"{API}/forms/{form_id}/logic/analyze")
    body = {"rules": rules_for_sample_form(), "sample_size": 120}
    result = (await client.post(f"{API}/forms/{form_id}/logic/review", json=body)).json()
    assert result["sample_size"] == 120 and result["ready"] is True and result["inconsistent_after"] == 0
    assert result["inconsistent_before"] > 0 and result["repaired"] > 0
    [corr] = result["correlations"]
    assert corr["after"] > corr["before"] + 0.2
    assert result["sample"]["answers"] and result["sample"]["attitude"]


async def test_soat_khi_chua_doc_cau_hoi_bao_loi(client: httpx.AsyncClient) -> None:
    form_id = await _form(client)
    response = await client.post(f"{API}/forms/{form_id}/logic/review", json={"rules": rules_for_sample_form()})
    assert response.status_code == 422 and "chưa được đọc câu hỏi" in response.json()["detail"]["errors"][0]


async def test_chua_xac_nhan_khong_tao_duoc_chien_dich_va_chup_ban_do(client: httpx.AsyncClient, ai: list[int]) -> None:
    form_id = await _form(client)
    body = {"form_id": form_id, "name": "x", "total_target": 5, "rules": rules_for_sample_form()}
    assert (await client.post(f"{API}/campaigns", json=body)).status_code == 422
    logic = (await client.post(f"{API}/forms/{form_id}/logic/analyze")).json()
    assert (await client.post(f"{API}/campaigns", json=body)).status_code == 422  # có bản đồ nhưng chưa xác nhận
    await client.put(f"{API}/forms/{form_id}/logic", json={**logic, "confirmed": True})
    campaign = (await client.post(f"{API}/campaigns", json=body)).json()
    async with AsyncSessionLocal() as session:
        stored = await session.get(Campaign, uuid.UUID(campaign["id"]))
        assert stored.logic_map["confirmed"] is True and stored.logic_map["rules"][0]["rule_id"] == "r1"


async def test_du_lieu_excel_khong_can_soat_logic(client: httpx.AsyncClient) -> None:
    form_id = await _form(client)
    body = {"form_id": form_id, "name": "x", "data_source": "EXCEL", "excel_records": [{"1001": "Nam", "1002": "Không", "1008": "Ổn"}]}
    response = await client.post(f"{API}/campaigns", json=body)
    assert response.status_code == 201, response.text


async def test_csdl_cu_duoc_them_cot_logic_map() -> None:
    async with engine.begin() as conn:
        for table in ("submission_logs", "question_rules", "campaigns", "forms"):
            await conn.execute(text(f"DROP TABLE IF EXISTS {table}"))
        await conn.execute(text(
            "CREATE TABLE forms (id CHAR(32) PRIMARY KEY, title VARCHAR(500) NOT NULL, view_url TEXT NOT NULL, "
            "submit_url TEXT NOT NULL, parsed_structure JSON NOT NULL, is_demo BOOLEAN NOT NULL DEFAULT 0, "
            "created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL)"
        ))
    await init_db()
    async with engine.begin() as conn:
        columns = {row[1] for row in (await conn.execute(text("PRAGMA table_info(forms)"))).all()}
        campaign_columns = {row[1] for row in (await conn.execute(text("PRAGMA table_info(campaigns)"))).all()}
    assert "logic_map" in columns and "logic_map" in campaign_columns
    await init_db()  # chạy lại không lỗi
    await reset_database()


@pytest.mark.parametrize(("keys", "user", "shared", "configured"), [
    ([(KeySlot.USER, None), (KeySlot.SHARED, None), (KeySlot.BACKUP, None)], False, False, False),
    ([(KeySlot.USER, None), (KeySlot.SHARED, "s"), (KeySlot.BACKUP, None)], False, True, True),
    ([(KeySlot.USER, None), (KeySlot.SHARED, None), (KeySlot.BACKUP, "b")], False, True, True),
    ([(KeySlot.USER, "u"), (KeySlot.SHARED, None), (KeySlot.BACKUP, None)], True, False, True),
])
async def test_cai_dat_cho_biet_key_rieng_va_key_chung(
    client: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch, keys: list, user: bool, shared: bool, configured: bool
) -> None:
    monkeypatch.setattr("app.api.settings_router.candidate_keys", lambda: keys)
    body = (await client.get(f"{API}/settings")).json()
    assert (body["gemini_user_key"], body["gemini_shared_key"], body["gemini_key_configured"]) == (user, shared, configured)
    assert all(value not in {"u", "s", "b"} for value in body.values())  # không bao giờ trả key ra ngoài
