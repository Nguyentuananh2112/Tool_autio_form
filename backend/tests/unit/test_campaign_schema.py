"""Kiểm tra validator của cấu hình chiến dịch (app/schemas/campaign_schema.py)."""

from datetime import date, time

import pytest
from pydantic import ValidationError

from app.schemas.campaign_schema import (
    QuestionRuleConfig,
    RuleStrategy,
    ScheduleConfig,
    ScheduleMode,
    SpssGroupConfig,
)


def _rule(**kwargs) -> QuestionRuleConfig:
    kwargs.setdefault("entry_id", "123")
    kwargs.setdefault("question_type", 2)
    return QuestionRuleConfig(**kwargs)


def _group(**kwargs) -> SpssGroupConfig:
    base = {"group_id": "g", "name": "Nhóm", "mean": 3.5, "std": 0.8, "alpha_target": 0.8, "entries": ["1", "2"]}
    base.update(kwargs)
    return SpssGroupConfig(**base)


# ---------------------------------------------------------------- QuestionRuleConfig
@pytest.mark.parametrize(("raw", "expected"), [("123", "123"), ("entry.456", "456"), ("  789 ", "789"), (" entry.10", "10")])
def test_entry_id_bo_tien_to_entry(raw: str, expected: str) -> None:
    assert _rule(entry_id=raw).entry_id == expected


@pytest.mark.parametrize("raw", ["abc", "entry.", "12a", "entry.12.3", "-5", "entry 12"])
def test_entry_id_phai_la_so(raw: str) -> None:
    with pytest.raises(ValidationError, match="entry_id"):
        _rule(entry_id=raw)


def test_entry_id_rong_bi_chan() -> None:
    with pytest.raises(ValidationError):
        _rule(entry_id="")


def test_trong_so_am_bi_chan() -> None:
    with pytest.raises(ValidationError, match="không được âm"):
        _rule(weights={"Nam": 50, "Nữ": -1})


def test_trong_so_bang_khong_hop_le() -> None:
    assert _rule(weights={"Nam": 0, "Nữ": 100}).weights == {"Nam": 0, "Nữ": 100}


def test_pool_bo_khoang_trang_va_dong_rong() -> None:
    rule = _rule(text_pool=[" Tốt ", "", "   ", "Ổn"], other_text_pool=["  ", "Khác "])
    assert rule.text_pool == ["Tốt", "Ổn"]
    assert rule.other_text_pool == ["Khác"]


def test_max_nho_hon_min_bi_chan() -> None:
    with pytest.raises(ValidationError, match="max_checked"):
        _rule(question_type=4, min_checked=3, max_checked=2)


def test_max_bang_min_hop_le() -> None:
    rule = _rule(question_type=4, min_checked=2, max_checked=2)
    assert (rule.min_checked, rule.max_checked) == (2, 2)


@pytest.mark.parametrize(("field", "value"), [("min_checked", -1), ("max_checked", 0), ("answer_rate", 100.5), ("answer_rate", -1)])
def test_gioi_han_truong_so(field: str, value: float) -> None:
    with pytest.raises(ValidationError):
        _rule(**{field: value})


def test_khoang_ngay_dao_nguoc_bi_chan() -> None:
    with pytest.raises(ValidationError, match="date_start"):
        _rule(question_type=9, date_start=date(2026, 5, 2), date_end=date(2026, 5, 1))
    assert _rule(question_type=9, date_start=date(2026, 5, 1), date_end=date(2026, 5, 1)).date_end == date(2026, 5, 1)


def test_khoang_gio_dao_nguoc_bi_chan() -> None:
    with pytest.raises(ValidationError, match="time_start"):
        _rule(question_type=10, time_start=time(10, 0), time_end=time(9, 59))
    assert _rule(question_type=10, time_start=time(8), time_end=time(17)).time_start == time(8)


def test_chi_mot_dau_khoang_thi_khong_kiem_tra() -> None:
    assert _rule(question_type=9, date_start=date(2030, 1, 1)).date_end is None


@pytest.mark.parametrize("value", [None, "", []])
def test_fixed_can_fixed_value(value) -> None:
    with pytest.raises(ValidationError, match="FIXED"):
        _rule(strategy=RuleStrategy.FIXED, fixed_value=value)


@pytest.mark.parametrize("value", ["Nam", ["FB", "TikTok"]])
def test_fixed_co_gia_tri_hop_le(value) -> None:
    assert _rule(strategy="FIXED", fixed_value=value).fixed_value == value


def test_mac_dinh_hop_ly() -> None:
    rule = _rule()
    assert rule.strategy == RuleStrategy.AUTO
    assert rule.answer_rate == 100.0 and rule.min_checked == 0 and rule.max_checked is None


# ---------------------------------------------------------------- SpssGroupConfig
def test_nhom_can_r_hoac_alpha() -> None:
    with pytest.raises(ValidationError, match="r hoặc alpha_target"):
        _group(alpha_target=None)
    assert _group(alpha_target=None, r=0.4).r == 0.4
    assert _group().alpha_target == 0.8


def test_nhom_chuan_hoa_entry() -> None:
    group = _group(entries=["entry.1", " 2 "], reversed_entries=["entry.2"])
    assert group.entries == ["1", "2"] and group.reversed_entries == ["2"]


def test_nhom_trung_entry_bi_chan() -> None:
    with pytest.raises(ValidationError, match="nhiều lần"):
        _group(entries=["1", "entry.1"])


def test_reversed_phai_la_tap_con() -> None:
    with pytest.raises(ValidationError, match="tập con"):
        _group(reversed_entries=["3"])


@pytest.mark.parametrize(
    "kwargs",
    [{"entries": ["1"]}, {"std": 0.05}, {"std": 3.5}, {"r": 0.96}, {"alpha_target": 1.0}, {"mean": -1}, {"group_id": ""}],
)
def test_nhom_gioi_han_truong(kwargs: dict) -> None:
    with pytest.raises(ValidationError):
        _group(**kwargs)


# ---------------------------------------------------------------- ScheduleConfig
def test_lich_scheduled_can_thoi_luong() -> None:
    with pytest.raises(ValidationError, match="duration_minutes"):
        ScheduleConfig(mode=ScheduleMode.SCHEDULED)
    assert ScheduleConfig(mode="SCHEDULED", duration_minutes=30).duration_minutes == 30


def test_lich_burst_mac_dinh() -> None:
    cfg = ScheduleConfig()
    assert cfg.mode == ScheduleMode.BURST and cfg.duration_minutes is None and cfg.concurrency == 10


@pytest.mark.parametrize("kwargs", [{"duration_minutes": 0}, {"duration_minutes": 60 * 24 * 31}, {"concurrency": 0}, {"concurrency": 201}])
def test_lich_gioi_han_truong(kwargs: dict) -> None:
    with pytest.raises(ValidationError):
        ScheduleConfig(**kwargs)
