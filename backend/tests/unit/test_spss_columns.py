"""Unit test cho app/services/spss/columns.py (ColumnBuilder sinh cả cột câu trả lời)."""

from datetime import date, time

import numpy as np
import pytest

from app.schemas.campaign_schema import QuestionRuleConfig, RuleStrategy
from app.schemas.form_schema import OTHER_OPTION_VALUE, QuestionType
from app.services.spss.answers import ANSWER_KIND_CHOICE, ANSWER_KIND_DATE, ANSWER_KIND_TEXT, ANSWER_KIND_TIME
from app.services.spss.columns import ColumnBuilder
from tests.unit.spss_factories import option, other_option, question

CHECKBOX = QuestionType.CHECKBOX


def _builder(seed: int = 1, mutator=None) -> ColumnBuilder:
    return ColumnBuilder(np.random.default_rng(seed), mutator)


def _rule(entry_id: str, type_id: int, **kwargs) -> QuestionRuleConfig:
    return QuestionRuleConfig(entry_id=entry_id, question_type=type_id, **kwargs)


def _mc(required: bool = False, with_other: bool = False):
    opts = [option("A"), option("B"), option("C")] + ([other_option()] if with_other else [])
    return question("1", QuestionType.MULTIPLE_CHOICE, opts, required=required)


def _cb(required: bool = False, with_other: bool = False):
    opts = [option("P"), option("Q"), option("R"), option("S")] + ([other_option()] if with_other else [])
    return question("5", CHECKBOX, opts, required=required)


# ------------------------------------------------------------------ FIXED / SKIP
def test_fixed_mot_lua_chon_co_ma_so() -> None:
    column = _builder().for_question(_mc(), _rule("1", 2, strategy=RuleStrategy.FIXED, fixed_value="B"), 5)
    assert all(a.values == ["B"] and a.numeric_value == 2.0 and a.kind == ANSWER_KIND_CHOICE for a in column)
    assert all(a.other_text is None for a in column)


def test_fixed_checkbox_nhieu_gia_tri_khong_co_ma_so() -> None:
    q = question("2", CHECKBOX, [option("X"), option("Y"), option("Z")])
    column = _builder().for_question(q, _rule("2", 4, strategy=RuleStrategy.FIXED, fixed_value=["X", "Z"]), 3)
    assert all(a.values == ["X", "Z"] and a.numeric_value is None for a in column)


def test_fixed_muc_khac_lay_text_tu_pool() -> None:
    rule = _rule("1", 2, strategy=RuleStrategy.FIXED, fixed_value=OTHER_OPTION_VALUE, other_text_pool=["Khác 1", "Khác 2"])
    column = _builder().for_question(_mc(with_other=True), rule, 20)
    assert all(a.values == [OTHER_OPTION_VALUE] and a.other_text in {"Khác 1", "Khác 2"} for a in column)
    assert all(a.numeric_value == 4.0 for a in column)


@pytest.mark.parametrize(
    ("type_id", "value", "kind"),
    [(QuestionType.SHORT_ANSWER, "Cố định", ANSWER_KIND_TEXT), (QuestionType.DATE, "2024-01-02", ANSWER_KIND_DATE),
     (QuestionType.TIME, "09:15", ANSWER_KIND_TIME)],
)
def test_fixed_tu_luan_ngay_gio_dung_kind(type_id: int, value: str, kind: str) -> None:
    q = question("3", type_id)
    column = _builder().for_question(q, _rule("3", type_id, strategy=RuleStrategy.FIXED, fixed_value=value), 2)
    assert [(a.values, a.kind) for a in column] == [([value], kind)] * 2


def test_skip_tra_ve_toan_none() -> None:
    assert _builder().for_question(_mc(), _rule("1", 2, strategy=RuleStrategy.SKIP), 4) == [None] * 4


# ------------------------------------------------------------------ answer_rate / lựa chọn đơn
def test_answer_rate_xap_xi_ty_le() -> None:
    column = _builder(seed=9).for_question(_mc(), _rule("1", 2, answer_rate=30), 4000)
    rate = sum(a is not None for a in column) / 4000
    assert 0.27 < rate < 0.33


def test_answer_rate_bi_bo_qua_voi_cau_bat_buoc() -> None:
    column = _builder().for_question(_mc(required=True), _rule("1", 2, answer_rate=0), 50)
    assert all(a is not None for a in column)


def test_khong_co_rule_chon_deu_va_khong_chon_muc_khac() -> None:
    column = _builder(seed=4).for_question(_mc(with_other=True), None, 3000)
    counts = {v: sum(a.values == [v] for a in column) for v in ["A", "B", "C", OTHER_OPTION_VALUE]}
    assert counts[OTHER_OPTION_VALUE] == 0
    assert all(900 < counts[v] < 1100 for v in "ABC")


def test_trong_so_lua_chon_don_va_ma_so() -> None:
    column = _builder(seed=2).for_question(_mc(), _rule("1", 2, weights={"A": 80, "B": 20}), 3000)
    share_a = sum(a.values == ["A"] for a in column) / 3000
    assert 0.77 < share_a < 0.83
    assert not any(a.values == ["C"] for a in column)
    assert {a.numeric_value for a in column} == {1.0, 2.0}


def test_trong_so_toan_0_tra_ve_none() -> None:
    assert _builder().for_question(_mc(), _rule("1", 2, weights={"A": 0, "B": 0}), 5) == [None] * 5


def test_muc_khac_lua_chon_don_dung_pool() -> None:
    rule = _rule("1", 2, weights={OTHER_OPTION_VALUE: 100}, other_text_pool=["Ý riêng"])
    column = _builder().for_question(_mc(with_other=True), rule, 5)
    assert all(a.values == [OTHER_OPTION_VALUE] and a.other_text == "Ý riêng" for a in column)
    assert all(a.numeric_value == 4.0 for a in column)


# ------------------------------------------------------------------ checkbox
def test_checkbox_ton_trong_max() -> None:
    rule = _rule("5", 4, weights={"P": 100, "Q": 100, "R": 100, "S": 100}, min_checked=1, max_checked=2)
    column = _builder().for_question(_cb(), rule, 200)
    assert all(len(a.values) == 2 for a in column)


def test_checkbox_ton_trong_min_bu_theo_trong_so_cao() -> None:
    rule = _rule("5", 4, weights={"P": 0, "Q": 0, "R": 10, "S": 0}, min_checked=3)
    column = _builder().for_question(_cb(), rule, 200)
    assert all(len(a.values) >= 3 and "R" in a.values for a in column)


def test_checkbox_bat_buoc_xac_suat_0_van_chon_it_nhat_1() -> None:
    rule = _rule("5", 4, weights={"P": 0, "Q": 0, "R": 0, "S": 0})
    column = _builder().for_question(_cb(required=True), rule, 100)
    assert all(a is not None and len(a.values) == 1 for a in column)


def test_checkbox_khong_bat_buoc_xac_suat_0_bo_trong() -> None:
    rule = _rule("5", 4, weights={"P": 0, "Q": 0, "R": 0, "S": 0})
    assert _builder().for_question(_cb(), rule, 10) == [None] * 10


def test_checkbox_gia_tri_sap_theo_thu_tu_option() -> None:
    column = _builder(seed=3).for_question(_cb(), None, 300)
    order = {"P": 0, "Q": 1, "R": 2, "S": 3}
    for answer in column:
        if answer is not None:
            assert [order[v] for v in answer.values] == sorted(order[v] for v in answer.values)
            assert answer.numeric_value is None


def test_checkbox_mac_dinh_moi_o_xac_suat_50() -> None:
    column = _builder(seed=8).for_question(_cb(), None, 4000)
    share_p = sum(a is not None and "P" in a.values for a in column) / 4000
    assert 0.46 < share_p < 0.54


def test_checkbox_muc_khac_khong_pool_khong_bao_gio_chon() -> None:
    rule = _rule("5", 4, weights={"P": 0, OTHER_OPTION_VALUE: 100}, min_checked=1)
    column = _builder().for_question(_cb(with_other=True), rule, 50)
    assert all(OTHER_OPTION_VALUE not in a.values for a in column)


def test_checkbox_muc_khac_co_pool_kem_text() -> None:
    rule = _rule("5", 4, weights={OTHER_OPTION_VALUE: 100}, other_text_pool=["Lý do khác"])
    column = _builder().for_question(_cb(with_other=True), rule, 20)
    assert all(a.values == [OTHER_OPTION_VALUE] and a.other_text == "Lý do khác" for a in column)


def test_checkbox_min_lon_hon_so_o_duoc_dien_bi_kep() -> None:
    rule = _rule("5", 4, weights={"P": 0}, min_checked=5)  # chỉ 4 ô điền được (Mục khác không có pool)
    column = _builder().for_question(_cb(with_other=True), rule, 20)
    assert all(sorted(a.values) == ["P", "Q", "R", "S"] for a in column)


# ------------------------------------------------------------------ ngày / giờ / tự luận
def test_ngay_nam_trong_khoang() -> None:
    rule = _rule("6", 9, date_start=date(2024, 2, 27), date_end=date(2024, 3, 2))
    column = _builder().for_question(question("6", QuestionType.DATE), rule, 500)
    values = {a.values[0] for a in column}
    assert values == {"2024-02-27", "2024-02-28", "2024-02-29", "2024-03-01", "2024-03-02"}
    assert all(a.kind == ANSWER_KIND_DATE for a in column)


def test_ngay_mac_dinh_trong_mot_nam_qua() -> None:
    column = _builder().for_question(question("6", QuestionType.DATE), None, 100)
    today = date.today()
    assert all(0 <= (today - date.fromisoformat(a.values[0])).days <= 365 for a in column)


def test_gio_nam_trong_khoang_va_dinh_dang() -> None:
    rule = _rule("7", 10, time_start=time(9, 58), time_end=time(10, 2))
    column = _builder().for_question(question("7", QuestionType.TIME), rule, 300)
    assert {a.values[0] for a in column} == {"09:58", "09:59", "10:00", "10:01", "10:02"}
    assert all(a.kind == ANSWER_KIND_TIME for a in column)


def test_gio_mac_dinh_8h_den_21h() -> None:
    column = _builder().for_question(question("7", QuestionType.TIME), None, 300)
    assert all("08:00" <= a.values[0] <= "21:00" for a in column)


def test_tu_luan_khong_pool_bo_trong() -> None:
    assert _builder().for_question(question("8", QuestionType.SHORT_ANSWER), None, 3) == [None] * 3


def test_tu_luan_goi_mutator_kem_pool() -> None:
    calls: list[tuple[str, list[str]]] = []

    def mutator(text, rng, pool):
        calls.append((text, list(pool)))
        return text + "!"

    pool = ["Một", "Hai"]
    column = _builder(mutator=mutator).for_question(
        question("8", QuestionType.PARAGRAPH), _rule("8", 1, text_pool=pool), 10
    )
    assert all(a.kind == ANSWER_KIND_TEXT and a.values[0] in {"Một!", "Hai!"} for a in column)
    assert len(calls) == 10 and all(p == pool and t in pool for t, p in calls)


def test_cung_seed_cho_cung_ket_qua() -> None:
    a = _builder(seed=5).for_question(_cb(), None, 50)
    b = _builder(seed=5).for_question(_cb(), None, 50)
    assert [x and x.values for x in a] == [x and x.values for x in b]


def test_checkbox_gioi_han_khong_trong_so_so_o_thay_doi_tu_nhien() -> None:
    """BUG-014 (chạy thật 100 phản hồi): 11 lựa chọn, tối đa 3, không đặt tỷ lệ → trước đây luôn đúng 3 ô."""
    opts = [option(f"L{i}") for i in range(11)] + [other_option()]
    q = question("6", CHECKBOX, opts, required=True)
    column = _builder(seed=7).for_question(q, _rule("6", 4, max_checked=3), 2000)
    counts = np.array([len(a.values) for a in column])
    assert counts.min() >= 1 and counts.max() <= 3
    assert set(counts.tolist()) == {1, 2, 3}
    assert np.mean(counts == 3) < 0.5
    assert 1.6 < counts.mean() < 2.4  # giữa khoảng [1, 3]
    assert all(OTHER_OPTION_VALUE not in a.values for a in column)
