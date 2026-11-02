"""Trạng thái chạy trong bộ nhớ (thay Redis của spec — app desktop một tiến trình, SPEC-008).

- `CampaignControl`: cờ Tạm dừng / Dừng hẳn cho một chiến dịch đang chạy.
- `EventBus`: phát sự kiện tới các WebSocket đang theo dõi.
- `CampaignRegistry`: chiến dịch nào đang có task chạy.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

EVENT_QUEUE_SIZE = 1000


@dataclass
class CampaignControl:
    campaign_id: str
    pause_reason: str | None = None
    task: asyncio.Task[Any] | None = None
    _resumed: asyncio.Event = field(default_factory=asyncio.Event)
    _cancelled: asyncio.Event = field(default_factory=asyncio.Event)

    def __post_init__(self) -> None:
        self._resumed.set()

    @property
    def is_paused(self) -> bool:
        return not self._resumed.is_set()

    @property
    def is_cancelled(self) -> bool:
        return self._cancelled.is_set()

    @property
    def is_active(self) -> bool:
        return self.task is not None and not self.task.done()

    def pause(self, reason: str | None = None) -> None:
        self.pause_reason = reason
        self._resumed.clear()

    def resume(self) -> None:
        self.pause_reason = None
        self._resumed.set()

    def cancel(self) -> None:
        self._cancelled.set()
        self._resumed.set()  # đánh thức worker đang chờ để chúng thoát

    def reset(self) -> None:
        self.pause_reason = None
        self._cancelled = asyncio.Event()
        self._resumed = asyncio.Event()
        self._resumed.set()

    async def wait_until_resumed(self) -> bool:
        """Chờ tới khi được tiếp tục. Trả về False nếu bị dừng hẳn."""
        await self._resumed.wait()
        return not self.is_cancelled

    async def sleep(self, seconds: float) -> bool:
        """Ngủ nhưng thức dậy ngay nếu bị dừng hẳn. Trả về False nếu bị dừng."""
        if seconds <= 0:
            return not self.is_cancelled
        with contextlib.suppress(TimeoutError):
            await asyncio.wait_for(self._cancelled.wait(), timeout=seconds)
        return not self.is_cancelled


class EventBus:
    def __init__(self) -> None:
        self._subscribers: dict[str, set[asyncio.Queue[dict[str, Any]]]] = {}

    def subscribe(self, campaign_id: str) -> asyncio.Queue[dict[str, Any]]:
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=EVENT_QUEUE_SIZE)
        self._subscribers.setdefault(campaign_id, set()).add(queue)
        return queue

    def unsubscribe(self, campaign_id: str, queue: asyncio.Queue[dict[str, Any]]) -> None:
        queues = self._subscribers.get(campaign_id)
        if queues is not None:
            queues.discard(queue)
            if not queues:
                del self._subscribers[campaign_id]

    def publish(self, campaign_id: str, event: dict[str, Any]) -> None:
        for queue in list(self._subscribers.get(campaign_id, ())):
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                logger.warning("Bỏ sự kiện cho một client theo dõi chậm (campaign %s)", campaign_id)


class CampaignRegistry:
    def __init__(self) -> None:
        self._controls: dict[str, CampaignControl] = {}

    def get(self, campaign_id: str) -> CampaignControl | None:
        return self._controls.get(campaign_id)

    def get_or_create(self, campaign_id: str) -> CampaignControl:
        control = self._controls.get(campaign_id)
        if control is None:
            control = CampaignControl(campaign_id=campaign_id)
            self._controls[campaign_id] = control
        return control

    def discard(self, campaign_id: str) -> None:
        self._controls.pop(campaign_id, None)

    def active_ids(self) -> list[str]:
        return [cid for cid, control in self._controls.items() if control.is_active]


registry = CampaignRegistry()
event_bus = EventBus()
