"""WebSocket tiến độ real-time `/ws/campaigns/{id}` (Mục 6.4 spec).

Gửi ngay một sự kiện SNAPSHOT (trạng thái hiện tại), sau đó chuyển tiếp mọi sự kiện của
chiến dịch; cứ 25 giây không có gì thì gửi PING để giữ kết nối.
"""

from __future__ import annotations

import asyncio
import contextlib
import uuid

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect, status

from app.core.config import get_settings
from app.core.database import AsyncSessionLocal
from app.core.security import is_token_valid
from app.services import campaign_service
from app.workers.campaign_control import event_bus

router = APIRouter(tags=["websocket"])
PING_INTERVAL_SECONDS = 25.0


@router.websocket("/ws/campaigns/{campaign_id}")
async def campaign_updates(websocket: WebSocket, campaign_id: uuid.UUID, token: str | None = Query(default=None)) -> None:
    if not is_token_valid(get_settings(), token):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    async with AsyncSessionLocal() as session:
        try:
            campaign = await campaign_service.get_campaign(session, campaign_id)
        except campaign_service.NotFoundError:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return
        snapshot = campaign_service.to_read(campaign).model_dump(mode="json")

    await websocket.accept()
    queue = event_bus.subscribe(str(campaign_id))
    try:
        await websocket.send_json({"event": "SNAPSHOT", "campaign": snapshot})
        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=PING_INTERVAL_SECONDS)
            except TimeoutError:
                event = {"event": "PING"}
            await websocket.send_json(event)
    except (WebSocketDisconnect, RuntimeError):
        pass
    finally:
        event_bus.unsubscribe(str(campaign_id), queue)
        with contextlib.suppress(RuntimeError):
            await websocket.close()
