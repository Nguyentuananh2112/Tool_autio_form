"""Bộ sinh có soát logic: nhất quán trong một người mà vẫn giữ tỷ lệ người dùng đặt (ISS-008)."""

import numpy as np
import pytest

from app.schemas.campaign_schema import QuestionRuleConfig, SpssGroupConfig
from app.schemas.logic_schema import Consistency, TextAttitude, TextSentiment
from app.services.logic.checker import ResponseChecker
from app.services.spss.generator import SurveyDataGenerator
from app.services.spss.group_plan import plan_group, sample_group_codes
from app.services.spss.statistics import cronbach_alpha
from tests.unit.logic_factories import (
    AGE, COMMENT, FEATURES, JOB, NONE_FEATURE, QUALITY, RECOMMEND, STUDENT, TRUST, UNDER_18,
    sample_form, sample_logic,
)

FORM = sample_form()
POS, NEG = "Rất hài lòng, sẽ quay lại", "Thất vọng, giao chậm"
RULES = [
    QuestionRuleConfig(entry_id=QUALITY, question_type=5, weights={"1": 5, "2": 10, "3": 20, "4": 40, "5": 25}),
    QuestionRuleConfig(entry_id=COMMENT, question_type=0, text_pool=[POS, "Bình thường", NEG]),
    QuestionRuleConfig(entry_id=FEATURES, question_type=4, weights={"Giá rẻ": 60, "Giao nhanh": 60, "Chính hãng": 60, NONE_FEATURE: 40}),
]


def _gen(logic=None, seed: int = 7, groups=None) -> SurveyDataGenerator:
    return SurveyDataGenerator(FORM, RULES, groups, seed=seed, logic=logic)


def _num(responses, entry: str) -> np.ndarray:
    return np.array([float(r.answers[entry].values[0]) for r in responses])


def test_khong_co_logic_giu_nguyen_hanh_vi_cu() -> None:
    gen = _gen()
    responses = gen.generate(50)
    assert gen.filter_stats is None
    again = _gen().generate(50)
    assert [r.answers[QUALITY].values for r in responses] == [r.answers[QUALITY].values for r in again]


def test_cung_seed_cung_ket_qua() -> None:
    a = _gen(sample_logic()).generate(80)
    b = _gen(sample_logic()).generate(80)
    assert [{k: v.values for k, v in r.answers.items()} for r in a] == [{k: v.values for k, v in r.answers.items()} for r in b]


def test_so_thu_tu_lien_tiep_tu_start_sequence() -> None:
    responses = _gen(sample_logic()).generate(30, start_sequence=11)
    assert [r.sequence_number for r in responses] == list(range(11, 41))


@pytest.mark.parametrize("consistency", list(Consistency))
def test_khong_con_mau_thuan_nao(consistency: Consistency) -> None:
    logic = sample_logic(consistency)
    gen = _gen(logic)
    responses = gen.generate(400)
    checker = ResponseChecker(FORM, logic)
    assert all(checker.blocking(r.answers) == [] for r in responses)
    assert gen.filter_stats is not None and gen.filter_stats.residual == 0


def test_rang_buoc_tuoi_nghe_va_giu_ty_le_tuoi() -> None:
    plain = _gen().generate(3000)
    responses = _gen(sample_logic()).generate(3000)
    under = [r for r in responses if r.answers[AGE].values == [UNDER_18]]
    assert under and all(r.answers[JOB].values == [STUDENT] for r in under)
    share = len(under) / len(responses)
    assert share == pytest.approx(sum(r.answers[AGE].values == [UNDER_18] for r in plain) / len(plain), abs=0.03)


def test_o_loai_tru_khong_di_kem_o_khac() -> None:
    responses = _gen(sample_logic()).generate(1000)
    chosen = [r.answers[FEATURES].values for r in responses]
    assert all(len(v) == 1 for v in chosen if NONE_FEATURE in v)
    assert any(v == [NONE_FEATURE] for v in chosen)  # vẫn có người chọn riêng ô loại trừ


def test_cac_cau_cung_thai_do_tuong_quan_duong() -> None:
    plain = _gen().generate(2000)
    responses = _gen(sample_logic()).generate(2000)
    assert abs(np.corrcoef(_num(plain, QUALITY), _num(plain, RECOMMEND))[0, 1]) < 0.1
    assert np.corrcoef(_num(responses, QUALITY), _num(responses, RECOMMEND))[0, 1] > 0.45
    assert np.corrcoef(_num(responses, QUALITY), _num(responses, TRUST))[0, 1] > 0.45


def test_do_dong_deu_cao_hon_thi_tuong_quan_cao_hon() -> None:
    corr = {
        c: np.corrcoef(_num(r, QUALITY), _num(r, RECOMMEND))[0, 1]
        for c in Consistency
        if (r := _gen(sample_logic(c)).generate(2000))
    }
    assert corr[Consistency.VARIED] < corr[Consistency.MODERATE] < corr[Consistency.UNIFORM]


def test_ty_le_giu_nguyen_khi_cac_cau_cung_kieu_ty_le() -> None:
    same = {"1": 5, "2": 10, "3": 20, "4": 40, "5": 25}
    rules = [*RULES[1:], *(QuestionRuleConfig(entry_id=e, question_type=5, weights=same) for e in (QUALITY, TRUST))]
    logic = sample_logic()
    logic.attitude_groups[0].items = [i for i in logic.attitude_groups[0].items if i.entry_id in (QUALITY, TRUST)]
    responses = SurveyDataGenerator(FORM, rules, None, seed=3, logic=logic).generate(4000)
    for entry in (QUALITY, TRUST):
        shares = np.bincount(_num(responses, entry).astype(int), minlength=6)[1:] / len(responses)
        assert shares == pytest.approx([0.05, 0.10, 0.20, 0.40, 0.25], abs=0.03)


def test_ty_le_rat_khac_nhau_chi_xe_dich_co_gioi_han() -> None:
    """QUALITY nghiêng 4–5, TRUST/RECOMMEND chia đều: giữ "sàn sàn" buộc kéo đuôi vào giữa một chút."""
    plain = _gen().generate(4000)
    responses = _gen(sample_logic()).generate(4000)
    before = np.bincount(_num(plain, QUALITY).astype(int), minlength=6)[1:] / 4000
    after = np.bincount(_num(responses, QUALITY).astype(int), minlength=6)[1:] / 4000
    assert np.abs(after - before).max() < 0.12
    assert abs(_num(responses, QUALITY).mean() - _num(plain, QUALITY).mean()) < 0.25


def test_tu_luan_chon_cau_mau_theo_thai_do() -> None:
    logic = sample_logic(text_attitudes=[TextAttitude(entry_id=COMMENT, group_id="brand", labels={
        POS: TextSentiment.POSITIVE, NEG: TextSentiment.NEGATIVE,
    })])
    responses = _gen(logic).generate(2000)
    quality = _num(responses, QUALITY)
    text = np.array([r.answers[COMMENT].values[0] for r in responses])
    assert quality[text == POS].mean() > quality[text == NEG].mean() + 0.8
    assert {POS, NEG, "Bình thường"} <= set(text)


def test_thong_ke_loc_dem_so_phan_hoi_da_sua() -> None:
    gen = _gen(sample_logic())
    gen.generate(500)
    stats = gen.filter_stats
    assert stats.generated >= 500 and stats.repaired > 0
    assert stats.by_kind["RULE"] > 0 and stats.by_key["age"] > 0


# ------------------------------------------------------------- nhóm SPSS
def _scale_group() -> SpssGroupConfig:
    return SpssGroupConfig(group_id="g", name="Nhóm", mean=3.8, std=0.8, alpha_target=0.8, entries=[QUALITY, TRUST])


def test_nhan_to_chung_khong_doi_tham_so_nhom() -> None:
    errors: list[str] = []
    plan = plan_group(_scale_group(), {q.entry_id: q for q in FORM.questions}, {}, errors)
    assert not errors
    rng = np.random.default_rng(0)
    base = sample_group_codes(plan, 30_000, rng)
    shared = sample_group_codes(plan, 30_000, rng, rng.standard_normal(30_000), 0.55)
    assert shared.mean() == pytest.approx(base.mean(), abs=0.03)
    assert shared.std() == pytest.approx(base.std(), abs=0.03)
    assert cronbach_alpha(shared) == pytest.approx(cronbach_alpha(base), abs=0.02)


def test_nhom_spss_gan_voi_thai_do_chung() -> None:
    responses = _gen(sample_logic(), groups=[_scale_group()]).generate(2000)
    group_mean = (_num(responses, QUALITY) + _num(responses, TRUST)) / 2
    assert np.corrcoef(group_mean, _num(responses, RECOMMEND))[0, 1] > 0.4


# ------------------------------------------------------------- review
def test_soat_mau_thu_khong_bao_xe_dich_o_loai_tru_va_dao_dong_ngau_nhien() -> None:
    from app.services.logic.review import review_logic

    result = review_logic(FORM, RULES, [], sample_logic(), n=300)
    assert result.ready and result.inconsistent_after == 0 and result.inconsistent_before > 0
    assert FEATURES not in {d.entry_id for d in result.drifts}
    assert AGE not in {d.entry_id for d in result.drifts}  # câu NẾU không bị sửa → chỉ dao động ngẫu nhiên
    [corr] = result.correlations
    assert corr.after > corr.before + 0.3
    assert result.sample is not None and result.sample.attitude


def test_soat_mau_thu_bao_alpha_nhom_spss_truoc_va_sau() -> None:
    from app.services.logic.review import review_logic

    result = review_logic(FORM, RULES, [_scale_group()], sample_logic(), n=400)
    [check] = result.spss_alpha
    assert check.group_id == "g" and check.target == 0.8
    assert check.before is not None and check.after is not None
    assert abs(check.before - 0.8) < 0.08  # cách cũ đạt gần mục tiêu
    assert check.after >= check.before - 0.02  # kéo câu lệch vào gần → không giảm


def test_soat_mau_thu_dem_cau_mau_chua_phan_loai() -> None:
    from app.services.logic.review import review_logic

    logic = sample_logic(text_attitudes=[TextAttitude(entry_id=COMMENT, group_id="brand", labels={POS: TextSentiment.POSITIVE})])
    assert review_logic(FORM, RULES, [], logic, n=60).unlabeled_texts == 2  # "Bình thường" và NEG chưa có nhãn


# ------------------------------------------------------------- BUG-017
def test_cau_bat_buoc_kieu_chua_ho_tro_chan_chay() -> None:
    from app.schemas.form_schema import UnsupportedItem
    from app.services.spss.validation import GeneratorConfigError

    form = FORM.model_copy(update={"unsupported_items": [
        UnsupportedItem(item_id=1, title="Tải CV lên", type_id=13, page_index=0, is_required=True),
        UnsupportedItem(item_id=2, title="Ảnh", type_id=13, page_index=0, is_required=False),
    ]})
    with pytest.raises(GeneratorConfigError) as info:
        SurveyDataGenerator(form, RULES).validate()
    assert any("Tải CV lên" in e for e in info.value.errors)
    assert not any("Ảnh" in e for e in info.value.errors)


def test_cau_danh_gia_sinh_va_gui_nhu_thang_do() -> None:
    from app.schemas.form_schema import QuestionType
    from app.services.spss.answers import build_payload_tuples
    from tests.unit.spss_factories import form as build_form
    from tests.unit.spss_factories import option, question, section

    rating = question("77", QuestionType.RATING, [option(str(i)) for i in range(1, 11)], required=True)
    structure = build_form([section(0, None)], [rating])
    rule = QuestionRuleConfig(entry_id="77", question_type=18, weights={str(i): (30 if i >= 8 else 2) for i in range(1, 11)})
    responses = SurveyDataGenerator(structure, [rule], seed=1).generate(300)
    values = [int(r.answers["77"].values[0]) for r in responses]
    assert np.mean([v >= 8 for v in values]) > 0.8
    assert ("entry.77", str(values[0])) in build_payload_tuples(responses[0], None)
    assert responses[0].answers["77"].numeric_value == float(values[0])
