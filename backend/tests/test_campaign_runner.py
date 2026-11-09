import asyncio
import uuid
from collections.abc import AsyncIterator
from typing import Any

import pytest
from sqlalchemy import func, select

from app.core.database import AsyncSessionLocal, init_db
from app.models import Campaign, CampaignStatus, Form, QuestionRule, SubmissionLog
from app.models.submission_log import EngineUsed
from app.services.form_parser import parse_form_html
from app.workers.campaign_control import CampaignControl, EventBus
from app.workers.campaign_runner import CampaignRunner
from app.workers.rate_guard import RateGuard
from app.workers.submission_types import OutcomeKind, SubmitOutcome
from tests.db_helpers import reset_database
from tests.fixtures.sample_form import FINAL_URL, build_html

FORM = parse_form_html(build_html(), FINAL_URL)


class ScriptedHttp:
    """Trả về lần lượt các kết quả đã định; hết kịch bản thì luôn thành công."""

    def __init__(self, script: list[OutcomeKind]) -> None:
        self.script = list(script)
        self.calls = 0

    async def submit(self, structure: Any, payload: Any) -> SubmitOutcome:
        self.calls += 1
        kind = self.script.pop(0) if self.script else OutcomeKind.SUCCESS
        code = {OutcomeKind.SUCCESS: 200, OutcomeKind.BLOCKED: 429, OutcomeKind.VALIDATION: 400}.get(kind, 0)
        return SubmitOutcome(kind, code, EngineUsed.HTTPX, error=None if kind == OutcomeKind.SUCCESS else kind.value)

    async def aclose(self) -> None:
        return None


class FakeBrowser:
    def __init__(self) -> None:
        self.calls = 0

    async def submit(self, structure: Any, response: Any) -> SubmitOutcome:
        self.calls += 1
        return SubmitOutcome(OutcomeKind.SUCCESS, 200, EngineUsed.PLAYWRIGHT)

    async def close(self) -> None:
        return None


@pytest.fixture
async def campaign_id() -> AsyncIterator[uuid.UUID]:
    await init_db()
    async with AsyncSessionLocal() as session:
        form = Form(title=FORM.title, view_url=FORM.view_url, submit_url=FORM.submit_url,
                    parsed_structure=FORM.model_dump(mode="json"))
        campaign = Campaign(form=form, name="Thử", total_target=6,
                            schedule_config={"mode": "BURST", "concurrency": 2})
        campaign.question_rules.append(QuestionRule(
            entry_id="1008", question_type=1, config_json={}, cached_ai_pool=["Tốt", "Ổn"],
        ))
        session.add(campaign)
        await session.commit()
        cid = campaign.id
    yield cid
    await reset_database()


def _runner(cid: uuid.UUID, http: ScriptedHttp, browser: FakeBrowser, bus: EventBus, control: CampaignControl) -> CampaignRunner:
    return CampaignRunner(
        cid, control=control, bus=bus,
        http_factory=lambda _: http, browser_factory=lambda _: browser,
        rate_guard=RateGuard(base_cooldown_seconds=0.01, max_cooldown_seconds=0.05),
    )


async def _counts(cid: uuid.UUID) -> tuple[str, int, int, int]:
    async with AsyncSessionLocal() as session:
        campaign = await session.get(Campaign, cid)
        logs = (await session.execute(select(func.count()).select_from(SubmissionLog))).scalar_one()
        assert campaign is not None
        return campaign.status, campaign.completed_count, campaign.failed_count, logs


async def test_runs_to_completion_with_browser_fallback(campaign_id: uuid.UUID) -> None:
    http, browser, bus = ScriptedHttp([OutcomeKind.VALIDATION, OutcomeKind.BLOCKED]), FakeBrowser(), EventBus()
    events = bus.subscribe(str(campaign_id))
    status = await _runner(campaign_id, http, browser, bus, CampaignControl(str(campaign_id))).run()
    assert status == CampaignStatus.COMPLETED
    assert await _counts(campaign_id) == ("COMPLETED", 6, 0, 6)
    assert browser.calls == 1
    kinds = [events.get_nowait()["event"] for _ in range(events.qsize())]
    assert kinds.count("SUBMISSION_UPDATE") == 6 and "RATE_LIMITED" in kinds


async def test_auto_pause_then_resume_finishes(campaign_id: uuid.UUID) -> None:
    http = ScriptedHttp([OutcomeKind.BLOCKED] * 3)
    control, bus = CampaignControl(str(campaign_id)), EventBus()
    events = bus.subscribe(str(campaign_id))
    task = asyncio.create_task(_runner(campaign_id, http, FakeBrowser(), bus, control).run())
    for _ in range(200):
        await asyncio.sleep(0.01)
        if (await _counts(campaign_id))[0] == "PAUSED":
            break
    assert control.is_paused and "Google" in (control.pause_reason or "")
    control.resume()
    assert await asyncio.wait_for(task, timeout=5) == CampaignStatus.COMPLETED
    assert await _counts(campaign_id) == ("COMPLETED", 6, 0, 6)
    statuses = [e["status"] for e in (events.get_nowait() for _ in range(events.qsize())) if e["event"] == "STATUS_CHANGE"]
    assert statuses == ["RUNNING", "PAUSED", "RUNNING", "COMPLETED"]


async def test_resume_skips_already_sent(campaign_id: uuid.UUID) -> None:
    control = CampaignControl(str(campaign_id))
    http = ScriptedHttp([])
    first = _runner(campaign_id, http, FakeBrowser(), EventBus(), control)
    original_record = first._record

    async def record_then_stop(response: Any, outcome: SubmitOutcome) -> None:
        await original_record(response, outcome)
        if first.completed == 3:
            control.cancel()

    first._record = record_then_stop  # type: ignore[method-assign]
    assert await first.run() == CampaignStatus.PAUSED
    status, completed, _, _ = await _counts(campaign_id)
    assert status == "PAUSED" and 3 <= completed < 6

    second_http = ScriptedHttp([])
    assert await _runner(campaign_id, second_http, FakeBrowser(), EventBus(), CampaignControl(str(campaign_id))).run() == CampaignStatus.COMPLETED
    assert await _counts(campaign_id) == ("COMPLETED", 6, 0, 6)
    assert second_http.calls == 6 - completed


class RejectingBrowser(FakeBrowser):
    async def submit(self, structure: Any, response: Any) -> SubmitOutcome:
        self.calls += 1
        return SubmitOutcome(OutcomeKind.VALIDATION, 400, EngineUsed.PLAYWRIGHT, error="Không tìm thấy nút")


async def test_form_tu_choi_lien_tiep_thi_tu_tam_dung(campaign_id: uuid.UUID) -> None:
    """BUG-017: form có câu bắt buộc bị bỏ qua → mọi lần đều 400; dừng sau 5 lần thay vì đốt hết lượt."""
    async with AsyncSessionLocal() as session:
        campaign = await session.get(Campaign, campaign_id)
        campaign.total_target = 20
        campaign.schedule_config = {"mode": "BURST", "concurrency": 1}
        await session.commit()
    control = CampaignControl(str(campaign_id))
    task = asyncio.create_task(
        _runner(campaign_id, ScriptedHttp([OutcomeKind.VALIDATION] * 50), RejectingBrowser(), EventBus(), control).run()
    )
    for _ in range(300):
        await asyncio.sleep(0.01)
        if (await _counts(campaign_id))[0] == "PAUSED":
            break
    status, completed, failed, _ = await _counts(campaign_id)
    assert status == "PAUSED" and completed == 0 and failed == 5
    assert "5 phản hồi liên tiếp" in (control.pause_reason or "")
    control.cancel()
    await asyncio.wait_for(task, timeout=5)


async def test_that_bai_xen_ke_thanh_cong_khong_tam_dung(campaign_id: uuid.UUID) -> None:
    script = [OutcomeKind.VALIDATION, OutcomeKind.SUCCESS] * 3
    status = await _runner(campaign_id, ScriptedHttp(script), RejectingBrowser(), EventBus(), CampaignControl(str(campaign_id))).run()
    assert status == CampaignStatus.COMPLETED
    assert await _counts(campaign_id) == ("COMPLETED", 3, 3, 6)
