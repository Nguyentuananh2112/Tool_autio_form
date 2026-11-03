"""Form mẫu nhỏ có đủ các kiểu mâu thuẫn để test soát logic (ISS-008)."""

from __future__ import annotations

from app.schemas.form_schema import ParsedFormStructure, QuestionType
from app.schemas.logic_schema import (
    AttitudeGroup,
    AttitudeItem,
    Consistency,
    ExclusiveOption,
    LogicMap,
    LogicRule,
    RuleStrength,
    ThenOp,
)
from tests.unit.spss_factories import form, option, other_option, question, section

AGE, JOB, QUALITY, TRUST, RECOMMEND, FREQ, FEATURES, COMMENT, KNOW, ADS = (
    "11", "12", "21", "22", "23", "24", "31", "32", "41", "42",
)
SCALE5 = [str(i) for i in range(1, 6)]
SCALE10 = [str(i) for i in range(1, 11)]
UNDER_18 = "Dưới 18"
STUDENT = "Học sinh - sinh viên"
NONE_FEATURE = "Không có đặc điểm nổi bật nào"


def sample_form() -> ParsedFormStructure:
    questions = [
        question(AGE, QuestionType.MULTIPLE_CHOICE, [option(UNDER_18), option("18 - 25"), option("Trên 25")], required=True),
        question(JOB, QuestionType.MULTIPLE_CHOICE, [option(STUDENT), option("Nhân viên văn phòng"), option("Tự do")], required=True),
        question(QUALITY, QuestionType.LINEAR_SCALE, [option(v) for v in SCALE5], required=True),
        question(TRUST, QuestionType.LINEAR_SCALE, [option(v) for v in SCALE5], required=True),
        question(RECOMMEND, QuestionType.LINEAR_SCALE, [option(v) for v in SCALE10], required=True),
        # Câu chữ: đáp án ĐẦU là tích cực
        question(FREQ, QuestionType.MULTIPLE_CHOICE, [option("Thường xuyên"), option("Thỉnh thoảng"), option("Hiếm khi")], required=True),
        question(FEATURES, QuestionType.CHECKBOX, [option("Giá rẻ"), option("Giao nhanh"), option("Chính hãng"), option(NONE_FEATURE)], required=True),
        question(COMMENT, QuestionType.SHORT_ANSWER, [], required=True),
        question(KNOW, QuestionType.MULTIPLE_CHOICE, [option("Không biết"), option("Có biết")], required=True),
        question(ADS, QuestionType.MULTIPLE_CHOICE, [option("Luôn thấy"), option("Đôi khi"), option("Chưa thấy"), other_option()], required=True),
    ]
    return form([section(0, None)], questions)


def sample_logic(consistency: Consistency = Consistency.MODERATE, **extra) -> LogicMap:
    return LogicMap(
        attitude_groups=[AttitudeGroup(group_id="brand", name="Thái độ", items=[
            AttitudeItem(entry_id=QUALITY), AttitudeItem(entry_id=TRUST), AttitudeItem(entry_id=RECOMMEND),
            AttitudeItem(entry_id=FREQ, positive_high=False),
        ])],
        rules=[
            LogicRule(rule_id="age", if_entry=AGE, if_values=[UNDER_18], then_entry=JOB, then_values=[STUDENT]),
            LogicRule(rule_id="ads", if_entry=KNOW, if_values=["Không biết"], then_entry=ADS,
                      then_op=ThenOp.IS_NOT, then_values=["Luôn thấy"]),
        ],
        exclusive_options=[ExclusiveOption(entry_id=FEATURES, value=NONE_FEATURE)],
        consistency=consistency,
        **extra,
    )


def usually_rule() -> LogicRule:
    return LogicRule(rule_id="usual", if_entry=AGE, if_values=["Trên 25"], then_entry=JOB,
                     then_values=["Nhân viên văn phòng"], strength=RuleStrength.USUALLY)
