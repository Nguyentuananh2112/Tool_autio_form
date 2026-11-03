"""Kiểm thử kiểu kết quả gửi và payload_to_json (app/workers/submission_types.py)."""

import pytest

from app.models.submission_log import EngineUsed
from app.workers.submission_types import RETRYABLE_KINDS, OutcomeKind, SubmitOutcome, payload_to_json


def test_payload_rong() -> None:
    assert payload_to_json([]) == {}


def test_entry_luon_la_list_truong_an_la_chuoi() -> None:
    payload = [
        ("entry.1", "Nam"),
        ("entry.2", "A"),
        ("entry.2", "B"),
        ("fvv", "1"),
        ("pageHistory", "0,1"),
        ("fbzx", "-123"),
    ]
    assert payload_to_json(payload) == {
        "entry.1": ["Nam"],
        "entry.2": ["A", "B"],
        "fvv": "1",
        "pageHistory": "0,1",
        "fbzx": "-123",
    }


def test_giu_thu_tu_khoa_va_gia_tri() -> None:
    payload = [("entry.9", "x"), ("entry.1", "c"), ("entry.9", "y"), ("entry.1", "a")]
    result = payload_to_json(payload)
    assert list(result) == ["entry.9", "entry.1"]
    assert result["entry.1"] == ["c", "a"]
    assert result["entry.9"] == ["x", "y"]


def test_truong_an_bi_lap_lay_gia_tri_dau() -> None:
    assert payload_to_json([("fvv", "1"), ("fvv", "2")]) == {"fvv": "1"}


def test_gia_tri_rong_van_duoc_giu() -> None:
    assert payload_to_json([("entry.5", "")]) == {"entry.5": [""]}


def test_khoa_ngay_gio_tach_rieng_la_list() -> None:
    payload = [("entry.7_year", "2024"), ("entry.7_month", "3"), ("entry.7.other_option_response", "Khác")]
    assert payload_to_json(payload) == {
        "entry.7_year": ["2024"],
        "entry.7_month": ["3"],
        "entry.7.other_option_response": ["Khác"],
    }


@pytest.mark.parametrize(
    ("kind", "ok"),
    [(OutcomeKind.SUCCESS, True)] + [(k, False) for k in OutcomeKind if k != OutcomeKind.SUCCESS],
)
def test_thuoc_tinh_ok(kind: OutcomeKind, ok: bool) -> None:
    assert SubmitOutcome(kind, 200, EngineUsed.HTTPX).ok is ok


def test_chi_loi_mang_va_may_chu_duoc_thu_lai() -> None:
    assert RETRYABLE_KINDS == {OutcomeKind.NETWORK, OutcomeKind.SERVER}


def test_gia_tri_mac_dinh_cua_outcome() -> None:
    outcome = SubmitOutcome(OutcomeKind.UNKNOWN, 302, EngineUsed.HTTPX)
    assert outcome.error is None and outcome.retry_after is None
