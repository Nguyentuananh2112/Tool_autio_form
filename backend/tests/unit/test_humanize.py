"""Câu trả lời tự luận gõ như người thật (app/services/humanize, SPEC-022)."""

import re
from collections import Counter

import numpy as np
import pytest

from app.services.gemini_service import AI_PHRASES, build_prompt
from app.services.humanize.ai_cleanup import clean_ai_text
from app.services.humanize.humanizer import humanize_answers, pick_style, style_text
from app.services.humanize.styles import STYLES, TypingStyle, style_weights
from app.services.humanize.vietnamese import abbreviate, add_typos, strip_diacritics
from app.services.spss.answers import ANSWER_KIND_TEXT, Answer

STYLE = {style.name: style for style in STYLES}
SENTENCE = "Giao hàng nhanh, đóng gói cẩn thận và sản phẩm chính hãng."


# ------------------------------------------------------------------ vietnamese
def test_bo_dau_ca_chu_d() -> None:
    assert strip_diacritics("Được rồi, đơn hàng ĐẸP quá") == "Duoc roi, don hang DEP qua"


def test_viet_tat_ca_tu_va_cum_tu() -> None:
    rng = np.random.default_rng(0)
    out = abbreviate("không biết mọi người thấy sản phẩm như thế nào", 1.0, rng)
    assert out.split()[0] in {"ko", "k", "hông", "khum"}
    assert "bít" in out and any(x in out for x in ("mn", "mng")) and "sp" in out and "ntn" in out


def test_viet_tat_khong_cat_giua_tu() -> None:
    rng = np.random.default_rng(0)
    assert abbreviate("không gian rộng", 1.0, rng).split()[1:] == ["gian", "rộng"]
    assert abbreviate("ngựa okapi", 1.0, rng) == "ngựa okapi"  # "ok" nằm trong từ khác → không đổi


def test_xac_suat_viet_tat_0_giu_nguyen() -> None:
    assert abbreviate(SENTENCE, 0.0, np.random.default_rng()) == SENTENCE


def test_loi_go_it_va_khong_dung_chu_cai_dau() -> None:
    rng = np.random.default_rng(1)
    text = "giao hàng nhanh đóng gói cẩn thận sản phẩm chính hãng"
    changed = 0
    for _ in range(300):
        out = add_typos(text, 0.02, rng)
        for before, after in zip(text.split(), out.split()):
            if before != after:
                changed += 1
                assert strip_diacritics(after[0]).lower() == strip_diacritics(before[0]).lower()
    assert 0 < changed < 300 * 9 * 0.05  # khoảng 2% số từ


def test_tu_ngan_khong_bi_go_sai() -> None:
    assert add_typos("ok k j", 1.0, np.random.default_rng()) == "ok k j"


# ------------------------------------------------------------------ styles
def test_ty_le_kieu_go_cong_lai_bang_1_va_on_dinh() -> None:
    assert sum(style_weights()) == pytest.approx(1.0)
    rng = np.random.default_rng(2)
    counts = Counter(pick_style(rng).name for _ in range(20_000))
    for style, weight in zip(STYLES, style_weights()):
        assert counts[style.name] / 20_000 == pytest.approx(weight, abs=0.015)


def test_kieu_khong_dau_khong_con_dau() -> None:
    rng = np.random.default_rng(3)
    for _ in range(50):
        out = style_text(SENTENCE, STYLE["NO_DIACRITICS"], rng)
        assert out == strip_diacritics(out)


def test_kieu_teen_viet_thuong_va_khong_cham_cuoi() -> None:
    rng = np.random.default_rng(4)
    for _ in range(50):
        out = style_text("Rất THÍCH Tiki.", STYLE["TEEN"], rng)
        assert out == out.lower() and not out.endswith(".")


def test_kieu_luoi_hay_chi_go_ve_dau() -> None:
    rng = np.random.default_rng(5)
    outs = [style_text(SENTENCE, STYLE["LAZY"], rng) for _ in range(200)]
    assert sum(1 for o in outs if len(o.split()) <= 4) > 60
    assert all(len(o.split()) >= 2 for o in outs)


def test_kieu_can_than_phan_lon_viet_hoa_dau_cau() -> None:
    rng = np.random.default_rng(6)
    outs = [style_text("giá hơi cao", STYLE["CAREFUL"], rng) for _ in range(400)]
    assert 0.75 < np.mean([o[0].isupper() for o in outs]) < 0.95
    assert 0.3 < np.mean([o.endswith(".") for o in outs]) < 0.6


def test_khong_kieu_nao_giong_ai_hoan_hao() -> None:
    """Người thật đa dạng: trong 1000 người, câu chuẩn chỉnh như AI (hoa đầu + chấm cuối + đủ dấu phẩy) là thiểu số."""
    rng = np.random.default_rng(7)
    outs = [style_text(SENTENCE, pick_style(rng), rng) for _ in range(1000)]
    perfect = sum(1 for o in outs if o == SENTENCE)
    assert perfect < 120
    assert len(set(outs)) > 60  # một câu 10 từ cho ~100 biến thể thật: hoa/thường, dấu câu, viết tắt, không dấu, lỗi gõ
    assert np.mean([o[0].islower() for o in outs]) > 0.5  # đa số không viết hoa đầu câu


def test_cau_rong_giu_nguyen() -> None:
    assert style_text("   ", STYLE["CASUAL"], np.random.default_rng()) == "   "


# ------------------------------------------------------------------ humanize_answers
def test_moi_nguoi_mot_kieu_go_cho_moi_cau_tu_luan() -> None:
    answers = {
        "1": Answer(values=["Giao hàng rất nhanh."], kind=ANSWER_KIND_TEXT),
        "2": Answer(values=["Đóng gói đẹp và chắc chắn."], kind=ANSWER_KIND_TEXT),
        "3": Answer(values=["Nam"], numeric_value=1.0),  # câu lựa chọn: không đụng tới
        "4": Answer(values=["__other_option__"], other_text="Bạn bè giới thiệu cho mình"),
    }
    seen_no_diacritics = False
    rng = np.random.default_rng(8)
    for _ in range(80):
        copy = {k: Answer(values=list(v.values), kind=v.kind, other_text=v.other_text, numeric_value=v.numeric_value) for k, v in answers.items()}
        style = humanize_answers(copy, rng)
        assert copy["3"].values == ["Nam"] and copy["3"].numeric_value == 1.0
        if style.strip_diacritics:
            seen_no_diacritics = True
            texts = [copy["1"].values[0], copy["2"].values[0], copy["4"].other_text]
            assert all(t == strip_diacritics(t) for t in texts)  # cùng một người → mọi câu đều không dấu
    assert seen_no_diacritics


def test_cung_seed_cung_ket_qua_de_gui_lai_dung_cau_cu() -> None:
    def run() -> list[str]:
        rng = np.random.default_rng(42)
        outs = []
        for _ in range(30):
            answers = {"1": Answer(values=[SENTENCE], kind=ANSWER_KIND_TEXT)}
            humanize_answers(answers, rng)
            outs.append(answers["1"].values[0])
        return outs

    assert run() == run()


def test_bo_sinh_bat_nhan_hoa_moi_doi_cau_tu_luan() -> None:
    from app.schemas.campaign_schema import QuestionRuleConfig
    from app.schemas.form_schema import QuestionType
    from app.services.spss.generator import SurveyDataGenerator
    from tests.unit.spss_factories import form, question, section

    structure = form([section(0, None)], [question("9", QuestionType.SHORT_ANSWER, [], required=True)])
    rules = [QuestionRuleConfig(entry_id="9", question_type=0, text_pool=[SENTENCE])]
    plain = SurveyDataGenerator(structure, rules, seed=1).generate(50)
    human = SurveyDataGenerator(structure, rules, seed=1, humanize=True).generate(50)
    assert {r.answers["9"].values[0] for r in plain} == {SENTENCE}
    assert len({r.answers["9"].values[0] for r in human}) > 10


# ------------------------------------------------------------------ ai_cleanup + prompt
@pytest.mark.parametrize(("raw", "expected"), [
    ("- Giao hàng nhanh", "Giao hàng nhanh"),
    ("1. Giảm phí ship", "Giảm phí ship"),
    ('"Đóng gói cẩn thận hơn"', "Đóng gói cẩn thận hơn"),
    ("Theo tôi, Tiki nên giảm giá sách", "Tiki nên giảm giá sách"),
    ("Tôi nghĩ rằng cần thêm mã giảm giá", "Cần thêm mã giảm giá"),
    ("Giao nhanh — nhưng đóng gói ẩu", "Giao nhanh, nhưng đóng gói ẩu"),
    ("Theo tôi, ok", "Theo tôi, ok"),  # còn quá ít nội dung thì giữ nguyên
    ("  nhiều   khoảng   trắng ", "nhiều khoảng trắng"),
])
def test_go_dau_vet_ai(raw: str, expected: str) -> None:
    assert clean_ai_text(raw) == expected


def test_cau_lenh_yeu_cau_nhieu_nguoi_that_va_cam_van_ai() -> None:
    prompt = build_prompt("Tiki cần cải thiện gì?", "Khảo sát Tiki", 20, "người Việt bình thường", ["câu cũ"])
    assert "20 NGƯỜI KHÁC NHAU" in prompt and "1–5 từ" in prompt and "không có ý kiến" in prompt
    assert "TUYỆT ĐỐI KHÔNG" in prompt and "KHÔNG chép lại nguyên văn" in prompt
    assert all(phrase in prompt for phrase in AI_PHRASES)
    assert "câu cũ" in prompt
    assert not re.search(r"\n\s*\n\s*\n", prompt)


def test_kieu_go_tuy_bien_duoc() -> None:
    plain = TypingStyle("X", 1.0, capitalize_start=1.0, final_period=1.0, drop_commas=0.0, abbreviate=0.0, typo_per_word=0.0)
    assert style_text("giao nhanh, gói đẹp", plain, np.random.default_rng()) == "Giao nhanh, gói đẹp."
