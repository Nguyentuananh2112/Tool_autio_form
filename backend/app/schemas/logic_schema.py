"""Bản đồ logic của form (quy tắc 6 CLAUDE.md, SPEC-020): câu nào phải trả lời khớp nhau.

Lượt 1 (AI đọc toàn bộ câu hỏi) tạo ra `LogicMap`; người dùng xem/sửa ở màn "Soát logic";
bộ sinh dùng nó để mỗi người điền nhất quán, bộ soát dùng nó để loại phản hồi mâu thuẫn.
"""

from __future__ import annotations

from enum import StrEnum

from typing import Annotated

from pydantic import AfterValidator, BaseModel, Field, model_validator

from app.schemas.common import UtcDateTime


def _clean_entry(value: str) -> str:
    cleaned = value.strip().removeprefix("entry.")
    if not cleaned.isdigit():
        raise ValueError("entry_id chỉ gồm phần số, VD '123456789'")
    return cleaned


EntryId = Annotated[str, AfterValidator(_clean_entry)]


class Consistency(StrEnum):
    """Độ đồng đều giữa các câu đánh giá của CÙNG một người."""

    VARIED = "VARIED"  # đa dạng
    MODERATE = "MODERATE"  # vừa phải (mặc định, đã chốt với người dùng)
    UNIFORM = "UNIFORM"  # rất đồng đều


class LogicSource(StrEnum):
    AI = "AI"
    MANUAL = "MANUAL"
    DEMO = "DEMO"  # bản đồ dựng sẵn cho form tập dùng (không cần AI)


class AttitudeItem(BaseModel):
    entry_id: EntryId
    # True: đáp án CUỐI danh sách là tích cực nhất (VD thang 1–5); False: đáp án ĐẦU là tích cực ("Rất nhất quán")
    positive_high: bool = True


class AttitudeGroup(BaseModel):
    group_id: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=255)
    items: list[AttitudeItem] = Field(min_length=1)

    @model_validator(mode="after")
    def _unique(self) -> AttitudeGroup:
        ids = [item.entry_id for item in self.items]
        if len(set(ids)) != len(ids):
            raise ValueError(f"Nhóm '{self.name}': một câu xuất hiện nhiều lần")
        return self


class ThenOp(StrEnum):
    IS = "IS"  # câu sau PHẢI là một trong then_values
    IS_NOT = "IS_NOT"  # câu sau KHÔNG được là then_values


class RuleStrength(StrEnum):
    ALWAYS = "ALWAYS"  # vi phạm = mâu thuẫn, luôn sinh lại
    USUALLY = "USUALLY"  # phần lớn tuân theo (USUALLY_RATE), vẫn có ngoại lệ tự nhiên


USUALLY_RATE = 0.75


class LogicRule(BaseModel):
    rule_id: str = Field(min_length=1, max_length=64)
    if_entry: EntryId
    if_values: list[str] = Field(min_length=1)
    then_entry: EntryId
    then_op: ThenOp = ThenOp.IS
    then_values: list[str] = Field(min_length=1)
    strength: RuleStrength = RuleStrength.ALWAYS
    reason: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def _distinct(self) -> LogicRule:
        if self.if_entry == self.then_entry:
            raise ValueError("Ràng buộc phải nối hai câu khác nhau")
        return self


class ExclusiveOption(BaseModel):
    """Ô hộp kiểm không được chọn kèm ô khác (VD "Không có đặc điểm nổi bật nào")."""

    entry_id: EntryId
    value: str = Field(min_length=1)


class TextSentiment(StrEnum):
    POSITIVE = "POSITIVE"
    NEUTRAL = "NEUTRAL"
    NEGATIVE = "NEGATIVE"


class TextAttitude(BaseModel):
    """Câu tự luận chọn câu mẫu theo thái độ của người điền trong nhóm `group_id`."""

    entry_id: EntryId
    group_id: str
    # câu mẫu → cảm xúc (do AI phân loại); câu không có trong đây coi là trung lập
    labels: dict[str, TextSentiment] = Field(default_factory=dict)


class LogicMap(BaseModel):
    version: int = 1
    attitude_groups: list[AttitudeGroup] = Field(default_factory=list)
    rules: list[LogicRule] = Field(default_factory=list)
    exclusive_options: list[ExclusiveOption] = Field(default_factory=list)
    text_attitudes: list[TextAttitude] = Field(default_factory=list)
    consistency: Consistency = Consistency.MODERATE
    source: LogicSource = LogicSource.AI
    model: str | None = None
    analyzed_at: UtcDateTime | None = None
    # Người dùng đã bấm "Xác nhận" ở màn Soát logic → được phép chạy
    confirmed: bool = False

    @model_validator(mode="after")
    def _check(self) -> LogicMap:
        group_ids = [group.group_id for group in self.attitude_groups]
        if len(set(group_ids)) != len(group_ids):
            raise ValueError("Trùng group_id trong nhóm thái độ")
        seen: set[str] = set()
        for group in self.attitude_groups:
            for item in group.items:
                if item.entry_id in seen:
                    raise ValueError(f"Câu {item.entry_id} thuộc nhiều nhóm thái độ")
                seen.add(item.entry_id)
        for text in self.text_attitudes:
            if text.group_id not in group_ids:
                raise ValueError(f"Câu tự luận {text.entry_id} gắn với nhóm không tồn tại '{text.group_id}'")
        return self

    def group_of(self, entry_id: str) -> tuple[AttitudeGroup, AttitudeItem] | None:
        for group in self.attitude_groups:
            for item in group.items:
                if item.entry_id == entry_id:
                    return group, item
        return None
