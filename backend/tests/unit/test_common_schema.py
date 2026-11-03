"""Kiểm tra kiểu UtcDateTime (app/schemas/common.py): mọi datetime trả ra phải có múi giờ UTC."""

from datetime import UTC, datetime, timedelta, timezone

from pydantic import BaseModel

from app.schemas.common import UtcDateTime


class _Dto(BaseModel):
    at: UtcDateTime
    maybe: UtcDateTime | None = None


def test_datetime_khong_mui_gio_duoc_gan_utc() -> None:
    """SQLite trả giờ UTC không kèm múi giờ → giữ nguyên giờ, chỉ gắn UTC (BUG-005)."""
    dto = _Dto(at=datetime(2026, 1, 2, 3, 4, 5))
    assert dto.at == datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC)
    assert dto.at.tzinfo is UTC


def test_datetime_mui_gio_khac_doi_sang_utc() -> None:
    vn = timezone(timedelta(hours=7))
    dto = _Dto(at=datetime(2026, 1, 2, 10, 0, tzinfo=vn))
    assert dto.at.utcoffset() == timedelta(0)
    assert dto.at.hour == 3


def test_chuoi_iso_va_json_co_mui_gio() -> None:
    dto = _Dto(at="2026-01-02T03:04:05")
    assert dto.at.tzinfo is not None
    assert dto.model_dump(mode="json")["at"].endswith("Z")


def test_gia_tri_none_duoc_phep_khi_optional() -> None:
    assert _Dto(at=datetime(2026, 1, 1), maybe=None).maybe is None
