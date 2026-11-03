"""Kiểm tra token bảo vệ API local (app/core/security.py)."""

import pytest

from app.core.config import Settings
from app.core.security import TOKEN_HEADER, generate_app_token, is_token_valid


def _settings(env: str, token: str | None) -> Settings:
    return Settings(_env_file=None, ENVIRONMENT=env, APP_TOKEN=token, DATABASE_URL="sqlite:///x.db")


def test_dev_khong_token_thi_cho_qua() -> None:
    assert is_token_valid(_settings("development", None), None) is True
    assert is_token_valid(_settings("development", ""), "bất kỳ") is True


def test_production_khong_token_thi_chan_het() -> None:
    """Fail closed: bản phát hành thiếu APP_TOKEN thì từ chối mọi request."""
    assert is_token_valid(_settings("production", None), None) is False
    assert is_token_valid(_settings("production", None), "abc") is False


@pytest.mark.parametrize("env", ["development", "production"])
@pytest.mark.parametrize(
    ("provided", "expected"),
    [("dung-roi", True), ("sai", False), ("", False), (None, False), ("dung-roi ", False), ("DUNG-ROI", False)],
)
def test_so_khop_token(env: str, provided: str | None, expected: bool) -> None:
    assert is_token_valid(_settings(env, "dung-roi"), provided) is expected


def test_token_unicode_van_so_khop_duoc() -> None:
    assert is_token_valid(_settings("production", "mã-bí-mật"), "mã-bí-mật") is True
    assert is_token_valid(_settings("production", "mã-bí-mật"), "ma-bi-mat") is False


def test_sinh_token_ngau_nhien_du_dai() -> None:
    a, b = generate_app_token(), generate_app_token()
    assert a != b and len(a) >= 40
    assert TOKEN_HEADER == "X-App-Token"
