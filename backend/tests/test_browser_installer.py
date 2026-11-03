"""Tải trình duyệt dự phòng: đọc trạng thái từ driver Playwright thật, tiến độ từ dòng xuất của trình cài."""

import httpx
import pytest

from app.core.database import init_db
from app.main import create_app
from app.services import browser_installer
from app.services.browser_installer import BrowserInstaller
from tests.db_helpers import reset_database


def test_progress_lines_are_parsed() -> None:
    installer = BrowserInstaller()
    installer._on_output("|■■■■■■■■                    |  27% of 112.6 MiB")
    assert installer._percent == 27 and installer._detail == "Đã tải 27% / 112.6 MiB"


def test_dry_run_reports_install_locations() -> None:
    locations = browser_installer._install_locations()
    assert locations and all("ms-playwright" in str(path) for path in locations)


async def test_status_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(browser_installer, "is_installed", lambda: False)
    await init_db()
    app = create_app()
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        body = (await client.get("/api/v1/system/browser")).json()
    await reset_database()
    assert body == {"installed": False, "installing": False, "percent": None, "detail": None, "error": None}
