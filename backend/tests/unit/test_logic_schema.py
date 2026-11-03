"""Kiểm tra bản đồ logic (app/schemas/logic_schema.py)."""

import pytest
from pydantic import ValidationError

from app.schemas.logic_schema import (
    AttitudeGroup,
    AttitudeItem,
    Consistency,
    ExclusiveOption,
    LogicMap,
    LogicRule,
    LogicSource,
    RuleStrength,
    TextAttitude,
    ThenOp,
)


def _group(group_id: str = "g", *entries: str) -> AttitudeGroup:
    return AttitudeGroup(group_id=group_id, name=group_id, items=[AttitudeItem(entry_id=e) for e in entries or ("1",)])


def test_mac_dinh_vua_phai_ai_chua_xac_nhan() -> None:
    logic = LogicMap()
    assert logic.consistency == Consistency.MODERATE
    assert logic.source == LogicSource.AI and logic.confirmed is False
    assert logic.attitude_groups == [] and logic.rules == []


@pytest.mark.parametrize("raw", ["entry.123", " 123 ", "123"])
def test_entry_id_bo_tien_to(raw: str) -> None:
    assert AttitudeItem(entry_id=raw).entry_id == "123"
    assert ExclusiveOption(entry_id=raw, value="x").entry_id == "123"


@pytest.mark.parametrize("raw", ["abc", "", "12a"])
def test_entry_id_khong_phai_so_bi_tu_choi(raw: str) -> None:
    with pytest.raises(ValidationError):
        AttitudeItem(entry_id=raw)


def test_rule_mac_dinh_la_luon_va_bat_buoc() -> None:
    rule = LogicRule(rule_id="r", if_entry="1", if_values=["a"], then_entry="2", then_values=["b"])
    assert rule.then_op == ThenOp.IS and rule.strength == RuleStrength.ALWAYS


def test_rule_cung_mot_cau_bi_tu_choi() -> None:
    with pytest.raises(ValidationError, match="hai câu khác nhau"):
        LogicRule(rule_id="r", if_entry="1", if_values=["a"], then_entry="entry.1", then_values=["b"])


@pytest.mark.parametrize("field", ["if_values", "then_values"])
def test_rule_can_it_nhat_mot_gia_tri(field: str) -> None:
    data = {"rule_id": "r", "if_entry": "1", "if_values": ["a"], "then_entry": "2", "then_values": ["b"], field: []}
    with pytest.raises(ValidationError):
        LogicRule(**data)


def test_nhom_trung_cau_bi_tu_choi() -> None:
    with pytest.raises(ValidationError, match="nhiều lần"):
        AttitudeGroup(group_id="g", name="g", items=[AttitudeItem(entry_id="1"), AttitudeItem(entry_id="1")])


def test_nhom_rong_bi_tu_choi() -> None:
    with pytest.raises(ValidationError):
        AttitudeGroup(group_id="g", name="g", items=[])


def test_mot_cau_thuoc_hai_nhom_bi_tu_choi() -> None:
    with pytest.raises(ValidationError, match="nhiều nhóm"):
        LogicMap(attitude_groups=[_group("a", "1"), _group("b", "1")])


def test_trung_group_id_bi_tu_choi() -> None:
    with pytest.raises(ValidationError, match="Trùng group_id"):
        LogicMap(attitude_groups=[_group("a", "1"), _group("a", "2")])


def test_tu_luan_gan_nhom_khong_ton_tai_bi_tu_choi() -> None:
    with pytest.raises(ValidationError, match="không tồn tại"):
        LogicMap(attitude_groups=[_group("a", "1")], text_attitudes=[TextAttitude(entry_id="5", group_id="zzz")])


def test_group_of_tim_dung_nhom_va_chieu() -> None:
    logic = LogicMap(attitude_groups=[
        AttitudeGroup(group_id="a", name="a", items=[AttitudeItem(entry_id="1"), AttitudeItem(entry_id="2", positive_high=False)]),
    ])
    group, item = logic.group_of("2")
    assert group.group_id == "a" and item.positive_high is False
    assert logic.group_of("9") is None


def test_round_trip_json() -> None:
    logic = LogicMap(attitude_groups=[_group("a", "1", "2")],
                     rules=[LogicRule(rule_id="r", if_entry="1", if_values=["x"], then_entry="2", then_values=["y"])],
                     consistency=Consistency.UNIFORM, confirmed=True)
    assert LogicMap.model_validate_json(logic.model_dump_json()) == logic
