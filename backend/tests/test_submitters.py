from urllib.parse import parse_qsl, urlsplit

import httpx
import numpy as np
import pytest

from app.services.form_parser import parse_form_html
from app.services.spss_generator import Answer, GeneratedResponse, build_payload_tuples
from app.workers.http_submitter import HttpSubmitter, parse_retry_after
from app.workers.playwright_fallback import build_prefill_url
from app.workers.rate_guard import RateGuard
from app.workers.scheduler import poisson_delays, remaining_duration_seconds
from app.workers.submission_types import OutcomeKind, payload_to_json
from tests.fixtures.sample_form import FINAL_URL, build_html

FORM = parse_form_html(build_html(), FINAL_URL)
RESPONSE = GeneratedResponse(
    sequence_number=1,
    answers={
        "1001": Answer(values=["__other_option__"], other_text="Không tiết lộ"),
        "1007": Answer(values=["FB", "TikTok"]),
    },
    page_history=[0, 1, 2],
)


async def _submit_with(status: int, body: str, headers: dict[str, str] | None = None) -> tuple:
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["body"] = request.content.decode()
        seen["content_type"] = request.headers["content-type"]
        return httpx.Response(status, text=body, headers=headers or {})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    async with HttpSubmitter(user_agent="test", client=client) as submitter:
        outcome = await submitter.submit(FORM, build_payload_tuples(RESPONSE, FORM.fbzx))
    await client.aclose()
    return outcome, seen


@pytest.mark.parametrize(
    ("status", "body", "kind"),
    [
        (200, "<div>Câu trả lời của bạn đã được ghi lại.</div>", OutcomeKind.SUCCESS),
        (200, "<script>var FB_PUBLIC_LOAD_DATA_ = [];</script>", OutcomeKind.VALIDATION),
        (400, "", OutcomeKind.VALIDATION),
        (404, "", OutcomeKind.FATAL),
        (503, "", OutcomeKind.SERVER),
    ],
)
async def test_classification(status: int, body: str, kind: OutcomeKind) -> None:
    outcome, _ = await _submit_with(status, body)
    assert outcome.kind == kind


async def test_payload_keeps_duplicate_keys_and_other_text() -> None:
    outcome, seen = await _submit_with(429, "", {"Retry-After": "120"})
    assert outcome.kind == OutcomeKind.BLOCKED and outcome.retry_after == 120.0
    pairs = parse_qsl(str(seen["body"]))
    assert ("entry.1007", "FB") in pairs and ("entry.1007", "TikTok") in pairs
    assert ("entry.1001.other_option_response", "Không tiết lộ") in pairs
    assert seen["content_type"] == "application/x-www-form-urlencoded"
    assert payload_to_json(build_payload_tuples(RESPONSE, "x"))["entry.1007"] == ["FB", "TikTok"]


def test_retry_after_http_date() -> None:
    assert parse_retry_after("Wed, 21 Oct 2015 07:28:00 GMT") == 0.0
    assert parse_retry_after("garbage") is None


def test_prefill_url() -> None:
    parts = urlsplit(build_prefill_url(FORM, RESPONSE))
    assert parts.path.endswith("/viewform")
    pairs = parse_qsl(parts.query)
    assert pairs[0] == ("usp", "pp_url") and ("entry.1007", "TikTok") in pairs


def test_poisson_delays_match_duration() -> None:
    delays = poisson_delays(500, 7200.0, np.random.default_rng(1))
    assert len(delays) == 500 and delays.sum() == pytest.approx(7200.0)
    assert remaining_duration_seconds(120, 500, 250) == pytest.approx(3600.0)


def test_rate_guard_slows_down_then_pauses() -> None:
    guard = RateGuard(base_cooldown_seconds=10)
    first = guard.on_blocked(None, now=0)
    second = guard.on_blocked(30, now=0)
    third = guard.on_blocked(None, now=0)
    assert not first.should_pause and not second.should_pause and third.should_pause
    assert second.wait_seconds == 30 and guard.delay_factor == 8
    guard.on_success()
    assert guard.consecutive_blocks == 0 and 1 < guard.delay_factor < 8
