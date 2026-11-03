"""Unit test cho app/services/spss/statistics.py (Cronbach's Alpha, tương quan, Spearman-Brown)."""

import math

import numpy as np
import pytest

from app.services.spss.statistics import (
    MAX_LATENT_R,
    alpha_from_r,
    cronbach_alpha,
    discretized_moments,
    finite_or_none,
    mean_inter_item_correlation,
    r_from_alpha,
)


def test_alpha_bang_1_khi_cac_cot_tuong_quan_hoan_hao() -> None:
    column = np.array([1, 2, 3, 4, 5, 3, 2], dtype=float)
    data = np.column_stack([column, column, column])
    assert cronbach_alpha(data) == pytest.approx(1.0)


def test_alpha_gan_0_khi_cac_cot_doc_lap() -> None:
    rng = np.random.default_rng(7)
    data = rng.standard_normal((5000, 5))
    assert abs(cronbach_alpha(data)) < 0.05


def test_alpha_gia_tri_tinh_tay() -> None:
    """Ví dụ nhỏ tính tay: k=2, Var(X1)=Var(X2)=1, Var(tổng)=3 → α = 2·(1 - 2/3) = 2/3."""
    data = np.array([[1, 2], [2, 2], [2, 3], [3, 3]], dtype=float)
    item_var = data.var(axis=0, ddof=1).sum()
    total_var = data.sum(axis=1).var(ddof=1)
    expected = 2 * (1 - item_var / total_var)
    assert cronbach_alpha(data) == pytest.approx(expected)


@pytest.mark.parametrize(
    "data",
    [
        np.array([[1.0, 2.0]]),  # 1 hàng
        np.array([[1.0], [2.0], [3.0]]),  # 1 cột
        np.array([1.0, 2.0, 3.0]),  # không phải ma trận 2 chiều
        np.ones((5, 3)),  # tổng không đổi → phương sai 0
    ],
)
def test_alpha_khong_xac_dinh_tra_ve_nan(data: np.ndarray) -> None:
    assert math.isnan(cronbach_alpha(data))


def test_alpha_nhan_list_python() -> None:
    assert cronbach_alpha([[1, 1], [2, 2], [3, 3]]) == pytest.approx(1.0)


def test_tuong_quan_trung_binh_bo_qua_cot_hang_so() -> None:
    """Cột hằng số cho hệ số NaN → bị loại, chỉ còn cặp hợp lệ."""
    a = np.array([1, 2, 3, 4, 5], dtype=float)
    data = np.column_stack([a, a * 2 + 1, np.full(5, 3.0)])
    assert mean_inter_item_correlation(data) == pytest.approx(1.0)


def test_tuong_quan_trung_binh_tat_ca_hang_so_la_nan() -> None:
    assert math.isnan(mean_inter_item_correlation(np.full((6, 3), 2.0)))


def test_tuong_quan_trung_binh_qua_it_hang_la_nan() -> None:
    assert math.isnan(mean_inter_item_correlation(np.array([[1.0, 2.0], [2.0, 3.0]])))


def test_tuong_quan_trung_binh_cot_nguoc_chieu() -> None:
    a = np.arange(10, dtype=float)
    assert mean_inter_item_correlation(np.column_stack([a, -a])) == pytest.approx(-1.0)


@pytest.mark.parametrize("k", [2, 3, 5, 10])
@pytest.mark.parametrize("r", [0.0, 0.1, 0.35, 0.6, 0.9])
def test_r_va_alpha_chuyen_qua_lai(r: float, k: int) -> None:
    assert r_from_alpha(alpha_from_r(r, k), k) == pytest.approx(r, abs=1e-9)


def test_r_from_alpha_bien_va_k_nho() -> None:
    assert r_from_alpha(0.8, 1) == 0.0
    assert r_from_alpha(0.999999, 2) <= MAX_LATENT_R
    assert r_from_alpha(-0.5, 4) == 0.0  # alpha âm bị kẹp về 0
    assert r_from_alpha(1.0, 4) == MAX_LATENT_R  # mẫu số = 1 > 0 nhưng r = 1 bị kẹp
    assert r_from_alpha(2.0, 3) == MAX_LATENT_R  # mẫu số <= 0


def test_alpha_from_r_k_nho_la_nan() -> None:
    assert math.isnan(alpha_from_r(0.5, 1))
    assert alpha_from_r(0.5, 3) == pytest.approx(0.75)


def test_finite_or_none() -> None:
    assert finite_or_none(None) is None
    assert finite_or_none(float("nan")) is None
    assert finite_or_none(float("inf")) is None
    assert finite_or_none(0.123456) == 0.1235


def test_moment_roi_rac_xac_suat_tong_bang_1_va_nam_trong_bien() -> None:
    for mean, std in [(3.0, 1.0), (1.2, 0.5), (4.9, 2.0), (-10.0, 1.0), (20.0, 1.0)]:
        m, s = discretized_moments(mean, std, 1, 5)
        assert 1.0 <= m <= 5.0
        assert 0.0 <= s <= 2.0  # SD tối đa trên thang 1..5


def test_moment_roi_rac_doi_xung_o_tam_thang() -> None:
    m, s = discretized_moments(3.0, 0.8, 1, 5)
    assert m == pytest.approx(3.0, abs=1e-9)
    assert s > 0


def test_moment_roi_rac_tien_toi_bien_khi_lech_xa() -> None:
    assert discretized_moments(-50.0, 1.0, 1, 7) == pytest.approx((1.0, 0.0), abs=1e-9)
    assert discretized_moments(50.0, 1.0, 1, 7) == pytest.approx((7.0, 0.0), abs=1e-9)


def test_moment_roi_rac_khop_mo_phong() -> None:
    rng = np.random.default_rng(3)
    samples = np.clip(np.round(rng.normal(3.6, 1.1, 200_000)), 1, 5)
    m, s = discretized_moments(3.6, 1.1, 1, 5)
    assert m == pytest.approx(samples.mean(), abs=0.01)
    assert s == pytest.approx(samples.std(), abs=0.01)
