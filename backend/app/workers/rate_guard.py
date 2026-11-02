"""Tôn trọng giới hạn của Google: khi bị 429/403 thì giãn nhịp gửi, bị liên tiếp thì tạm dừng.

Đây là thay thế có chủ đích cho "xoay proxy / đổi User-Agent" của spec (dev-notes SPEC-012):
app KHÔNG cố lách cơ chế chặn mà chậm lại và báo cho người dùng.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class BlockDecision:
    wait_seconds: float
    should_pause: bool
    consecutive_blocks: int


@dataclass
class RateGuard:
    max_consecutive_blocks: int = 3
    base_cooldown_seconds: float = 60.0
    max_cooldown_seconds: float = 900.0
    max_delay_factor: float = 16.0
    consecutive_blocks: int = 0
    delay_factor: float = 1.0
    cooldown_until: float = 0.0

    def on_success(self) -> None:
        self.consecutive_blocks = 0
        # Hồi phục dần, không quay ngay về tốc độ cũ
        self.delay_factor = max(1.0, self.delay_factor * 0.8)

    def on_blocked(self, retry_after: float | None, now: float) -> BlockDecision:
        self.consecutive_blocks += 1
        self.delay_factor = min(self.delay_factor * 2.0, self.max_delay_factor)
        wait = max(retry_after or 0.0, self.base_cooldown_seconds * self.delay_factor / 2.0)
        wait = min(wait, self.max_cooldown_seconds)
        self.cooldown_until = max(self.cooldown_until, now + wait)
        return BlockDecision(
            wait_seconds=wait,
            should_pause=self.consecutive_blocks >= self.max_consecutive_blocks,
            consecutive_blocks=self.consecutive_blocks,
        )

    def remaining_cooldown(self, now: float) -> float:
        return max(0.0, self.cooldown_until - now)

    def reset_after_resume(self) -> None:
        """Người dùng bấm Tiếp tục sau khi bị tạm dừng: bắt đầu lại đếm nhưng giữ nhịp chậm."""
        self.consecutive_blocks = 0
        self.cooldown_until = 0.0
