"""Tải trình duyệt cho tính năng "trình duyệt dự phòng" (dev-notes RISK-012).

Dùng driver Node đi kèm gói Playwright (có trong bản đóng gói PyInstaller), nên chạy được cả khi
máy người dùng không có Python. Chỉ tải Chrome Headless Shell (app luôn chạy trình duyệt ẩn).
Lệnh chạy trong luồng riêng: vòng lặp sự kiện của uvicorn trên Windows không hỗ trợ subprocess async.
"""

from __future__ import annotations

import asyncio
import logging
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

INSTALL_ARGS = ("install", "--only-shell", "chromium")
DRY_RUN_ARGS = ("install", "--dry-run", "--only-shell", "chromium")
COMPLETE_MARKER = "INSTALLATION_COMPLETE"
PROGRESS_PATTERN = re.compile(r"(\d{1,3})%\s+of\s+([\d.]+\s*\w+)")
LOCATION_PATTERN = re.compile(r"Install location:\s+(.+)")
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


@dataclass
class BrowserStatus:
    installed: bool
    installing: bool
    percent: int | None = None
    detail: str | None = None
    error: str | None = None


def _driver_command(*args: str) -> tuple[list[str], dict[str, str]]:
    from playwright._impl._driver import compute_driver_executable, get_driver_env

    node, cli = compute_driver_executable()
    return [node, cli, *args], get_driver_env()


def _install_locations() -> list[Path]:
    command, env = _driver_command(*DRY_RUN_ARGS)
    result = subprocess.run(
        command, env=env, capture_output=True, text=True, encoding="utf-8", timeout=60, creationflags=NO_WINDOW,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "Không đọc được thông tin trình duyệt.")
    return [Path(match.strip()) for match in LOCATION_PATTERN.findall(result.stdout)]


def is_installed() -> bool:
    locations = _install_locations()
    return bool(locations) and all((location / COMPLETE_MARKER).exists() for location in locations)


class BrowserInstaller:
    def __init__(self) -> None:
        self._task: asyncio.Task[None] | None = None
        self._percent: int | None = None
        self._detail: str | None = None
        self._error: str | None = None

    @property
    def installing(self) -> bool:
        return self._task is not None and not self._task.done()

    async def status(self) -> BrowserStatus:
        if self.installing:
            return BrowserStatus(installed=False, installing=True, percent=self._percent, detail=self._detail)
        try:
            installed = await asyncio.to_thread(is_installed)
        except (OSError, RuntimeError, subprocess.SubprocessError) as exc:
            return BrowserStatus(installed=False, installing=False, error=f"Không kiểm tra được trình duyệt: {exc}")
        return BrowserStatus(installed=installed, installing=False, error=None if installed else self._error)

    def start(self) -> None:
        if self.installing:
            return
        self._percent, self._detail, self._error = 0, "Đang chuẩn bị tải…", None
        self._task = asyncio.create_task(asyncio.to_thread(self._run), name="browser-install")

    def _on_output(self, line: str) -> None:
        match = PROGRESS_PATTERN.search(line)
        if match:
            self._percent = int(match.group(1))
            self._detail = f"Đã tải {self._percent}% / {match.group(2)}"
        elif "downloaded to" in line.lower():
            self._detail = "Đang giải nén…"

    def _run(self) -> None:
        try:
            command, env = _driver_command(*INSTALL_ARGS)
            with subprocess.Popen(
                command, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, creationflags=NO_WINDOW,
            ) as process:
                assert process.stdout is not None
                buffer = ""
                while chunk := process.stdout.read(256):
                    buffer += chunk.decode("utf-8", errors="replace")
                    *lines, buffer = re.split(r"[\r\n]", buffer)  # thanh tiến độ dùng \r để vẽ lại cùng dòng
                    for line in lines:
                        if line.strip():
                            self._on_output(line)
                if process.wait() != 0:
                    self._error = "Tải trình duyệt thất bại. Kiểm tra kết nối mạng rồi thử lại."
                    logger.error("Cài Chromium thất bại (mã %s)", process.returncode)
                else:
                    self._percent, self._detail = 100, "Đã tải xong."
                    logger.info("Đã cài Chrome Headless Shell cho trình duyệt dự phòng")
        except (OSError, subprocess.SubprocessError) as exc:
            self._error = f"Không chạy được trình cài trình duyệt: {exc}"
            logger.exception("Không chạy được trình cài Chromium")


installer = BrowserInstaller()
