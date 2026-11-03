"""Kiểm thử trạng thái chạy trong bộ nhớ (app/workers/campaign_control.py)."""

import asyncio
import logging
import time

import pytest

from app.workers import campaign_control as cc
from app.workers.campaign_control import CampaignControl, CampaignRegistry, EventBus

# ---------- CampaignControl ----------


def test_trang_thai_ban_dau() -> None:
    control = CampaignControl(campaign_id="c1")
    assert not control.is_paused and not control.is_cancelled
    assert not control.is_active and control.pause_reason is None


def test_tam_dung_va_tiep_tuc() -> None:
    control = CampaignControl(campaign_id="c1")
    control.pause("Bị giới hạn")
    assert control.is_paused and control.pause_reason == "Bị giới hạn"
    control.resume()
    assert not control.is_paused and control.pause_reason is None


async def test_cho_tiep_tuc_tra_ve_true_khi_duoc_tiep_tuc() -> None:
    control = CampaignControl(campaign_id="c1")
    control.pause()
    waiter = asyncio.create_task(control.wait_until_resumed())
    await asyncio.sleep(0.01)
    assert not waiter.done()
    control.resume()
    assert await asyncio.wait_for(waiter, 1) is True


async def test_huy_danh_thuc_worker_dang_cho_va_tra_ve_false() -> None:
    control = CampaignControl(campaign_id="c1")
    control.pause()
    waiter = asyncio.create_task(control.wait_until_resumed())
    await asyncio.sleep(0.01)
    control.cancel()
    assert await asyncio.wait_for(waiter, 1) is False
    assert control.is_cancelled and not control.is_paused


async def test_cho_tiep_tuc_khi_khong_tam_dung_tra_ngay() -> None:
    control = CampaignControl(campaign_id="c1")
    assert await asyncio.wait_for(control.wait_until_resumed(), 0.5) is True


async def test_ngu_het_thoi_gian_tra_ve_true() -> None:
    control = CampaignControl(campaign_id="c1")
    started = time.monotonic()
    assert await control.sleep(0.02) is True
    assert time.monotonic() - started >= 0.01  # đồng hồ Windows thô ~15 ms


async def test_ngu_bi_huy_thuc_day_ngay() -> None:
    control = CampaignControl(campaign_id="c1")
    sleeper = asyncio.create_task(control.sleep(30))
    await asyncio.sleep(0.01)
    started = time.monotonic()
    control.cancel()
    assert await asyncio.wait_for(sleeper, 1) is False
    assert time.monotonic() - started < 0.5


@pytest.mark.parametrize("seconds", [0, -1])
async def test_ngu_khong_duong_tra_ngay(seconds: float) -> None:
    control = CampaignControl(campaign_id="c1")
    assert await control.sleep(seconds) is True
    control.cancel()
    assert await control.sleep(seconds) is False


def test_reset_xoa_huy_va_tam_dung() -> None:
    control = CampaignControl(campaign_id="c1")
    control.pause("x")
    control.cancel()
    control.reset()
    assert not control.is_cancelled and not control.is_paused
    assert control.pause_reason is None


async def test_sau_reset_ngu_khong_bi_huy_ngay() -> None:
    control = CampaignControl(campaign_id="c1")
    control.cancel()
    control.reset()
    assert await control.sleep(0.01) is True


async def test_is_active_theo_task() -> None:
    control = CampaignControl(campaign_id="c1")
    control.task = asyncio.create_task(asyncio.sleep(0.01))
    assert control.is_active
    await control.task
    assert not control.is_active


# ---------- EventBus ----------


async def test_phat_su_kien_toi_moi_nguoi_theo_doi_dung_chien_dich() -> None:
    bus = EventBus()
    q1, q2 = bus.subscribe("a"), bus.subscribe("a")
    other = bus.subscribe("b")
    bus.publish("a", {"type": "progress", "n": 1})
    assert q1.get_nowait() == {"type": "progress", "n": 1}
    assert q2.get_nowait() == {"type": "progress", "n": 1}
    assert other.empty()


def test_phat_khi_khong_ai_theo_doi_khong_loi() -> None:
    EventBus().publish("khong-co", {"type": "x"})


def test_huy_theo_doi_ngung_nhan_va_don_dict() -> None:
    bus = EventBus()
    q1, q2 = bus.subscribe("a"), bus.subscribe("a")
    bus.unsubscribe("a", q1)
    bus.publish("a", {"n": 1})
    assert q1.empty() and q2.qsize() == 1
    bus.unsubscribe("a", q2)
    assert "a" not in bus._subscribers
    # Hủy lần nữa / hủy chiến dịch lạ không gây lỗi
    bus.unsubscribe("a", q2)
    bus.unsubscribe("zzz", q2)


def test_hang_doi_day_thi_bo_su_kien_va_canh_bao(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setattr(cc, "EVENT_QUEUE_SIZE", 2)
    bus = EventBus()
    slow = bus.subscribe("a")
    monkeypatch.setattr(cc, "EVENT_QUEUE_SIZE", 10)
    fast = bus.subscribe("a")
    with caplog.at_level(logging.WARNING, logger=cc.__name__):
        for i in range(3):
            bus.publish("a", {"n": i})
    assert slow.qsize() == 2 and fast.qsize() == 3
    assert [slow.get_nowait()["n"] for _ in range(2)] == [0, 1]
    assert any("chậm" in r.getMessage() for r in caplog.records)


# ---------- CampaignRegistry ----------


def test_get_or_create_tra_cung_doi_tuong() -> None:
    reg = CampaignRegistry()
    assert reg.get("x") is None
    control = reg.get_or_create("x")
    assert reg.get_or_create("x") is control and reg.get("x") is control
    reg.discard("x")
    assert reg.get("x") is None
    reg.discard("x")  # không lỗi


async def test_active_ids_chi_gom_task_dang_chay() -> None:
    reg = CampaignRegistry()
    running = reg.get_or_create("chay")
    running.task = asyncio.create_task(asyncio.sleep(10))
    done = reg.get_or_create("xong")
    done.task = asyncio.create_task(asyncio.sleep(0))
    await done.task
    reg.get_or_create("chua-co-task")
    assert reg.active_ids() == ["chay"]
    running.task.cancel()


async def test_stop_all_huy_va_cho_worker_hop_tac() -> None:
    reg = CampaignRegistry()
    finished: list[str] = []

    async def worker(control: CampaignControl) -> None:
        while await control.sleep(30):
            pass
        finished.append(control.campaign_id)

    for cid in ("a", "b"):
        control = reg.get_or_create(cid)
        control.task = asyncio.create_task(worker(control))
    idle = reg.get_or_create("idle")
    await asyncio.sleep(0.01)
    started = time.monotonic()
    await reg.stop_all(timeout=2)
    assert time.monotonic() - started < 1
    assert sorted(finished) == ["a", "b"]
    assert not idle.is_cancelled  # không có task thì không bị hủy
    assert reg.get("a") is None and reg.active_ids() == []


async def test_stop_all_khong_co_chien_dich() -> None:
    await CampaignRegistry().stop_all(timeout=0.1)


async def test_stop_all_ton_trong_timeout_voi_worker_khong_hop_tac() -> None:
    """BUG-011 (đã sửa): task không đọc cờ huỷ phải bị cancel khi quá hạn, không chạy ngầm."""
    reg = CampaignRegistry()
    control = reg.get_or_create("cung-dau")
    control.task = asyncio.create_task(asyncio.sleep(5))  # không đọc cờ hủy
    started = time.monotonic()
    await reg.stop_all(timeout=0.05)
    assert time.monotonic() - started < 1
    assert reg.get("cung-dau") is None
    assert control.task.cancelled()
