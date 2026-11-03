"""Kiểm thử RateGuard: giãn nhịp khi bị Google giới hạn (app/workers/rate_guard.py)."""

import pytest

from app.workers.rate_guard import RateGuard


def test_lan_chan_dau_tien_cho_bang_cooldown_co_ban() -> None:
    guard = RateGuard()
    decision = guard.on_blocked(None, now=1000.0)
    assert guard.delay_factor == 2.0
    assert decision.wait_seconds == pytest.approx(60.0)  # 60 * 2 / 2
    assert decision.consecutive_blocks == 1
    assert not decision.should_pause
    assert guard.cooldown_until == pytest.approx(1060.0)


def test_retry_after_lon_hon_duoc_uu_tien() -> None:
    guard = RateGuard()
    assert guard.on_blocked(300.0, now=0.0).wait_seconds == pytest.approx(300.0)


def test_retry_after_nho_hon_khong_lam_giam_thoi_gian_cho() -> None:
    guard = RateGuard()
    assert guard.on_blocked(5.0, now=0.0).wait_seconds == pytest.approx(60.0)


def test_retry_after_bang_0_coi_nhu_khong_co() -> None:
    guard = RateGuard()
    assert guard.on_blocked(0.0, now=0.0).wait_seconds == pytest.approx(60.0)


def test_retry_after_qua_lon_bi_chan_boi_max_cooldown() -> None:
    guard = RateGuard(max_cooldown_seconds=900.0)
    assert guard.on_blocked(10_000.0, now=0.0).wait_seconds == pytest.approx(900.0)


def test_he_so_tre_tang_gap_doi_va_bi_chan_tren() -> None:
    guard = RateGuard(max_consecutive_blocks=100, max_delay_factor=16.0)
    waits = [guard.on_blocked(None, now=0.0).wait_seconds for _ in range(6)]
    assert waits == pytest.approx([60.0, 120.0, 240.0, 480.0, 480.0, 480.0])
    assert guard.delay_factor == 16.0


def test_cooldown_tinh_toan_bi_chan_boi_max_cooldown() -> None:
    guard = RateGuard(max_consecutive_blocks=100, max_delay_factor=64.0, max_cooldown_seconds=900.0)
    waits = [guard.on_blocked(None, now=0.0).wait_seconds for _ in range(7)]
    assert max(waits) == pytest.approx(900.0)
    assert waits[-1] == pytest.approx(900.0)


def test_tam_dung_khi_bi_chan_lien_tiep_du_so_lan() -> None:
    guard = RateGuard(max_consecutive_blocks=3)
    flags = [guard.on_blocked(None, now=0.0).should_pause for _ in range(4)]
    assert flags == [False, False, True, True]


def test_thanh_cong_xoa_dem_va_hoi_phuc_dan() -> None:
    guard = RateGuard()
    guard.on_blocked(None, now=0.0)
    guard.on_blocked(None, now=0.0)
    assert guard.delay_factor == 4.0
    guard.on_success()
    assert guard.consecutive_blocks == 0
    assert guard.delay_factor == pytest.approx(3.2)
    for _ in range(50):
        guard.on_success()
    assert guard.delay_factor == 1.0  # không xuống dưới 1


def test_thanh_cong_xen_giua_khong_cho_tam_dung() -> None:
    guard = RateGuard(max_consecutive_blocks=2)
    guard.on_blocked(None, now=0.0)
    guard.on_success()
    assert not guard.on_blocked(None, now=0.0).should_pause


def test_cooldown_until_khong_bao_gio_lui_lai() -> None:
    guard = RateGuard()
    guard.on_blocked(500.0, now=100.0)  # tới 600
    guard.on_success()
    guard.on_blocked(None, now=110.0)  # 110 + 96 < 600
    assert guard.cooldown_until == pytest.approx(600.0)


def test_thoi_gian_cooldown_con_lai() -> None:
    guard = RateGuard()
    guard.on_blocked(None, now=1000.0)
    assert guard.remaining_cooldown(1000.0) == pytest.approx(60.0)
    assert guard.remaining_cooldown(1030.0) == pytest.approx(30.0)
    assert guard.remaining_cooldown(2000.0) == 0.0
    assert RateGuard().remaining_cooldown(0.0) == 0.0


def test_reset_sau_khi_tiep_tuc_giu_nhip_cham() -> None:
    guard = RateGuard(max_consecutive_blocks=2)
    guard.on_blocked(None, now=0.0)
    assert guard.on_blocked(None, now=0.0).should_pause
    guard.reset_after_resume()
    assert guard.consecutive_blocks == 0
    assert guard.cooldown_until == 0.0
    assert guard.remaining_cooldown(0.0) == 0.0
    assert guard.delay_factor == 4.0  # vẫn giữ nhịp chậm
    decision = guard.on_blocked(None, now=0.0)
    assert decision.consecutive_blocks == 1 and not decision.should_pause
