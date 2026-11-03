"""Kiểm thử bộ lập lịch Poisson Jitter (app/workers/scheduler.py)."""

import numpy as np
import pytest

from app.workers.scheduler import poisson_delays, remaining_duration_seconds


@pytest.mark.parametrize("n", [0, -1, -10])
def test_so_luong_khong_duong_tra_ve_mang_rong(n: int) -> None:
    result = poisson_delays(n, 60.0, np.random.default_rng(1))
    assert result.shape == (0,)


@pytest.mark.parametrize("total", [0.0, -5.0])
def test_thoi_luong_khong_duong_tra_ve_toan_so_0(total: float) -> None:
    result = poisson_delays(4, total, np.random.default_rng(1))
    assert result.shape == (4,)
    assert np.all(result == 0)


@pytest.mark.parametrize(("n", "total"), [(1, 10.0), (5, 60.0), (100, 3600.0), (1000, 7.5)])
def test_tong_khoang_nghi_khop_thoi_luong(n: int, total: float) -> None:
    result = poisson_delays(n, total, np.random.default_rng(7))
    assert result.shape == (n,)
    assert float(result.sum()) == pytest.approx(total, rel=1e-9)
    assert np.all(result >= 0)


def test_cung_seed_cho_cung_ket_qua() -> None:
    a = poisson_delays(20, 100.0, np.random.default_rng(42))
    b = poisson_delays(20, 100.0, np.random.default_rng(42))
    c = poisson_delays(20, 100.0, np.random.default_rng(43))
    assert np.array_equal(a, b)
    assert not np.array_equal(a, c)


def test_khoang_nghi_khong_deu_nhau() -> None:
    """Phân phối mũ: các khoảng nghỉ phải dao động, không phải hằng số."""
    result = poisson_delays(200, 200.0, np.random.default_rng(3))
    assert result.std() > 0.3
    assert result.max() > 2 * result.min()


def test_tong_ngau_nhien_bang_0_dung_khoang_deu() -> None:
    """Nhánh phòng vệ: nếu rng trả toàn 0 thì chia đều thời lượng."""

    class ZeroRng:
        def exponential(self, scale: float, size: int) -> np.ndarray:
            return np.zeros(size)

    result = poisson_delays(4, 20.0, ZeroRng())  # type: ignore[arg-type]
    assert np.allclose(result, 5.0)


@pytest.mark.parametrize(
    ("minutes", "target", "remaining", "expected"),
    [
        (10, 100, 100, 600.0),
        (10, 100, 50, 300.0),
        (10, 100, 1, 6.0),
        (10, 100, 150, 600.0),  # còn lại vượt mục tiêu → tối đa toàn bộ thời lượng
        (10, 0, 5, 0.0),
        (10, -1, 5, 0.0),
        (10, 100, 0, 0.0),
        (10, 100, -3, 0.0),
        (0, 100, 50, 0.0),
    ],
)
def test_thoi_luong_con_lai_theo_ty_le(minutes: float, target: int, remaining: int, expected: float) -> None:
    assert remaining_duration_seconds(minutes, target, remaining) == pytest.approx(expected)
