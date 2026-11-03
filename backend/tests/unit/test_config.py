"""Kiểm tra Settings (app/core/config.py): luôn dựng Settings(...) với giá trị tường minh."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from app.core.config import APP_DIR_NAME, Settings, default_data_dir


def _make(**kwargs) -> Settings:
    kwargs.setdefault("DATABASE_URL", "sqlite+aiosqlite:///x.db")
    return Settings(_env_file=None, **kwargs)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("sqlite:///C:/data/a.db", "sqlite+aiosqlite:///C:/data/a.db"),
        ("  sqlite:///a.db  ", "sqlite+aiosqlite:///a.db"),
        ("sqlite+aiosqlite:///b.db", "sqlite+aiosqlite:///b.db"),
        ("sqlite:///:memory:", "sqlite+aiosqlite:///:memory:"),
    ],
)
def test_chuan_hoa_database_url(raw: str, expected: str) -> None:
    assert _make(DATABASE_URL=raw).DATABASE_URL == expected


def test_database_url_trong_dung_data_dir(tmp_path: Path) -> None:
    s = _make(DATABASE_URL="", DATA_DIR=tmp_path)
    assert s.DATABASE_URL == f"sqlite+aiosqlite:///{(tmp_path / 'auto_form.db').as_posix()}"
    assert not s.is_in_memory_db


def test_nhan_biet_db_trong_bo_nho() -> None:
    assert _make(DATABASE_URL="sqlite:///:memory:").is_in_memory_db


@pytest.mark.parametrize(
    "url",
    ["postgresql+asyncpg://u:p@localhost/db", "postgres://localhost/db", "mysql://x", "sqlite+pysqlite:///a.db"],
)
def test_tu_choi_db_khong_phai_sqlite_async(url: str) -> None:
    with pytest.raises(ValidationError, match="SQLite"):
        _make(DATABASE_URL=url)


@pytest.mark.parametrize("host", ["127.0.0.1", "localhost", "::1"])
def test_host_loopback_hop_le(host: str) -> None:
    assert _make(HOST=host).HOST == host


@pytest.mark.parametrize("host", ["0.0.0.0", "192.168.1.5", "example.com", ""])
def test_host_khong_phai_loopback_bi_chan(host: str) -> None:
    with pytest.raises(ValidationError, match="loopback"):
        _make(HOST=host)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [("/api/v1", "/api/v1"), ("api/v1", "/api/v1"), ("/api/v1/", "/api/v1"), (" /api ", "/api"), ("/", ""), ("", "")],
)
def test_chuan_hoa_api_prefix(raw: str, expected: str) -> None:
    assert _make(API_V1_PREFIX=raw).API_V1_PREFIX == expected


def test_port_ngoai_khoang_bi_chan() -> None:
    with pytest.raises(ValidationError):
        _make(PORT=80)
    with pytest.raises(ValidationError):
        _make(PORT=70000)


def test_cors_origins_list_bo_khoang_trang_va_rong() -> None:
    s = _make(CORS_ORIGINS=" http://a , ,http://b,")
    assert s.cors_origins_list == ["http://a", "http://b"]


def test_is_production() -> None:
    assert _make(ENVIRONMENT="production").is_production
    assert not _make(ENVIRONMENT="development").is_production
    with pytest.raises(ValidationError):
        _make(ENVIRONMENT="staging")


def test_default_data_dir_theo_appdata(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("APPDATA", str(tmp_path))
    assert default_data_dir() == tmp_path / APP_DIR_NAME
    monkeypatch.delenv("APPDATA")
    assert default_data_dir() == Path.home() / ".local" / "share" / APP_DIR_NAME
