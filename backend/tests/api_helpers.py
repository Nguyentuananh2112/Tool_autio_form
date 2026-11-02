"""Công cụ dùng chung cho test API: app với submitter giả (không bao giờ gửi thật lên Google)."""

from __future__ import annotations

import asyncio
from typing import Any

from app.models.submission_log import EngineUsed
from app.workers.submission_types import OutcomeKind, SubmitOutcome


class FakeHttp:
    def __init__(self, delay: float = 0.0) -> None:
        self.delay = delay
        self.calls = 0

    async def submit(self, structure: Any, payload: Any) -> SubmitOutcome:
        self.calls += 1
        if self.delay:
            await asyncio.sleep(self.delay)
        return SubmitOutcome(OutcomeKind.SUCCESS, 200, EngineUsed.HTTPX)

    async def aclose(self) -> None:
        return None


def rules_for_sample_form() -> list[dict[str, Any]]:
    return [
        {"entry_id": "1001", "question_type": 2, "weights": {"Nam": 50, "Nữ": 50}},
        {"entry_id": "1008", "question_type": 1, "text_pool": ["Tốt", "Ổn"]},
    ]


async def wait_for_status(client: Any, campaign_id: str, wanted: str, timeout: float = 5.0) -> dict[str, Any]:
    deadline = asyncio.get_running_loop().time() + timeout
    while True:
        body = (await client.get(f"/api/v1/campaigns/{campaign_id}")).json()
        if body["status"] == wanted and not (wanted == "COMPLETED" and body["is_active"]):
            return body
        if asyncio.get_running_loop().time() > deadline:
            raise AssertionError(f"Hết thời gian chờ trạng thái {wanted}, hiện tại: {body}")
        await asyncio.sleep(0.02)
