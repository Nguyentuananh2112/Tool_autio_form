"""Lượt 1: Gemini đọc TOÀN BỘ câu hỏi của form → bản đồ logic (SPEC-020).

Chỉ gửi nội dung câu hỏi và các lựa chọn (không gửi câu trả lời hay dữ liệu người dùng).
Kết quả AI luôn được làm sạch: câu/đáp án không có trong form bị bỏ, để bộ sinh không bao giờ
nhận một ràng buộc trỏ vào thứ không tồn tại.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field, ValidationError

from app.schemas.form_schema import ParsedFormStructure, ParsedQuestion
from app.schemas.logic_schema import (
    AttitudeGroup,
    AttitudeItem,
    ExclusiveOption,
    LogicMap,
    LogicRule,
    LogicSource,
    RuleStrength,
    TextAttitude,
    ThenOp,
)
from app.services.answer_coercion import normalize
from app.services.gemini_call import GeminiCallError as GeminiServiceError
from app.services.gemini_call import generate_json

MIN_GROUP_ITEMS = 2


# ---------------------------------------------------------------- AI response
class AiAttitudeItem(BaseModel):
    entry_id: str
    # Chép nguyên văn lựa chọn TÍCH CỰC NHẤT — app tự suy ra chiều (AI hay nhầm khi trả true/false)
    most_positive_option: str


class AiAttitudeGroup(BaseModel):
    name: str
    items: list[AiAttitudeItem] = Field(default_factory=list)


class AiRule(BaseModel):
    if_entry: str
    if_values: list[str] = Field(default_factory=list)
    then_entry: str
    then_op: str = "IS"
    then_values: list[str] = Field(default_factory=list)
    strength: str = "ALWAYS"
    reason: str = ""


class AiExclusive(BaseModel):
    entry_id: str
    value: str


class AiTextLink(BaseModel):
    entry_id: str
    group_name: str


class AiLogicResponse(BaseModel):
    attitude_groups: list[AiAttitudeGroup] = Field(default_factory=list)
    rules: list[AiRule] = Field(default_factory=list)
    exclusive_options: list[AiExclusive] = Field(default_factory=list)
    text_questions: list[AiTextLink] = Field(default_factory=list)


# --------------------------------------------------------------------- prompt
def _question_title(question: ParsedQuestion) -> str:
    if question.row_label:
        return f"{question.grid_title or question.title} — hàng: {question.row_label}"
    return question.title


def describe_form(structure: ParsedFormStructure) -> str:
    lines = [f'Tiêu đề form: "{structure.title}"']
    if structure.description:
        lines.append(f'Mô tả: "{structure.description[:500]}"')
    for question in structure.questions:
        flags = [f"trang {question.page_index + 1}", question.type_name]
        if question.is_multi_select:
            flags.append("chọn nhiều")
        options = " | ".join(f'"{o.value}"' for o in question.choice_options)
        extra = " (+ ô Mục khác)" if question.has_other else ""
        scale = ""
        if question.scale_low_label or question.scale_high_label:
            scale = f' [đầu thấp: "{question.scale_low_label or ""}", đầu cao: "{question.scale_high_label or ""}"]'
        lines.append(
            f'- entry {question.entry_id} ({", ".join(flags)}) "{_question_title(question)}"{scale}'
            + (f"\n  lựa chọn: {options}{extra}" if options else " — tự luận")
        )
    return "\n".join(lines)


INSTRUCTIONS = """Bạn là chuyên gia thiết kế bảng hỏi. Đọc TOÀN BỘ form dưới đây và tìm những chỗ
câu trả lời của CÙNG MỘT người phải khớp nhau, để dữ liệu sinh ra không mâu thuẫn.

1) attitude_groups — câu đo thái độ / đánh giá / mức độ gắn bó với CÙNG MỘT đối tượng (VD một thương hiệu):
   người có thái độ tốt sẽ chọn phía tích cực ở TẤT CẢ các câu đó.
   - GỘP vào MỘT nhóm mọi câu đánh giá cùng đối tượng: mọi hàng của các ma trận đánh giá, thang điểm 1–5 / 1–10
     (hài lòng, tin tưởng, sẵn lòng giới thiệu…), câu mức độ nhận biết / nhận diện, tần suất sử dụng,
     câu có thứ bậc kiểu "Rất… → Không…", "Thường xuyên → Hiếm khi", "Luôn → Không bao giờ".
     Chỉ tách nhóm khi đối tượng khác hẳn nhau (VD hai thương hiệu khác nhau).
   - most_positive_option: CHÉP NGUYÊN VĂN lựa chọn thể hiện thái độ TÍCH CỰC NHẤT với đối tượng
     (VD "Rất nhất quán", "Hoàn toàn có thể nhận diện", "Thường xuyên", "5", "10"). Câu đo điều tiêu cực
     (VD "mức độ cần thay đổi hình ảnh", "tin đồn làm giảm niềm tin") thì lựa chọn tích cực nhất là phía ÍT tiêu cực.
   - KHÔNG đưa vào: nhân khẩu học, câu chọn tên/đối tượng (không có thứ bậc), câu hộp kiểm, câu tự luận.
2) rules — ràng buộc NẾU câu A chọn X THÌ câu B (IS: phải là / IS_NOT: không được là) một trong các giá trị.
   Kiểm tra KỸ từng cặp sau và tạo ràng buộc nếu có:
   - Nhân khẩu học: tuổi ↔ nghề nghiệp / thu nhập / học vấn / tình trạng hôn nhân
     (VD "Dưới 18" THÌ nghề IS "Học sinh - sinh viên").
   - Nhận biết ↔ trải nghiệm: chưa biết / không nhận diện được đối tượng THÌ IS_NOT các lựa chọn
     "luôn nhận ra", "thấy thường xuyên", "đã dùng nhiều"…
   - Lựa chọn ↔ lựa chọn: VD thương hiệu nghĩ đến đầu tiên thường cũng là thương hiệu hay dùng (USUALLY).
   - ALWAYS: vi phạm là vô lý với người thật. USUALLY: thường đúng nhưng có ngoại lệ.
   - Không tạo ràng buộc giữa hai câu đã cùng một nhóm thái độ.
3) exclusive_options — trong câu hộp kiểm (chọn nhiều), ô không thể chọn kèm ô khác
   (VD "Không có đặc điểm nào", "Không biết", "Chưa từng sử dụng").
4) text_questions — câu tự luận hỏi cảm nhận / ấn tượng / góp ý về đối tượng của một nhóm thái độ (group_name = tên nhóm).

Mọi giá trị lựa chọn phải CHÉP NGUYÊN VĂN từ danh sách lựa chọn (giữ dấu tiếng Việt). entry_id chỉ gồm chữ số.
Tên nhóm và lý do viết tiếng Việt có dấu.
"""


def build_prompt(structure: ParsedFormStructure) -> str:
    return f"{INSTRUCTIONS}\nFORM:\n{describe_form(structure)}"


# ------------------------------------------------------------------ sanitize
def _match_value(question: ParsedQuestion, raw: str) -> str | None:
    for option in question.options:
        if raw == option.value:
            return option.value
    wanted = normalize(raw)
    for option in question.options:
        if wanted in (normalize(option.value), normalize(option.label)):
            return option.value
    loose = normalize(raw, strip_accents=True)
    for option in question.options:
        if loose == normalize(option.label, strip_accents=True):
            return option.value
    return None


def _match_values(question: ParsedQuestion, raws: list[str]) -> list[str]:
    matched = [value for raw in raws if (value := _match_value(question, raw)) is not None]
    return list(dict.fromkeys(matched))


def _positive_high(question: ParsedQuestion, most_positive: str) -> bool | None:
    """Lựa chọn tích cực nhất nằm nửa sau danh sách → chiều tăng dần; nửa đầu → giảm dần."""
    value = _match_value(question, most_positive)
    values = [option.value for option in question.choice_options]
    if value not in values:
        return None
    index = values.index(value)
    if len(values) % 2 == 1 and index == len(values) // 2:
        return None  # chọn đúng mức giữa: không suy ra được chiều
    return index >= len(values) / 2


def _entry(raw: str) -> str:
    return raw.strip().removeprefix("entry.").removeprefix("entry ").strip()


def to_logic_map(response: AiLogicResponse, structure: ParsedFormStructure, model: str | None) -> LogicMap:
    questions = {q.entry_id: q for q in structure.questions}
    groups: list[AttitudeGroup] = []
    used: set[str] = set()
    for ai_group in response.attitude_groups:
        items = []
        for ai_item in ai_group.items:
            entry = _entry(ai_item.entry_id)
            question = questions.get(entry)
            if question is None or entry in used or not question.is_single_choice or len(question.choice_options) < 2:
                continue
            positive_high = _positive_high(question, ai_item.most_positive_option)
            if positive_high is None:
                continue
            used.add(entry)
            items.append(AttitudeItem(entry_id=entry, positive_high=positive_high))
        if len(items) >= MIN_GROUP_ITEMS:
            name = ai_group.name.strip()[:255] or f"Nhóm {len(groups) + 1}"
            groups.append(AttitudeGroup(group_id=f"g{len(groups) + 1}", name=name, items=items))

    rules: list[LogicRule] = []
    for ai_rule in response.rules:
        if_q, then_q = questions.get(_entry(ai_rule.if_entry)), questions.get(_entry(ai_rule.then_entry))
        if if_q is None or then_q is None or if_q.entry_id == then_q.entry_id or not if_q.options or not then_q.options:
            continue
        if_values, then_values = _match_values(if_q, ai_rule.if_values), _match_values(then_q, ai_rule.then_values)
        op = ThenOp.IS_NOT if ai_rule.then_op.strip().upper() == "IS_NOT" else ThenOp.IS
        if not if_values or not then_values:
            continue
        if op == ThenOp.IS_NOT and len(then_values) >= len(then_q.choice_options):
            continue  # cấm hết mọi đáp án → không thể thoả
        rules.append(LogicRule(
            rule_id=f"r{len(rules) + 1}", if_entry=if_q.entry_id, if_values=if_values, then_entry=then_q.entry_id,
            then_op=op, then_values=then_values,
            strength=RuleStrength.USUALLY if ai_rule.strength.strip().upper() == "USUALLY" else RuleStrength.ALWAYS,
            reason=ai_rule.reason.strip()[:500] or None,
        ))

    exclusive: list[ExclusiveOption] = []
    for ai_option in response.exclusive_options:
        question = questions.get(_entry(ai_option.entry_id))
        if question is None or not question.is_multi_select or len(question.options) < 2:
            continue
        value = _match_value(question, ai_option.value)
        if value is not None and not any(e.entry_id == question.entry_id and e.value == value for e in exclusive):
            exclusive.append(ExclusiveOption(entry_id=question.entry_id, value=value))

    by_name = {normalize(group.name): group.group_id for group in groups}
    texts: list[TextAttitude] = []
    for link in response.text_questions:
        question = questions.get(_entry(link.entry_id))
        group_id = by_name.get(normalize(link.group_name)) or (groups[0].group_id if len(groups) == 1 else None)
        if question is not None and question.is_text and group_id and all(t.entry_id != question.entry_id for t in texts):
            texts.append(TextAttitude(entry_id=question.entry_id, group_id=group_id))

    return LogicMap(
        attitude_groups=groups, rules=rules, exclusive_options=exclusive, text_attitudes=texts,
        source=LogicSource.AI, model=model, analyzed_at=datetime.now(UTC), confirmed=False,
    )


# --------------------------------------------------------------------- call
def _parse(response: Any) -> AiLogicResponse:
    parsed = getattr(response, "parsed", None)
    try:
        if isinstance(parsed, AiLogicResponse):
            return parsed
        if isinstance(parsed, dict):
            return AiLogicResponse.model_validate(parsed)
        text = getattr(response, "text", None)
        if text:
            return AiLogicResponse.model_validate(json.loads(text))
    except (ValidationError, json.JSONDecodeError) as exc:
        raise GeminiServiceError(f"Gemini trả về bản đồ logic không đúng định dạng: {exc}") from exc
    raise GeminiServiceError("Gemini không trả về bản đồ logic.")


async def read_form_logic(client: Any, structure: ParsedFormStructure, model: str) -> LogicMap:
    """Một lần gọi Gemini cho cả form. Lỗi giữ mã HTTP để chuỗi key chuyển key khi hết lượt."""
    response = await generate_json(client, model, build_prompt(structure), AiLogicResponse, temperature=0.2)
    used_model = getattr(response, "model_version", None) or model
    return to_logic_map(_parse(response), structure, used_model if isinstance(used_model, str) else model)
