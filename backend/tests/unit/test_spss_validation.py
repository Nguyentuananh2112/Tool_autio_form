"""Unit test cho app/services/spss/validation.py (kiểm tra luật trước khi sinh dữ liệu)."""

import numpy as np
import pytest

from app.schemas.campaign_schema import QuestionRuleConfig, RuleStrategy
from app.schemas.form_schema import OTHER_OPTION_VALUE, QuestionType
from app.services.spss.validation import (
    DEFAULT_CHECKBOX_PROBABILITY,
    GeneratorConfigError,
    default_checkbox_probability,
    resolve_weights,
    validate_question,
)
from tests.unit.spss_factories import option, other_option, question


def _run(q, rule) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    validate_question(q, rule, errors, warnings)
    return errors, warnings


def _rule(**kwargs) -> QuestionRuleConfig:
    kwargs.setdefault("question_type", 2)
    return QuestionRuleConfig(entry_id="1", **kwargs)


def _mc(required: bool = False):
    return question("1", QuestionType.MULTIPLE_CHOICE, [option("A"), option("B"), other_option()], required=required)


def _cb():
    return question("1", QuestionType.CHECKBOX, [option("X"), option("Y"), other_option()])


def test_loi_gop_thong_diep() -> None:
    error = GeneratorConfigError(["lỗi 1", "lỗi 2"])
    assert error.errors == ["lỗi 1", "lỗi 2"]
    assert str(error) == "lỗi 1; lỗi 2"


# ------------------------------------------------------------------ resolve_weights
def test_trong_so_mac_dinh_lua_chon_don_muc_khac_bang_0() -> None:
    _, weights = resolve_weights(_mc(), None)
    assert weights.tolist() == [1.0, 1.0, 0.0]


def test_trong_so_mac_dinh_checkbox_50() -> None:
    _, weights = resolve_weights(_cb(), None)
    assert weights.tolist() == [50.0, 50.0, 0.0]


def test_trong_so_checkbox_bi_kep_0_100_va_khoa_thieu_bang_0() -> None:
    _, weights = resolve_weights(_cb(), _rule(question_type=4, weights={"X": 150, OTHER_OPTION_VALUE: 20}))
    assert np.array_equal(weights, [100.0, 0.0, 20.0])


# ------------------------------------------------------------------ SKIP / FIXED
def test_skip_cau_bat_buoc_bao_loi() -> None:
    errors, _ = _run(_mc(required=True), _rule(strategy=RuleStrategy.SKIP))
    assert len(errors) == 1 and "không thể bỏ qua (SKIP)" in errors[0]


def test_skip_cau_khong_bat_buoc_hop_le() -> None:
    assert _run(_mc(), _rule(strategy=RuleStrategy.SKIP)) == ([], [])


def test_fixed_gia_tri_khong_co_trong_lua_chon() -> None:
    errors, _ = _run(_mc(), _rule(strategy=RuleStrategy.FIXED, fixed_value="Z"))
    assert any("giá trị cố định ['Z'] không có" in e for e in errors)


def test_fixed_nhieu_gia_tri_cho_cau_mot_lua_chon() -> None:
    errors, _ = _run(_mc(), _rule(strategy=RuleStrategy.FIXED, fixed_value=["A", "B"]))
    assert errors == ["'Câu 1': câu một lựa chọn chỉ nhận 1 giá trị cố định."]


def test_fixed_nhieu_gia_tri_cho_checkbox_hop_le() -> None:
    assert _run(_cb(), _rule(question_type=4, strategy=RuleStrategy.FIXED, fixed_value=["X", "Y"])) == ([], [])


def test_fixed_muc_khac_thieu_pool() -> None:
    errors, _ = _run(_mc(), _rule(strategy=RuleStrategy.FIXED, fixed_value=OTHER_OPTION_VALUE))
    assert any("other_text_pool" in e for e in errors)


def test_fixed_cau_tu_luan_khong_kiem_tra_lua_chon() -> None:
    q = question("1", QuestionType.SHORT_ANSWER)
    assert _run(q, _rule(question_type=0, strategy=RuleStrategy.FIXED, fixed_value="bất kỳ")) == ([], [])


# ------------------------------------------------------------------ lựa chọn
def test_muc_khac_co_trong_so_nhung_thieu_pool() -> None:
    errors, _ = _run(_mc(), _rule(weights={"A": 90, OTHER_OPTION_VALUE: 10}))
    assert errors == ["'Câu 1': 'Mục khác' có trọng số > 0 nhưng chưa nhập other_text_pool."]


def test_muc_khac_co_pool_hop_le() -> None:
    assert _run(_mc(), _rule(weights={"A": 90, OTHER_OPTION_VALUE: 10}, other_text_pool=["x"])) == ([], [])


def test_min_checked_vuot_so_lua_chon() -> None:
    errors, _ = _run(_cb(), _rule(question_type=4, min_checked=4))
    assert any("min_checked vượt quá số lựa chọn (3)" in e for e in errors)


def test_khoa_trong_so_khong_ton_tai_canh_bao() -> None:
    _, warnings = _run(_mc(), _rule(weights={"A": 50, "B": 50, "Ma": 5}))
    assert any("không tồn tại ['Ma']" in w for w in warnings)


def test_tong_trong_so_khac_100_canh_bao() -> None:
    errors, warnings = _run(_mc(), _rule(weights={"A": 30, "B": 30}))
    assert errors == []
    assert warnings == ["'Câu 1': tổng trọng số = 60.0 (khác 100), sẽ được chuẩn hóa."]


def test_tong_trong_so_lech_nho_khong_canh_bao() -> None:
    assert _run(_mc(), _rule(weights={"A": 50.2, "B": 50})) == ([], [])


@pytest.mark.parametrize(("required", "has_error"), [(True, True), (False, False)])
def test_tong_trong_so_bang_0(required: bool, has_error: bool) -> None:
    errors, warnings = _run(_mc(required=required), _rule(weights={"A": 0, "B": 0}))
    assert bool(errors) is has_error
    assert bool(warnings) is not has_error


def test_checkbox_khong_canh_bao_tong_khac_100() -> None:
    assert _run(_cb(), _rule(question_type=4, weights={"X": 10, "Y": 10})) == ([], [])


# ------------------------------------------------------------------ tự luận / ngày giờ
def test_tu_luan_bat_buoc_thieu_pool_bao_loi() -> None:
    errors, _ = _run(question("1", QuestionType.PARAGRAPH, required=True), None)
    assert len(errors) == 1 and "text_pool" in errors[0]


def test_tu_luan_khong_bat_buoc_thieu_pool_canh_bao() -> None:
    errors, warnings = _run(question("1", QuestionType.SHORT_ANSWER), None)
    assert errors == [] and len(warnings) == 1


def test_tu_luan_co_pool_hop_le() -> None:
    assert _run(question("1", QuestionType.SHORT_ANSWER, required=True), _rule(question_type=0, text_pool=["ok"])) == ([], [])


@pytest.mark.parametrize("type_id", [QuestionType.DATE, QuestionType.TIME])
def test_ngay_gio_khong_can_cau_hinh(type_id: int) -> None:
    assert _run(question("1", type_id, required=True), None) == ([], [])


# ------------------------------------------------------------------ default_checkbox_probability (BUG-014)
def _many(n: int, *, required: bool = False, other: bool = True):
    opts = [option(f"L{i}") for i in range(n)] + ([other_option()] if other else [])
    return question("1", QuestionType.CHECKBOX, opts, required=required)


@pytest.mark.parametrize(("n", "required", "min_checked", "max_checked", "expected"), [
    (11, True, 0, 3, 18.2),    # E4 thật: (1 + 3) / 2 / 11 ô
    (11, False, 0, 3, 13.6),   # không bắt buộc: (0 + 3) / 2
    (10, False, 2, 4, 30.0),   # (2 + 4) / 2 / 10
    (4, True, 0, 4, 50.0),     # vượt 50% → giữ trần 50%
    (40, False, 0, 1, 5.0),    # quá nhỏ → sàn 5%
    (5, False, 5, 3, 50.0),    # min > max (dữ liệu cũ) → dùng max làm min: 3/5 = 60% → trần 50
])
def test_xac_suat_mac_dinh_theo_gioi_han(n, required, min_checked, max_checked, expected) -> None:
    rule = _rule(question_type=4, max_checked=max_checked)
    rule.min_checked = min_checked  # bỏ qua kiểm tra min <= max để thử dữ liệu cũ
    assert default_checkbox_probability(_many(n, required=required), rule) == pytest.approx(expected)


@pytest.mark.parametrize("rule", [None, _rule(question_type=4), _rule(question_type=4, min_checked=2)])
def test_xac_suat_mac_dinh_khong_gioi_han_giu_50(rule) -> None:
    assert default_checkbox_probability(_many(11), rule) == DEFAULT_CHECKBOX_PROBABILITY


def test_xac_suat_mac_dinh_chi_toan_muc_khac_giu_50() -> None:
    q = question("1", QuestionType.CHECKBOX, [other_option()])
    assert default_checkbox_probability(q, _rule(question_type=4, max_checked=1)) == DEFAULT_CHECKBOX_PROBABILITY


def test_resolve_weights_checkbox_gioi_han_dung_muc_mac_dinh_moi() -> None:
    _, weights = resolve_weights(_many(11, required=True), _rule(question_type=4, max_checked=3))
    assert weights.tolist() == [18.2] * 11 + [0.0]


def test_resolve_weights_co_trong_so_thi_bo_qua_mac_dinh() -> None:
    _, weights = resolve_weights(_many(3), _rule(question_type=4, max_checked=1, weights={"L0": 90}))
    assert weights.tolist() == [90.0, 0.0, 0.0, 0.0]
