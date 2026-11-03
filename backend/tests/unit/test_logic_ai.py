"""Lượt 1 bằng AI: mô tả form, làm sạch kết quả Gemini, phân loại câu tự luận, kiểm tra bản đồ."""

import json
from types import SimpleNamespace
from typing import Any

import pytest

from app.schemas.form_schema import QuestionType
from app.schemas.logic_schema import (
    AttitudeGroup,
    AttitudeItem,
    ExclusiveOption,
    LogicMap,
    LogicRule,
    LogicSource,
    RuleStrength,
    TextAttitude,
    TextSentiment,
    ThenOp,
)
from app.services.gemini_call import GeminiCallError
from app.services.logic.ai_reader import (
    AiAttitudeGroup,
    AiAttitudeItem,
    AiExclusive,
    AiLogicResponse,
    AiRule,
    AiTextLink,
    build_prompt,
    describe_form,
    read_form_logic,
    to_logic_map,
)
from app.services.logic.text_classifier import classify_texts
from app.services.logic.validation import LogicMapInvalidError, ensure_valid, validate_logic
from tests.unit.logic_factories import (
    ADS, AGE, COMMENT, FEATURES, FREQ, JOB, KNOW, NONE_FEATURE, QUALITY, RECOMMEND, STUDENT, TRUST, UNDER_18,
    sample_form,
)
from tests.unit.spss_factories import form, option, question, section

FORM = sample_form()


def _item(entry: str, positive: str) -> AiAttitudeItem:
    return AiAttitudeItem(entry_id=entry, most_positive_option=positive)


# ------------------------------------------------------------------ describe
def test_mo_ta_form_gom_entry_loai_va_lua_chon() -> None:
    text = describe_form(FORM)
    assert f"entry {AGE}" in text and f'"{UNDER_18}"' in text
    assert "CHECKBOX" in text and "chọn nhiều" in text
    assert "(+ ô Mục khác)" in text  # câu ADS có Mục khác
    assert f"entry {COMMENT}" in text and "tự luận" in text


def test_mo_ta_hang_ma_tran_kem_tieu_de_ma_tran() -> None:
    q = question("5", QuestionType.GRID, [option("1"), option("2")])
    q.grid_title, q.row_label = "Đánh giá Tiki", "Uy tín"
    assert "Đánh giá Tiki — hàng: Uy tín" in describe_form(form([section(0, None)], [q]))


def test_prompt_khong_chua_cau_tra_loi_chi_co_cau_hoi() -> None:
    prompt = build_prompt(FORM)
    assert "most_positive_option" in prompt and "FORM:" in prompt
    assert "Dưới 18" in prompt  # ví dụ ràng buộc tuổi–nghề


# ------------------------------------------------------------------ sanitize
def test_lam_sach_nhom_suy_ra_chieu_tu_lua_chon_tich_cuc() -> None:
    response = AiLogicResponse(attitude_groups=[AiAttitudeGroup(name="Thái độ", items=[
        _item(QUALITY, "5"), _item(TRUST, "5"), _item(FREQ, "Thường xuyên"),
    ])])
    logic = to_logic_map(response, FORM, "m")
    items = {i.entry_id: i.positive_high for i in logic.attitude_groups[0].items}
    assert items == {QUALITY: True, TRUST: True, FREQ: False}
    assert logic.source == LogicSource.AI and logic.model == "m" and logic.confirmed is False


@pytest.mark.parametrize(("positive", "kept"), [("Thỉnh thoảng", False), ("Không có", False), ("thường xuyên.", True)])
def test_lua_chon_tich_cuc_o_giua_hoac_khong_khop_bi_bo(positive: str, kept: bool) -> None:
    response = AiLogicResponse(attitude_groups=[AiAttitudeGroup(name="g", items=[_item(QUALITY, "5"), _item(FREQ, positive)])])
    logic = to_logic_map(response, FORM, None)
    entries = [i.entry_id for g in logic.attitude_groups for i in g.items]
    assert (FREQ in entries) is kept


def test_nhom_bo_cau_khong_hop_le_va_nhom_mot_cau() -> None:
    response = AiLogicResponse(attitude_groups=[
        AiAttitudeGroup(name="A", items=[_item(QUALITY, "5"), _item("999", "x"), _item(FEATURES, "Giá rẻ"), _item(COMMENT, "x")]),
        AiAttitudeGroup(name="B", items=[_item(TRUST, "5"), _item(QUALITY, "5")]),  # QUALITY trùng nhóm A
    ])
    logic = to_logic_map(response, FORM, None)
    assert logic.attitude_groups == []  # A còn 1 câu, B còn 1 câu → đều bị bỏ


def test_entry_co_tien_to_van_nhan() -> None:
    response = AiLogicResponse(attitude_groups=[AiAttitudeGroup(name="g", items=[_item(f"entry.{QUALITY}", "5"), _item(TRUST, "5")])])
    assert len(to_logic_map(response, FORM, None).attitude_groups[0].items) == 2


def test_lam_sach_rang_buoc_khop_gia_tri_khong_phan_biet_hoa_thuong() -> None:
    response = AiLogicResponse(rules=[AiRule(
        if_entry=AGE, if_values=["dưới 18"], then_entry=JOB, then_values=["HỌC SINH - SINH VIÊN"],
        strength="usually", reason="Tuổi đi học",
    )])
    [rule] = to_logic_map(response, FORM, None).rules
    assert rule.if_values == [UNDER_18] and rule.then_values == [STUDENT]
    assert rule.strength == RuleStrength.USUALLY and rule.then_op == ThenOp.IS and rule.rule_id == "r1"


@pytest.mark.parametrize("bad", [
    AiRule(if_entry="999", if_values=["x"], then_entry=JOB, then_values=[STUDENT]),
    AiRule(if_entry=AGE, if_values=["Không có"], then_entry=JOB, then_values=[STUDENT]),
    AiRule(if_entry=AGE, if_values=[UNDER_18], then_entry=JOB, then_values=["Phi hành gia"]),
    AiRule(if_entry=AGE, if_values=[UNDER_18], then_entry=AGE, then_values=[UNDER_18]),
    AiRule(if_entry=AGE, if_values=[UNDER_18], then_entry=COMMENT, then_values=["x"]),
    AiRule(if_entry=KNOW, if_values=["Không biết"], then_entry=JOB, then_op="IS_NOT",
           then_values=[STUDENT, "Nhân viên văn phòng", "Tự do"]),  # cấm hết đáp án
])
def test_rang_buoc_sai_bi_bo(bad: AiRule) -> None:
    assert to_logic_map(AiLogicResponse(rules=[bad]), FORM, None).rules == []


def test_o_loai_tru_chi_nhan_cau_hop_kiem() -> None:
    response = AiLogicResponse(exclusive_options=[
        AiExclusive(entry_id=FEATURES, value=NONE_FEATURE.upper()), AiExclusive(entry_id=FEATURES, value=NONE_FEATURE),
        AiExclusive(entry_id=AGE, value=UNDER_18), AiExclusive(entry_id=FEATURES, value="Không tồn tại"),
    ])
    assert to_logic_map(response, FORM, None).exclusive_options == [ExclusiveOption(entry_id=FEATURES, value=NONE_FEATURE)]


def test_tu_luan_gan_nhom_theo_ten_hoac_nhom_duy_nhat() -> None:
    response = AiLogicResponse(
        attitude_groups=[AiAttitudeGroup(name="Thái độ", items=[_item(QUALITY, "5"), _item(TRUST, "5")])],
        text_questions=[AiTextLink(entry_id=COMMENT, group_name="tên lạ"), AiTextLink(entry_id=AGE, group_name="Thái độ")],
    )
    assert to_logic_map(response, FORM, None).text_attitudes == [TextAttitude(entry_id=COMMENT, group_id="g1")]


async def test_doc_form_mot_lan_goi_gemini() -> None:
    payload = AiLogicResponse(attitude_groups=[AiAttitudeGroup(name="g", items=[_item(QUALITY, "5"), _item(RECOMMEND, "10")])])
    calls: list[str] = []

    async def generate_content(*, model: str, contents: str, config: Any) -> Any:
        calls.append(model)
        return SimpleNamespace(parsed=None, text=payload.model_dump_json(), model_version="gemini-x-flash")

    client = SimpleNamespace(aio=SimpleNamespace(models=SimpleNamespace(generate_content=generate_content)))
    logic = await read_form_logic(client, FORM, "gemini-flash-latest")
    assert calls == ["gemini-flash-latest"] and logic.model == "gemini-x-flash"
    assert [i.entry_id for i in logic.attitude_groups[0].items] == [QUALITY, RECOMMEND]


async def test_doc_form_ket_qua_hong_bao_loi_de_hieu() -> None:
    async def generate_content(**_: Any) -> Any:
        return SimpleNamespace(parsed=None, text="{không phải json")

    client = SimpleNamespace(aio=SimpleNamespace(models=SimpleNamespace(generate_content=generate_content)))
    with pytest.raises(GeminiCallError, match="không đúng định dạng"):
        await read_form_logic(client, FORM, "m")


# ------------------------------------------------------------------ text classifier
async def test_phan_loai_cau_tu_luan_thieu_nhan_la_trung_lap() -> None:
    texts = ["Rất tốt", "Tệ quá", "Bình thường", "Không rõ"]

    async def generate_content(*, model: str, contents: str, config: Any) -> Any:
        assert all(t in contents for t in texts)
        labels = [{"index": 0, "sentiment": "positive"}, {"index": 1, "sentiment": "NEGATIVE"},
                  {"index": 2, "sentiment": "lạ"}, {"index": 99, "sentiment": "POSITIVE"}]
        return SimpleNamespace(parsed=None, text=json.dumps({"labels": labels}))

    client = SimpleNamespace(aio=SimpleNamespace(models=SimpleNamespace(generate_content=generate_content)))
    labels = await classify_texts(client, "Góp ý?", "Tiki", texts, "m")
    assert labels == {"Rất tốt": TextSentiment.POSITIVE, "Tệ quá": TextSentiment.NEGATIVE,
                      "Bình thường": TextSentiment.NEUTRAL, "Không rõ": TextSentiment.NEUTRAL}


# ------------------------------------------------------------------ validation
def test_ban_do_hop_le_khong_loi() -> None:
    from tests.unit.logic_factories import sample_logic

    assert validate_logic(FORM, sample_logic()) == []


def test_ban_do_sua_tay_sai_liet_ke_tung_loi() -> None:
    logic = LogicMap(
        attitude_groups=[AttitudeGroup(group_id="g", name="G", items=[AttitudeItem(entry_id="999"), AttitudeItem(entry_id=FEATURES)])],
        rules=[LogicRule(rule_id="r", if_entry=AGE, if_values=["Già"], then_entry=JOB, then_values=[STUDENT]),
               LogicRule(rule_id="r2", if_entry="888", if_values=["x"], then_entry=JOB, then_values=[STUDENT])],
        exclusive_options=[ExclusiveOption(entry_id=AGE, value=UNDER_18), ExclusiveOption(entry_id=FEATURES, value="lạ")],
        text_attitudes=[TextAttitude(entry_id=ADS, group_id="g")],
    )
    errors = validate_logic(FORM, logic)
    assert len(errors) == 7
    with pytest.raises(LogicMapInvalidError) as info:
        ensure_valid(FORM, logic)
    assert info.value.errors == errors
