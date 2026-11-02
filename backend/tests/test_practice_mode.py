"""Chế độ tập dùng: form mẫu chạy được trọn vòng mà KHÔNG gọi tới bất kỳ bộ gửi thật nào."""

from collections.abc import AsyncIterator
from typing import Any

import httpx
import pytest

from app.core.database import init_db
from app.main import create_app
from app.schemas.campaign_schema import QuestionRuleConfig
from app.services.demo_form import build_demo_structure
from app.services.spss_generator import SurveyDataGenerator
from tests.api_helpers import wait_for_status
from tests.db_helpers import reset_database

API = "/api/v1"


class ExplodingHttp:
    """Nếu chế độ tập dùng lỡ gọi bộ gửi thật, test sẽ hỏng ngay."""

    async def submit(self, *_: Any) -> Any:
        raise AssertionError("Chế độ tập dùng không được gửi ra ngoài")

    async def aclose(self) -> None:
        return None


@pytest.fixture
async def client() -> AsyncIterator[httpx.AsyncClient]:
    await init_db()
    app = create_app(runner_kwargs={"http_factory": lambda _: ExplodingHttp()})
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as c:
        yield c
    await reset_database()


DEMO_RULES = [
    {"entry_id": "1004", "question_type": 4, "weights": {"Quán gần nhà": 60, "Chuỗi cà phê": 50}, "max_checked": 2},
    {"entry_id": "1040", "question_type": 0, "text_pool": ["Thêm chỗ ngồi", "Giảm giá cho sinh viên"]},
]


def test_demo_structure_is_valid_and_branches() -> None:
    structure = build_demo_structure()
    rules = [QuestionRuleConfig(**rule) for rule in DEMO_RULES]
    responses = SurveyDataGenerator(structure, rules, seed=3).generate(300)
    paths = {r.page_history_str for r in responses}
    assert paths == {"0,1,3", "0,2,3"}


async def test_demo_form_is_reused(client: httpx.AsyncClient) -> None:
    first = (await client.post(f"{API}/forms/demo")).json()
    second = (await client.post(f"{API}/forms/demo")).json()
    assert first["id"] == second["id"] and first["is_demo"] is True
    assert ".invalid" in first["submit_url"]


async def test_demo_campaign_and_trial_never_send(client: httpx.AsyncClient) -> None:
    form_id = (await client.post(f"{API}/forms/demo")).json()["id"]
    trial = (await client.post(f"{API}/campaigns/trial-submit", json={"form_id": form_id, "rules": DEMO_RULES})).json()
    assert trial["success"] and trial["engine_used"] == "SIMULATED"

    body = {"form_id": form_id, "name": "Tập dùng", "total_target": 8, "rules": DEMO_RULES}
    campaign = (await client.post(f"{API}/campaigns", json=body)).json()
    await client.post(f"{API}/campaigns/{campaign['id']}/start")
    done = await wait_for_status(client, campaign["id"], "COMPLETED")
    assert done["completed_count"] == 8
    logs = (await client.get(f"{API}/campaigns/{campaign['id']}/logs")).json()
    assert {log["engine_used"] for log in logs} == {"SIMULATED"}
