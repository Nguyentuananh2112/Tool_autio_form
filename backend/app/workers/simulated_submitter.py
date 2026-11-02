"""Bộ gửi mô phỏng cho Chế độ tập dùng: không mở kết nối mạng nào, luôn "thành công" sau một chút chờ."""

from __future__ import annotations

import asyncio
from collections.abc import Sequence

from app.models.submission_log import EngineUsed
from app.schemas.form_schema import ParsedFormStructure
from app.workers.submission_types import OutcomeKind, SubmitOutcome

SIMULATED_DELAY_SECONDS = 0.4


class SimulatedSubmitter:
    def __init__(self, delay: float = SIMULATED_DELAY_SECONDS) -> None:
        self.delay = delay

    async def submit(self, structure: ParsedFormStructure, payload: Sequence[tuple[str, str]]) -> SubmitOutcome:
        if self.delay > 0:
            await asyncio.sleep(self.delay)
        return SubmitOutcome(OutcomeKind.SUCCESS, 200, EngineUsed.SIMULATED, error=None)

    async def aclose(self) -> None:
        return None
