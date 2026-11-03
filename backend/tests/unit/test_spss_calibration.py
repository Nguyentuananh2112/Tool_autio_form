"""Unit test cho app/services/spss/calibration.py (hiệu chỉnh tham số ẩn cho thang Likert)."""

import math

import numpy as np
import pytest

from app.services.spss.calibration import calibrate_latent_correlation, calibrate_latent_moments
from app.services.spss.statistics import MAX_LATENT_R, cronbach_alpha, discretized_moments


@pytest.mark.parametrize(
    ("mean", "std", "lo", "hi"),
    [
        (3.0, 1.0, 1, 5),
        (4.1, 0.7, 1, 5),
        (2.2, 0.9, 1, 5),
        (1.5, 0.6, 1, 5),
        (4.0, 1.2, 1, 7),
        (5.5, 1.0, 1, 7),
        (2.5, 1.5, 1, 7),
    ],
)
def test_hieu_chinh_dat_mean_va_sd_muc_tieu(mean: float, std: float, lo: int, hi: int) -> None:
    latent_mean, latent_std = calibrate_latent_moments(mean, std, lo, hi)
    observed_mean, observed_std = discretized_moments(latent_mean, latent_std, lo, hi)
    assert observed_mean == pytest.approx(mean, abs=0.02)
    assert observed_std == pytest.approx(std, abs=0.02)


def test_hieu_chinh_bu_lam_tron_va_cat_bien() -> None:
    """Mean cao gần biên trên: μ ẩn phải lớn hơn mean mục tiêu để bù phần bị cắt ở 5."""
    latent_mean, latent_std = calibrate_latent_moments(4.5, 0.6, 1, 5)
    assert latent_mean > 4.5
    assert latent_std > 0.6


@pytest.mark.parametrize(("mean", "std"), [(4.8, 1.2), (1.1, 1.5), (3.0, 2.9)])
def test_sd_khong_kha_thi_van_tra_ve_gia_tri_huu_han(mean: float, std: float) -> None:
    latent_mean, latent_std = calibrate_latent_moments(mean, std, 1, 5)
    assert math.isfinite(latent_mean) and math.isfinite(latent_std)
    assert 0.05 <= latent_std <= 10.0
    observed_mean, _ = discretized_moments(latent_mean, latent_std, 1, 5)
    assert observed_mean == pytest.approx(mean, abs=0.02)


@pytest.mark.parametrize("mean", [1.0, 5.0, 0.0, 9.0])
def test_mean_o_bien_hoac_ngoai_thang_duoc_kep(mean: float) -> None:
    latent_mean, latent_std = calibrate_latent_moments(mean, 0.5, 1, 5)
    observed_mean, _ = discretized_moments(latent_mean, latent_std, 1, 5)
    assert 1.0 <= observed_mean <= 5.0
    assert math.isfinite(latent_mean)


def _alpha_of(r: float, latent_mean: float = 3.5, latent_std: float = 1.0, k: int = 4) -> float:
    rng = np.random.default_rng(11)
    factor = rng.standard_normal((4000, 1))
    noise = rng.standard_normal((4000, k))
    latent = latent_mean + latent_std * (math.sqrt(r) * factor + math.sqrt(1 - r) * noise)
    return cronbach_alpha(np.clip(np.round(latent), 1, 5))


def test_tuong_quan_an_don_dieu_theo_alpha_muc_tieu() -> None:
    targets = [0.5, 0.65, 0.75, 0.85, 0.9]
    results = [
        calibrate_latent_correlation(latent_mean=3.5, latent_std=1.0, lo=1, hi=5, k=4, target_alpha=t)
        for t in targets
    ]
    assert results == sorted(results)
    assert all(0.0 <= r <= MAX_LATENT_R for r in results)


@pytest.mark.parametrize("target", [0.6, 0.8, 0.9])
def test_tuong_quan_an_dat_alpha_muc_tieu(target: float) -> None:
    r = calibrate_latent_correlation(latent_mean=3.5, latent_std=1.0, lo=1, hi=5, k=4, target_alpha=target)
    assert _alpha_of(r) == pytest.approx(target, abs=0.03)


def test_tuong_quan_an_theo_target_r() -> None:
    r = calibrate_latent_correlation(latent_mean=3.0, latent_std=1.0, lo=1, hi=5, k=3, target_r=0.4)
    assert 0.4 < r < 0.6  # làm tròn làm giảm tương quan nên r ẩn phải cao hơn


def test_tuong_quan_an_muc_tieu_bang_0_tra_ve_0() -> None:
    assert calibrate_latent_correlation(latent_mean=3.0, latent_std=1.0, lo=1, hi=5, k=4, target_alpha=-0.5) == 0.0


def test_tuong_quan_an_muc_tieu_khong_dat_duoc_tra_ve_tran() -> None:
    r = calibrate_latent_correlation(latent_mean=3.0, latent_std=1.0, lo=1, hi=5, k=2, target_alpha=0.9999)
    assert r == MAX_LATENT_R


def test_tuong_quan_an_thieu_muc_tieu_bao_loi() -> None:
    with pytest.raises(ValueError):
        calibrate_latent_correlation(latent_mean=3.0, latent_std=1.0, lo=1, hi=5, k=4)


def test_tuong_quan_an_xac_dinh_voi_cung_seed() -> None:
    kwargs = dict(latent_mean=3.2, latent_std=0.9, lo=1, hi=5, k=5, target_alpha=0.8, seed=5)
    assert calibrate_latent_correlation(**kwargs) == calibrate_latent_correlation(**kwargs)
