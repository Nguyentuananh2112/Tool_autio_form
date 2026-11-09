"""Điều phối một chiến dịch: lịch gửi, tạm dừng/tiếp tục, thử lại, trình duyệt dự phòng, ghi log.

Mô hình: hàng đợi các phản hồi chưa gửi + N worker (Tốc độ tối đa: N = concurrency;
Rải đều: 1 worker ngủ theo Poisson Jitter). Bị 429/403 → RateGuard giãn nhịp, quá
3 lần liên tiếp → tự tạm dừng và báo người dùng (SPEC-012).
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Protocol

import numpy as np
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import get_settings
from app.core.database import AsyncSessionLocal
from app.models import Campaign, CampaignStatus, SubmissionLog
from app.schemas.campaign_schema import ScheduleMode
from app.schemas.event_schema import RateLimitedEvent, StatusChangeEvent, SubmissionUpdateEvent
from app.schemas.form_schema import ParsedFormStructure
from app.services.spss_generator import GeneratedResponse, GeneratorConfigError, build_payload_tuples
from app.workers.campaign_control import CampaignControl, EventBus, event_bus, registry
from app.workers.campaign_loader import CampaignPlan, campaign_seed, load_plan
from app.workers.http_submitter import HttpSubmitter
from app.workers.playwright_fallback import FallbackUnavailableError, PlaywrightSubmitter
from app.workers.rate_guard import RateGuard
from app.workers.simulated_submitter import SimulatedSubmitter
from app.workers.scheduler import poisson_delays, remaining_duration_seconds
from app.workers.submission_types import RETRYABLE_KINDS, OutcomeKind, SubmitOutcome, payload_to_json

logger = logging.getLogger(__name__)

NETWORK_RETRIES = 2
AUTO_PAUSE_REASON = "Google đang giới hạn số lần gửi. Chiến dịch đã tự tạm dừng; hãy chờ một lúc rồi bấm Tiếp tục."
NOTHING_SENT_REASON = "Không gửi được phản hồi nào: Google từ chối cả {count} lần. Xem lý do trong Nhật ký gửi."
# Form từ chối liên tiếp → gần như chắc chắn lỗi cấu hình / form đổi, không phải ngẫu nhiên: dừng sớm thay vì đốt hết lượt
MAX_CONSECUTIVE_FAILURES = 5
FAILURE_PAUSE_REASON = (
    "Google từ chối {count} phản hồi liên tiếp nên chiến dịch đã tự tạm dừng. Xem lỗi trong Nhật ký gửi, "
    "kiểm tra lại form (có câu mới / câu đổi kiểu?) rồi phân tích lại form trước khi bấm Tiếp tục."
)
USER_STOP_REASON = "Người dùng đã dừng chiến dịch."
USER_PAUSE_REASON = "Bạn đã tạm dừng chiến dịch."


class CampaignAlreadyRunningError(RuntimeError):
    pass


class FormSubmitter(Protocol):
    async def submit(self, structure: ParsedFormStructure, payload: list[tuple[str, str]]) -> SubmitOutcome: ...
    async def aclose(self) -> None: ...


class BrowserSubmitter(Protocol):
    async def submit(self, structure: ParsedFormStructure, response: GeneratedResponse) -> SubmitOutcome: ...
    async def close(self) -> None: ...


@dataclass(slots=True)
class _WorkItem:
    response: GeneratedResponse
    delay: float


def default_http_factory(proxy: str | None) -> FormSubmitter:
    return HttpSubmitter(user_agent=get_settings().HTTP_USER_AGENT, proxy=proxy)


def default_browser_factory(proxy: str | None) -> BrowserSubmitter:
    return PlaywrightSubmitter(proxy=proxy)


class CampaignRunner:
    def __init__(
        self,
        campaign_id: uuid.UUID,
        *,
        control: CampaignControl,
        bus: EventBus = event_bus,
        session_factory: async_sessionmaker[AsyncSession] = AsyncSessionLocal,
        http_factory: Callable[[str | None], FormSubmitter] = default_http_factory,
        browser_factory: Callable[[str | None], BrowserSubmitter] = default_browser_factory,
        rate_guard: RateGuard | None = None,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.campaign_id = campaign_id
        self.control = control
        self.bus = bus
        self.session_factory = session_factory
        self.http_factory = http_factory
        self.browser_factory = browser_factory
        self.guard = rate_guard or RateGuard()
        self.clock = clock

        self._queue: deque[_WorkItem] = deque()
        self._db_lock = asyncio.Lock()
        self._status_lock = asyncio.Lock()
        self._pause_recorded = False
        self._fatal_error: str | None = None
        self._http: FormSubmitter | None = None
        self._browser: BrowserSubmitter | None = None
        self._browser_unavailable: str | None = None
        self.plan: CampaignPlan | None = None
        self.completed = 0
        self.failed = 0
        self._consecutive_failures = 0

    # ------------------------------------------------------------------ public
    async def run(self) -> CampaignStatus:
        try:
            async with self.session_factory() as session:
                self.plan = await load_plan(session, self.campaign_id)
            plan = self.plan
            self.completed, self.failed = plan.completed_count, plan.failed_count
            self._fill_queue(plan)
            await self._set_status(CampaignStatus.RUNNING)

            # Chế độ tập dùng: không bao giờ gửi ra ngoài, bất kể http_factory nào được truyền vào
            self._http = SimulatedSubmitter() if plan.is_demo else self.http_factory(plan.proxy)
            workers = plan.schedule.concurrency if plan.schedule.mode == ScheduleMode.BURST else 1
            await asyncio.gather(*(self._worker() for _ in range(max(1, workers))))
            return await self._finish()
        except GeneratorConfigError as exc:
            await self._set_status(CampaignStatus.FAILED, reason=f"Cấu hình chưa hợp lệ: {exc}")
            return CampaignStatus.FAILED
        except Exception as exc:
            logger.exception("Chiến dịch %s lỗi không mong đợi", self.campaign_id)
            await self._set_status(CampaignStatus.FAILED, reason=f"Lỗi hệ thống: {exc}")
            return CampaignStatus.FAILED
        finally:
            await self._close_engines()

    # ------------------------------------------------------------------ setup
    def _fill_queue(self, plan: CampaignPlan) -> None:
        pending = plan.pending
        if plan.schedule.mode == ScheduleMode.SCHEDULED and plan.schedule.duration_minutes:
            seconds = remaining_duration_seconds(plan.schedule.duration_minutes, plan.total_target, len(pending))
            rng = np.random.default_rng(campaign_seed(plan.campaign_id) + len(plan.done_sequences))
            delays = poisson_delays(len(pending), seconds, rng)
        else:
            delays = np.zeros(len(pending))
        self._queue.extend(_WorkItem(response, float(delay)) for response, delay in zip(pending, delays))

    async def _finish(self) -> CampaignStatus:
        if self._fatal_error:
            await self._set_status(CampaignStatus.FAILED, reason=self._fatal_error)
            return CampaignStatus.FAILED
        if self.control.is_cancelled:
            await self._set_status(CampaignStatus.PAUSED, reason=USER_STOP_REASON)
            return CampaignStatus.PAUSED
        if self.completed == 0 and self.failed > 0:
            # Gửi hết lượt mà không phản hồi nào được nhận → KHÔNG phải "Hoàn thành" (BUG-019)
            await self._set_status(CampaignStatus.FAILED, reason=NOTHING_SENT_REASON.format(count=self.failed))
            return CampaignStatus.FAILED
        await self._set_status(CampaignStatus.COMPLETED)
        return CampaignStatus.COMPLETED

    async def _close_engines(self) -> None:
        if self._http is not None:
            await self._http.aclose()
        if self._browser is not None:
            await self._browser.close()

    # ------------------------------------------------------------------ worker
    async def _worker(self) -> None:
        while True:
            if not await self._checkpoint() or not self._queue:
                return
            item = self._queue.popleft()
            if not await self.control.sleep(item.delay * self.guard.delay_factor):
                self._queue.appendleft(item)
                return
            if not await self._checkpoint() or not await self.control.sleep(self.guard.remaining_cooldown(self.clock())):
                self._queue.appendleft(item)
                return

            outcome = await self._submit(item.response)
            if outcome.kind == OutcomeKind.BLOCKED:
                self._handle_blocked(item, outcome)
                continue
            if outcome.kind == OutcomeKind.FATAL:
                self._fatal_error = outcome.error
                await self._record(item.response, outcome)
                self.control.cancel()
                return
            if outcome.ok:
                self.guard.on_success()
            await self._record(item.response, outcome)
            self._track_failures(outcome)

    def _track_failures(self, outcome: SubmitOutcome) -> None:
        if outcome.ok:
            self._consecutive_failures = 0
            return
        self._consecutive_failures += 1
        if self._consecutive_failures >= MAX_CONSECUTIVE_FAILURES and not self.control.is_paused:
            self.control.pause(FAILURE_PAUSE_REASON.format(count=self._consecutive_failures))

    def _handle_blocked(self, item: _WorkItem, outcome: SubmitOutcome) -> None:
        decision = self.guard.on_blocked(outcome.retry_after, self.clock())
        item.delay = 0.0  # khoảng chờ đã nằm trong cooldown của RateGuard
        self._queue.appendleft(item)
        self.bus.publish(str(self.campaign_id), RateLimitedEvent(
            campaign_id=str(self.campaign_id), sequence_number=item.response.sequence_number,
            status_code=outcome.status_code, wait_seconds=round(decision.wait_seconds, 1),
            consecutive_blocks=decision.consecutive_blocks, will_pause=decision.should_pause,
        ).model_dump(mode="json"))
        if decision.should_pause and not self.control.is_paused:
            self.control.pause(AUTO_PAUSE_REASON)

    async def _checkpoint(self) -> bool:
        """Nếu đang tạm dừng: ghi trạng thái PAUSED một lần, chờ Tiếp tục, rồi ghi RUNNING."""
        if self.control.is_cancelled:
            return False
        if not self.control.is_paused:
            return True
        async with self._status_lock:
            if not self._pause_recorded and self.control.is_paused:
                self._pause_recorded = True
                await self._set_status(CampaignStatus.PAUSED, reason=self.control.pause_reason)
        if not await self.control.wait_until_resumed():
            return False
        async with self._status_lock:
            if self._pause_recorded:
                self._pause_recorded = False
                self.guard.reset_after_resume()
                self._consecutive_failures = 0
                await self._set_status(CampaignStatus.RUNNING)
        return True

    # ------------------------------------------------------------------ submit
    async def _submit(self, response: GeneratedResponse) -> SubmitOutcome:
        assert self.plan is not None and self._http is not None
        payload = build_payload_tuples(response, self.plan.structure.fbzx)
        outcome = await self._http.submit(self.plan.structure, payload)
        for attempt in range(NETWORK_RETRIES):
            if outcome.kind not in RETRYABLE_KINDS:
                break
            if not await self.control.sleep(2.0 * (attempt + 1)):
                return outcome
            outcome = await self._http.submit(self.plan.structure, payload)
        if outcome.kind == OutcomeKind.VALIDATION and self.plan.use_fallback:
            return await self._submit_with_browser(response, outcome)
        return outcome

    async def _submit_with_browser(self, response: GeneratedResponse, http_outcome: SubmitOutcome) -> SubmitOutcome:
        assert self.plan is not None
        if self._browser_unavailable:
            http_outcome.error = f"{http_outcome.error} Trình duyệt dự phòng: {self._browser_unavailable}"
            return http_outcome
        if self._browser is None:
            self._browser = self.browser_factory(self.plan.proxy)
        try:
            return await self._browser.submit(self.plan.structure, response)
        except FallbackUnavailableError as exc:
            self._browser_unavailable = str(exc)
            http_outcome.error = f"{http_outcome.error} Trình duyệt dự phòng: {exc}"
            return http_outcome

    # ----------------------------------------------------------- persistence
    async def _record(self, response: GeneratedResponse, outcome: SubmitOutcome) -> None:
        assert self.plan is not None
        payload = payload_to_json(build_payload_tuples(response, self.plan.structure.fbzx))
        async with self._db_lock:
            if outcome.ok:
                self.completed += 1
            else:
                self.failed += 1
            async with self.session_factory() as session:
                session.add(SubmissionLog(
                    campaign_id=self.campaign_id, sequence_number=response.sequence_number,
                    engine_used=outcome.engine.value, status_code=outcome.status_code,
                    is_success=outcome.ok, payload_sent=payload, error_detail=outcome.error,
                ))
                await session.execute(
                    update(Campaign).where(Campaign.id == self.campaign_id)
                    .values(completed_count=self.completed, failed_count=self.failed)
                )
                await session.commit()
        next_delay = self._queue[0].delay * self.guard.delay_factor if self._queue else None
        self.bus.publish(str(self.campaign_id), SubmissionUpdateEvent(
            campaign_id=str(self.campaign_id), sequence_number=response.sequence_number,
            completed_count=self.completed, failed_count=self.failed,
            engine_used=outcome.engine.value, status_code=outcome.status_code, is_success=outcome.ok,
            page_history=response.page_history_str, error_detail=outcome.error,
            next_delay_seconds=round(next_delay, 1) if next_delay is not None else None,
        ).model_dump(mode="json"))

    async def _set_status(self, status: CampaignStatus, *, reason: str | None = None) -> None:
        async with self.session_factory() as session:
            await session.execute(
                update(Campaign).where(Campaign.id == self.campaign_id).values(status=status.value, status_reason=reason)
            )
            await session.commit()
        self.bus.publish(str(self.campaign_id), StatusChangeEvent(
            campaign_id=str(self.campaign_id), status=status.value, reason=reason,
        ).model_dump(mode="json"))


def start_campaign(campaign_id: uuid.UUID, **runner_kwargs: Any) -> CampaignControl:
    """Tạo task nền cho chiến dịch (gọi từ endpoint start/resume ở Phase 3)."""
    control = registry.get_or_create(str(campaign_id))
    if control.is_active:
        raise CampaignAlreadyRunningError("Chiến dịch đang chạy.")
    control.reset()
    runner = CampaignRunner(campaign_id, control=control, **runner_kwargs)
    control.task = asyncio.create_task(runner.run(), name=f"campaign-{campaign_id}")
    return control
