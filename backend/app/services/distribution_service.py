"""Phân phối đáp án đã gửi so với tỷ lệ mục tiêu (biểu đồ ở màn hình Giám sát chiến dịch)."""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence

from pydantic import BaseModel

from app.models import QuestionRule, SubmissionLog
from app.schemas.campaign_schema import QuestionRuleConfig
from app.schemas.form_schema import ParsedFormStructure, ParsedQuestion
from app.services.spss.validation import default_checkbox_probability


class OptionDistribution(BaseModel):
    label: str
    sent_count: int
    sent_pct: float
    target_pct: float | None


class QuestionDistribution(BaseModel):
    entry_id: str
    title: str
    answered: int
    options: list[OptionDistribution]


def _rule_config(rule: QuestionRule | None) -> QuestionRuleConfig | None:
    if rule is None:
        return None
    try:
        return QuestionRuleConfig.model_validate(
            {**rule.config_json, "entry_id": rule.entry_id, "question_type": rule.question_type}
        )
    except ValueError:
        return None


def _targets(question: ParsedQuestion, rule: QuestionRule | None) -> dict[str, float] | None:
    weights = (rule.config_json.get("weights") if rule else None) or {}
    if question.is_multi_select:
        # Hộp kiểm: xác suất độc lập từng ô ("Mục khác" 0%); mặc định giống lúc sinh dữ liệu
        default = default_checkbox_probability(question, _rule_config(rule))
        return {o.value: float(weights.get(o.value, 0.0)) if weights else (0.0 if o.is_other else default)
                for o in question.options}
    raw = {o.value: float(weights.get(o.value, 0.0)) for o in question.options} if weights else {
        o.value: 0.0 if o.is_other else 1.0 for o in question.options
    }
    total = sum(raw.values())
    return {k: round(v * 100 / total, 1) for k, v in raw.items()} if total > 0 else None


def build_distributions(
    structure: ParsedFormStructure, rules: Sequence[QuestionRule], logs: Sequence[SubmissionLog]
) -> list[QuestionDistribution]:
    rules_by_entry = {rule.entry_id: rule for rule in rules}
    successful = [log.payload_sent for log in logs if log.is_success]
    result: list[QuestionDistribution] = []
    for question in structure.questions:
        if not question.options:
            continue
        counts: Counter[str] = Counter()
        answered = 0
        for payload in successful:
            raw = payload.get(f"entry.{question.entry_id}")
            values = raw if isinstance(raw, list) else ([raw] if raw is not None else [])
            if values:
                answered += 1
                counts.update(str(v) for v in values)
        targets = _targets(question, rules_by_entry.get(question.entry_id))
        result.append(QuestionDistribution(
            entry_id=question.entry_id,
            title=question.title,
            answered=answered,
            options=[
                OptionDistribution(
                    label=option.label,
                    sent_count=counts[option.value],
                    sent_pct=round(counts[option.value] * 100 / answered, 1) if answered else 0.0,
                    target_pct=targets.get(option.value) if targets else None,
                )
                for option in question.options
            ],
        ))
    return result
