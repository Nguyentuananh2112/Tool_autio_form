from collections.abc import AsyncIterator

import pytest
from sqlalchemy import func, select

from app.core.database import AsyncSessionLocal, init_db
from tests.db_helpers import reset_database
from app.models import Campaign, CampaignStatus, Form, QuestionRule, SubmissionLog


@pytest.fixture
async def fresh_db() -> AsyncIterator[None]:
    await init_db()
    yield
    await reset_database()


async def _seed() -> Campaign:
    async with AsyncSessionLocal() as session:
        form = Form(title="Khảo sát thử", view_url="v", submit_url="s", parsed_structure={"questions": []})
        campaign = Campaign(form=form, name="Đợt 1", total_target=10, schedule_config={"mode": "BURST"})
        campaign.question_rules.append(QuestionRule(entry_id="123", question_type=2, config_json={"weights": {}}))
        session.add(campaign)
        await session.flush()
        session.add(SubmissionLog(
            campaign_id=campaign.id, sequence_number=1, engine_used="HTTPX",
            status_code=200, is_success=True, payload_sent={"entry.123": ["Nam"]},
        ))
        await session.commit()
        return campaign


async def test_defaults_and_json_roundtrip(fresh_db: None) -> None:
    campaign = await _seed()
    async with AsyncSessionLocal() as session:
        stored = await session.get(Campaign, campaign.id)
        assert stored is not None
        assert stored.status == CampaignStatus.IDLE
        assert stored.spss_groups == [] and stored.proxy_list == []
        assert stored.use_playwright_fallback is True
        log = (await session.execute(select(SubmissionLog))).scalar_one()
        assert log.id == 1 and log.payload_sent == {"entry.123": ["Nam"]}


async def test_deleting_form_cascades(fresh_db: None) -> None:
    campaign = await _seed()
    async with AsyncSessionLocal() as session:
        form = await session.get(Form, campaign.form_id)
        await session.delete(form)
        await session.commit()
        for model in (Campaign, QuestionRule, SubmissionLog):
            count = (await session.execute(select(func.count()).select_from(model))).scalar_one()
            assert count == 0, model.__name__
