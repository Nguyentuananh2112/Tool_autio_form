"""Unit test cho app/services/text_mutation.py (Micro-Mutation câu trả lời tự luận)."""

import re

import numpy as np
import pytest

from app.services.text_mutation import (
    MAX_WORDS_TO_MERGE,
    _lower_first_letter,
    _merge,
    _toggle_first_letter,
    _toggle_trailing_period,
    micro_mutate,
)

POOL = ["Sản phẩm tốt", "Giá hơi cao.", "Giao hàng nhanh và đóng gói cẩn thận", "Ổn"]


def _words(text: str) -> set[str]:
    return {w.lower() for w in re.findall(r"\w+", text)}


@pytest.mark.parametrize(
    ("text", "expected"),
    [("abc", "Abc"), ("Abc", "abc"), ("  123 ổn", "  123 Ổn"), ("123", "123"), ("", "")],
)
def test_dao_chu_cai_dau(text: str, expected: str) -> None:
    assert _toggle_first_letter(text) == expected


def test_ha_chu_cai_dau() -> None:
    assert _lower_first_letter("Ổn định") == "ổn định"
    assert _lower_first_letter("1. Tốt") == "1. tốt"
    assert _lower_first_letter("!!!") == "!!!"


@pytest.mark.parametrize(
    ("text", "expected"),
    [("Tốt", "Tốt."), ("Tốt.", "Tốt"), ("Tốt...", "Tốt"), ("Tốt!", "Tốt!"), ("Tốt?", "Tốt?"), ("", "")],
)
def test_dao_dau_cham_cuoi(text: str, expected: str) -> None:
    assert _toggle_trailing_period(text) == expected


def test_ghep_hai_cau() -> None:
    assert _merge("Tốt. ", " Rẻ", ", ") == "Tốt, rẻ"
    assert _merge("Tốt.", "Rẻ", " và ") == "Tốt và rẻ"
    assert _merge("Tốt.", "Rẻ", ". ") == "Tốt. Rẻ"  # sau dấu chấm giữ chữ hoa


def test_chuoi_rong_tra_ve_nguyen_ban() -> None:
    rng = np.random.default_rng(0)
    assert micro_mutate("", rng, POOL) == ""
    assert micro_mutate("   ", rng, POOL) == "   "


def test_khong_bao_gio_rong_va_giu_tu_noi_dung() -> None:
    rng = np.random.default_rng(1)
    for _ in range(500):
        source = POOL[int(rng.integers(len(POOL)))]
        result = micro_mutate(source, rng, POOL)
        assert result.strip()
        assert _words(source) <= _words(result)


def test_chuan_hoa_khoang_trang() -> None:
    rng = np.random.default_rng(2)
    for _ in range(50):
        assert "  " not in micro_mutate("  Rất   hài  lòng ", rng)


def test_khong_ghep_khi_khong_co_pool_hoac_pool_mot_cau() -> None:
    rng = np.random.default_rng(3)
    for pool in ((), ("Một câu",)):
        for _ in range(200):
            result = micro_mutate("Một câu", rng, pool)
            assert _words(result) == _words("Một câu")


def test_co_ghep_khi_cau_ngan() -> None:
    rng = np.random.default_rng(4)
    results = [micro_mutate("Tốt", rng, ["Tốt", "Rẻ"]) for _ in range(400)]
    merged = [r for r in results if "rẻ" in r.lower()]
    assert 20 < len(merged) < 120  # ~15% (chỉ khi bốc trúng câu khác: ~7.5%)


def test_khong_ghep_khi_cau_dai() -> None:
    long_text = " ".join(f"từ{i}" for i in range(MAX_WORDS_TO_MERGE + 1))
    rng = np.random.default_rng(5)
    for _ in range(300):
        result = micro_mutate(long_text, rng, [long_text, "Ngắn"])
        assert "ngắn" not in result.lower()


def test_xac_dinh_voi_cung_seed() -> None:
    first = [micro_mutate(t, np.random.default_rng(42), POOL) for t in POOL]
    second = [micro_mutate(t, np.random.default_rng(42), POOL) for t in POOL]
    assert first == second


def test_co_tao_ra_bien_the() -> None:
    rng = np.random.default_rng(6)
    variants = {micro_mutate("Sản phẩm tốt", rng, POOL) for _ in range(200)}
    assert {"Sản phẩm tốt", "sản phẩm tốt", "Sản phẩm tốt."} <= variants
