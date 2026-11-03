"""Thứ tự tích cực, copula thái độ, bộ soát và bộ sửa (app/services/logic/*)."""

import numpy as np
import pytest

from app.schemas.form_schema import QuestionType
from app.schemas.logic_schema import AttitudeItem, Consistency, TextSentiment
from app.services.logic.attitude import LOADING, copula_picks, item_latent, pool_for, sentiment_of
from app.services.logic.checker import SPREAD_LIMIT, ResponseChecker, ViolationKind
from app.services.logic.ordering import is_rating_scale, ordered_values, positions, spread_groups
from app.services.logic.repair import ResponseRepairer
from app.services.spss.answers import Answer
from tests.unit.logic_factories import (
    ADS, AGE, FEATURES, FREQ, JOB, KNOW, NONE_FEATURE, QUALITY, RECOMMEND, STUDENT, TRUST, UNDER_18,
    sample_form, sample_logic, usually_rule,
)
from tests.unit.spss_factories import option, other_option, question

FORM = sample_form()
Q = {q.entry_id: q for q in FORM.questions}


def _a(*values: str, numeric: float | None = None) -> Answer:
    return Answer(values=list(values), numeric_value=numeric)


def _consistent() -> dict[str, Answer]:
    return {
        AGE: _a(UNDER_18), JOB: _a(STUDENT), QUALITY: _a("4", numeric=4), TRUST: _a("4", numeric=4),
        RECOMMEND: _a("8", numeric=8), FREQ: _a("Thường xuyên"), FEATURES: _a("Giá rẻ", "Giao nhanh"),
        KNOW: _a("Có biết"), ADS: _a("Luôn thấy"),
    }


# ------------------------------------------------------------------ ordering
def test_thu_tu_tich_cuc_theo_chieu() -> None:
    assert ordered_values(Q[QUALITY], AttitudeItem(entry_id=QUALITY)) == ["1", "2", "3", "4", "5"]
    assert ordered_values(Q[FREQ], AttitudeItem(entry_id=FREQ, positive_high=False)) == ["Hiếm khi", "Thỉnh thoảng", "Thường xuyên"]


def test_vi_tri_bo_muc_khac_va_chia_deu() -> None:
    pos = positions(Q[ADS], AttitudeItem(entry_id=ADS))
    assert pos == {"Luôn thấy": 0.0, "Đôi khi": 0.5, "Chưa thấy": 1.0}


def test_vi_tri_cau_mot_muc_rong() -> None:
    q = question("9", QuestionType.MULTIPLE_CHOICE, [option("A"), other_option()])
    assert positions(q, AttitudeItem(entry_id="9")) == {}


@pytest.mark.parametrize(("entry", "expected"), [(QUALITY, True), (RECOMMEND, True), (FREQ, False), (FEATURES, False), (KNOW, False)])
def test_cau_cham_diem(entry: str, expected: bool) -> None:
    assert is_rating_scale(Q[entry]) is expected


def test_thang_so_it_hon_5_muc_khong_tinh_la_cham_diem() -> None:
    assert not is_rating_scale(question("9", QuestionType.LINEAR_SCALE, [option(v) for v in "1234"]))


def test_thang_so_khong_lien_tiep_khong_tinh() -> None:
    assert not is_rating_scale(question("9", QuestionType.LINEAR_SCALE, [option(v) for v in ["1", "2", "3", "4", "6"]]))


def test_spread_groups_gom_cau_co_thu_bac_va_danh_dau_cau_cham_diem() -> None:
    [(group_id, items)] = spread_groups(FORM, sample_logic())
    assert group_id == "brand"
    assert [(i.entry_id, i.rating) for i in items] == [(QUALITY, True), (TRUST, True), (RECOMMEND, True), (FREQ, False)]


def test_spread_groups_bo_cau_hai_muc() -> None:
    logic = sample_logic()
    logic.attitude_groups[0].items.append(AttitudeItem(entry_id=KNOW))
    [(_, items)] = spread_groups(FORM, logic)
    assert KNOW not in [i.entry_id for i in items]


# ------------------------------------------------------------------ attitude
def test_bien_an_giu_phuong_sai_1_va_tuong_quan_theo_loading() -> None:
    rng = np.random.default_rng(0)
    factor = rng.standard_normal(40_000)
    a, b = item_latent(factor, 0.55, rng), item_latent(factor, 0.55, rng)
    assert a.std() == pytest.approx(1.0, abs=0.02)
    assert np.corrcoef(a, b)[0, 1] == pytest.approx(0.55, abs=0.02)


def test_loading_tang_dan_theo_do_dong_deu() -> None:
    assert LOADING[Consistency.VARIED] < LOADING[Consistency.MODERATE] < LOADING[Consistency.UNIFORM] < 1


def test_copula_giu_ty_le_nguoi_dung_dat() -> None:
    rng = np.random.default_rng(1)
    options = [option(str(i)) for i in range(1, 6)]
    weights = np.array([5.0, 10.0, 20.0, 40.0, 25.0])
    picks = copula_picks(options, weights, [0, 1, 2, 3, 4], rng.standard_normal(50_000), rng)
    shares = np.bincount(picks, minlength=5) / picks.size
    assert shares == pytest.approx(weights / weights.sum(), abs=0.01)


def test_copula_chieu_nguoc_nguoi_tich_cuc_chon_dap_an_dau() -> None:
    rng = np.random.default_rng(2)
    options = [option("Rất tốt"), option("Tốt"), option("Kém")]
    picks = copula_picks(options, np.ones(3), [2, 1, 0], np.array([3.0, -3.0]), rng)
    assert picks.tolist() == [0, 2]


def test_copula_muc_khac_boc_doc_lap_dung_ty_le() -> None:
    rng = np.random.default_rng(3)
    options = [option("A"), option("B"), other_option()]
    picks = copula_picks(options, np.array([45.0, 45.0, 10.0]), [0, 1], rng.standard_normal(40_000), rng)
    assert np.mean(picks == 2) == pytest.approx(0.10, abs=0.01)


def test_copula_tong_trong_so_0_tra_none() -> None:
    assert copula_picks([option("A")], np.zeros(1), [0], np.zeros(3), np.random.default_rng()) is None


def test_copula_chi_co_muc_khac() -> None:
    picks = copula_picks([option("A"), other_option()], np.array([0.0, 5.0]), [0], np.zeros(4), np.random.default_rng())
    assert picks.tolist() == [1, 1, 1, 1]


@pytest.mark.parametrize(("value", "expected"), [(1.0, TextSentiment.POSITIVE), (-1.0, TextSentiment.NEGATIVE), (0.0, TextSentiment.NEUTRAL)])
def test_cam_xuc_theo_nhan_to(value: float, expected: TextSentiment) -> None:
    assert sentiment_of(value) == expected


def test_pool_theo_cam_xuc_va_lui_ve_trung_lap() -> None:
    labels = {"Tuyệt": TextSentiment.POSITIVE, "Tệ": TextSentiment.NEGATIVE}
    pool = ["Tuyệt", "Tệ", "Bình thường"]
    assert pool_for(pool, labels, TextSentiment.POSITIVE) == ["Tuyệt"]
    assert pool_for(["Tệ", "Bình thường"], labels, TextSentiment.POSITIVE) == ["Bình thường"]
    assert pool_for(["Tệ"], labels, TextSentiment.POSITIVE) == ["Tệ"]


# ------------------------------------------------------------------ checker
def test_phan_hoi_nhat_quan_khong_co_mau_thuan() -> None:
    assert ResponseChecker(FORM, sample_logic()).violations(_consistent()) == []


def test_bat_rang_buoc_bat_buoc() -> None:
    answers = _consistent() | {JOB: _a("Nhân viên văn phòng")}
    [v] = ResponseChecker(FORM, sample_logic()).violations(answers)
    assert v.kind == ViolationKind.RULE and v.key == "age" and not v.soft


def test_bat_rang_buoc_khong_bao_gio() -> None:
    answers = _consistent() | {KNOW: _a("Không biết"), ADS: _a("Luôn thấy")}
    assert [v.key for v in ResponseChecker(FORM, sample_logic()).violations(answers)] == ["ads"]


def test_rang_buoc_bo_qua_khi_cau_chua_tra_loi() -> None:
    answers = _consistent() | {JOB: _a("Tự do")}
    del answers[AGE]
    assert ResponseChecker(FORM, sample_logic()).violations(answers) == []


def test_rang_buoc_thuong_la_mau_thuan_mem() -> None:
    logic = sample_logic()
    logic.rules = [usually_rule()]
    answers = _consistent() | {AGE: _a("Trên 25"), JOB: _a("Tự do")}
    checker = ResponseChecker(FORM, logic)
    [v] = checker.violations(answers)
    assert v.soft and checker.blocking(answers) == []


def test_rang_buoc_tren_hop_kiem_khop_mot_gia_tri() -> None:
    logic = sample_logic()
    logic.rules[0] = logic.rules[0].model_copy(update={"if_entry": FEATURES, "if_values": ["Giá rẻ"]})
    assert ResponseChecker(FORM, logic).violations(_consistent() | {JOB: _a(STUDENT)}) == []


def test_bat_o_loai_tru_di_kem() -> None:
    answers = _consistent() | {FEATURES: _a("Giá rẻ", NONE_FEATURE)}
    [v] = ResponseChecker(FORM, sample_logic()).violations(answers)
    assert v.kind == ViolationKind.EXCLUSIVE and v.key == FEATURES


def test_o_loai_tru_mot_minh_hop_le() -> None:
    assert ResponseChecker(FORM, sample_logic()).violations(_consistent() | {FEATURES: _a(NONE_FEATURE)}) == []


@pytest.mark.parametrize(("consistency", "quality", "trust", "bad"), [
    (Consistency.MODERATE, "4", "1", True),   # ví dụ của người dùng: uy tín 4 nhưng chất lượng 1
    (Consistency.MODERATE, "4", "2", False),  # lệch 2 điểm: chấp nhận ở mức vừa phải
    (Consistency.UNIFORM, "4", "2", True),
    (Consistency.UNIFORM, "4", "3", False),
    (Consistency.VARIED, "4", "1", False),
    (Consistency.VARIED, "5", "1", True),
])
def test_do_lech_trong_nhom_theo_do_dong_deu(consistency, quality, trust, bad) -> None:
    answers = _consistent() | {QUALITY: _a(quality), TRUST: _a(trust), RECOMMEND: _a("6"), FREQ: _a("Thỉnh thoảng")}
    kinds = [v.kind for v in ResponseChecker(FORM, sample_logic(consistency)).violations(answers)]
    assert (ViolationKind.SPREAD in kinds) is bad


def test_do_lech_so_thang_1_10_voi_thang_1_5_theo_vi_tri() -> None:
    answers = _consistent() | {QUALITY: _a("5"), TRUST: _a("5"), RECOMMEND: _a("1")}
    assert [v.kind for v in ResponseChecker(FORM, sample_logic()).violations(answers)] == [ViolationKind.SPREAD]


def test_cau_chu_lech_vua_phai_khong_tinh() -> None:
    # Câu chữ không so theo ngưỡng điểm: "Hiếm khi" (đầu tiêu cực) với điểm 4/5, 8/10 vẫn hợp lệ
    answers = _consistent() | {FREQ: _a("Hiếm khi")}
    assert ResponseChecker(FORM, sample_logic()).violations(answers) == []


def test_cau_chu_hai_dau_nguoc_nhau_la_mau_thuan() -> None:
    # "Hiếm khi" (tiêu cực nhất) trong khi chấm 5/5 (tích cực nhất)
    answers = _consistent() | {FREQ: _a("Hiếm khi"), QUALITY: _a("5"), TRUST: _a("5"), RECOMMEND: _a("9")}
    kinds = [v.kind for v in ResponseChecker(FORM, sample_logic(Consistency.VARIED)).violations(answers)]
    assert kinds == [ViolationKind.SPREAD]


def test_sua_hai_dau_nguoc_nhau_keo_cau_chu_vao_mot_muc() -> None:
    answers = _consistent() | {FREQ: _a("Hiếm khi"), QUALITY: _a("5"), TRUST: _a("5"), RECOMMEND: _a("10")}
    _repairer().repair(answers, np.random.default_rng(0))
    assert answers[FREQ].values == ["Thỉnh thoảng"]
    assert answers[QUALITY].values == ["5"] and answers[RECOMMEND].values == ["10"]


def test_nguong_lech_tang_dan() -> None:
    assert SPREAD_LIMIT[Consistency.UNIFORM] < SPREAD_LIMIT[Consistency.MODERATE] < SPREAD_LIMIT[Consistency.VARIED]


# ------------------------------------------------------------------ repair
def _repairer(logic=None, rules=None) -> ResponseRepairer:
    return ResponseRepairer(FORM, logic or sample_logic(), rules or {})


def test_sua_rang_buoc_doi_cau_sau_giu_cau_truoc() -> None:
    answers = _consistent() | {JOB: _a("Tự do")}
    fixed = _repairer().repair(answers, np.random.default_rng(0))
    assert answers[AGE].values == [UNDER_18] and answers[JOB].values == [STUDENT]
    assert answers[JOB].numeric_value == 1.0
    assert [v.key for v in fixed] == ["age"]


def test_sua_rang_buoc_khong_bao_gio_chon_dap_an_khac_khong_phai_muc_khac() -> None:
    rng = np.random.default_rng(1)
    for _ in range(50):
        answers = _consistent() | {KNOW: _a("Không biết"), ADS: _a("Luôn thấy")}
        _repairer().repair(answers, rng)
        assert answers[ADS].values[0] in {"Đôi khi", "Chưa thấy"}


def test_sua_rang_buoc_boc_theo_trong_so() -> None:
    from app.schemas.campaign_schema import QuestionRuleConfig

    rules = {ADS: QuestionRuleConfig(entry_id=ADS, question_type=2, weights={"Luôn thấy": 50, "Đôi khi": 0, "Chưa thấy": 50})}
    answers = _consistent() | {KNOW: _a("Không biết"), ADS: _a("Luôn thấy")}
    _repairer(rules=rules).repair(answers, np.random.default_rng(2))
    assert answers[ADS].values == ["Chưa thấy"]


def test_rang_buoc_thuong_sua_khoang_ty_le() -> None:
    logic = sample_logic()
    logic.rules = [usually_rule()]
    rng = np.random.default_rng(3)
    repaired = 0
    for _ in range(2000):
        answers = _consistent() | {AGE: _a("Trên 25"), JOB: _a("Tự do")}
        _repairer(logic).repair(answers, rng)
        repaired += answers[JOB].values == ["Nhân viên văn phòng"]
    assert repaired / 2000 == pytest.approx(0.75, abs=0.04)


def test_sua_do_lech_keo_cau_lech_ve_gan_nguoi_do() -> None:
    answers = _consistent() | {QUALITY: _a("5"), TRUST: _a("5"), RECOMMEND: _a("1")}
    fixed = _repairer().repair(answers, np.random.default_rng(0))
    assert [v.kind for v in fixed] == [ViolationKind.SPREAD]
    assert answers[QUALITY].values == ["5"] and answers[TRUST].values == ["5"]  # chỉ sửa câu lệch
    assert int(answers[RECOMMEND].values[0]) >= 6 and answers[RECOMMEND].numeric_value == float(answers[RECOMMEND].values[0])
    assert ResponseChecker(FORM, sample_logic()).violations(answers) == []


@pytest.mark.parametrize("consistency", list(Consistency))
def test_sau_khi_sua_khong_con_mau_thuan(consistency: Consistency) -> None:
    rng = np.random.default_rng(4)
    logic = sample_logic(consistency)
    checker, repairer = ResponseChecker(FORM, logic), _repairer(logic)
    for _ in range(300):
        answers = _consistent() | {
            QUALITY: _a(str(rng.integers(1, 6))), TRUST: _a(str(rng.integers(1, 6))),
            RECOMMEND: _a(str(rng.integers(1, 11))), JOB: _a("Tự do"),
        }
        repairer.repair(answers, rng)
        assert checker.blocking(answers) == []


def test_khong_mau_thuan_thi_khong_sua() -> None:
    answers = _consistent()
    before = {k: list(v.values) for k, v in answers.items()}
    assert _repairer().repair(answers, np.random.default_rng()) == []
    assert {k: v.values for k, v in answers.items()} == before


def test_sua_rang_buoc_tren_hop_kiem_bo_gia_tri_cam() -> None:
    logic = sample_logic()
    logic.rules = [logic.rules[0].model_copy(update={"then_entry": FEATURES, "then_op": "IS_NOT", "then_values": ["Giá rẻ"]})]
    answers = _consistent() | {FEATURES: _a("Giá rẻ", "Giao nhanh")}
    _repairer(logic).repair(answers, np.random.default_rng(5))
    assert "Giá rẻ" not in answers[FEATURES].values and "Giao nhanh" in answers[FEATURES].values
