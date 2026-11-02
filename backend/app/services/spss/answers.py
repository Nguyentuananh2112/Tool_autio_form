"""Kiểu dữ liệu đầu ra của bộ sinh: một câu trả lời, một phản hồi, và cách đóng gói payload."""

from __future__ import annotations

from dataclasses import dataclass, field

ANSWER_KIND_CHOICE = "CHOICE"
ANSWER_KIND_TEXT = "TEXT"
ANSWER_KIND_DATE = "DATE"
ANSWER_KIND_TIME = "TIME"


@dataclass(slots=True)
class Answer:
    values: list[str]
    other_text: str | None = None
    kind: str = ANSWER_KIND_CHOICE
    # Mã số phục vụ xuất SPSS (Likert = điểm, trắc nghiệm = thứ tự lựa chọn từ 1)
    numeric_value: float | None = None


@dataclass(slots=True)
class GeneratedResponse:
    sequence_number: int
    answers: dict[str, Answer]
    page_history: list[int] = field(default_factory=lambda: [0])

    @property
    def page_history_str(self) -> str:
        return ",".join(map(str, self.page_history))


def build_payload_tuples(response: GeneratedResponse, fbzx: str | None) -> list[tuple[str, str]]:
    """Đóng gói thành list[tuple] cho POST /formResponse (Mục 5.4.A)."""
    payload: list[tuple[str, str]] = []
    for entry_id, answer in response.answers.items():
        key = f"entry.{entry_id}"
        if answer.kind == ANSWER_KIND_DATE:
            year, month, day = answer.values[0].split("-")
            payload.extend(
                [(f"{key}_year", str(int(year))), (f"{key}_month", str(int(month))), (f"{key}_day", str(int(day)))]
            )
            continue
        if answer.kind == ANSWER_KIND_TIME:
            hour, minute = answer.values[0].split(":")[:2]
            payload.extend([(f"{key}_hour", hour.zfill(2)), (f"{key}_minute", minute.zfill(2))])
            continue
        for value in answer.values:
            payload.append((key, value))
        if answer.other_text is not None:
            payload.append((f"{key}.other_option_response", answer.other_text))
    payload.append(("fvv", "1"))
    payload.append(("pageHistory", response.page_history_str))
    if fbzx:
        payload.append(("fbzx", fbzx))
    return payload
