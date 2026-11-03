"""Lượt 2–3 trên mẫu thử: sinh N người theo kiểu cũ và kiểu có soát, so sánh để người dùng xem.

Module thuần CPU: trong code async gọi qua `asyncio.to_thread(review_logic, ...)`.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence

import numpy as np
import pandas as pd

from app.schemas.campaign_schema import QuestionRuleConfig, SpssGroupConfig
from app.schemas.form_schema import ParsedFormStructure
from app.schemas.logic_api import GroupCorrelation, LogicReviewResult, RatioDrift, SampleRespondent, ViolationCount
from app.schemas.logic_schema import LogicMap
from app.services.logic.checker import ResponseChecker
from app.services.logic.ordering import positions
from app.services.spss.answers import GeneratedResponse
from app.services.spss.generator import SurveyDataGenerator

REVIEW_SEED = 20_261_103
DRIFT_REPORT_PCT = 5.0
MAX_DRIFTS = 5
MIN_PAIR_ANSWERS = 10
ATTITUDE_LABELS = ((0.75, "rất tích cực"), (0.58, "khá tích cực"), (0.42, "trung lập"), (0.25, "khá tiêu cực"))


def _position_frame(responses: Sequence[GeneratedResponse], structure: ParsedFormStructure, logic: LogicMap, group_index: int) -> pd.DataFrame:
    questions = {q.entry_id: q for q in structure.questions}
    columns: dict[str, list[float]] = {}
    for item in logic.attitude_groups[group_index].items:
        question = questions.get(item.entry_id)
        if question is None:
            continue
        pos = positions(question, item)
        columns[item.entry_id] = [
            pos.get(answer.values[0], np.nan) if (answer := r.answers.get(item.entry_id)) and answer.values else np.nan
            for r in responses
        ]
    return pd.DataFrame(columns)


def mean_correlation(frame: pd.DataFrame) -> float | None:
    if frame.shape[1] < 2:
        return None
    corr = frame.corr(min_periods=MIN_PAIR_ANSWERS).to_numpy()
    upper = corr[np.triu_indices_from(corr, k=1)]
    upper = upper[~np.isnan(upper)]
    return round(float(upper.mean()), 2) if upper.size else None


def _shares(responses: Sequence[GeneratedResponse], entry_id: str) -> Counter[str]:
    counts: Counter[str] = Counter()
    for response in responses:
        answer = response.answers.get(entry_id)
        if answer is not None:
            counts.update(answer.values)
    return counts


def _drifts(structure: ParsedFormStructure, plain: Sequence[GeneratedResponse], checked: Sequence[GeneratedResponse]) -> list[RatioDrift]:
    drifts = []
    for question in structure.questions:
        if not question.options:
            continue
        before, after = _shares(plain, question.entry_id), _shares(checked, question.entry_id)
        n_before = sum(1 for r in plain if question.entry_id in r.answers)
        n_after = sum(1 for r in checked if question.entry_id in r.answers)
        if not n_before or not n_after:
            continue
        drift = max(abs(after[o.value] / n_after - before[o.value] / n_before) * 100 for o in question.options)
        if drift >= DRIFT_REPORT_PCT:
            drifts.append(RatioDrift(entry_id=question.entry_id, title=question.row_label or question.title, max_drift_pct=round(drift, 1)))
    return sorted(drifts, key=lambda d: -d.max_drift_pct)[:MAX_DRIFTS]


def _sample(responses: Sequence[GeneratedResponse], structure: ParsedFormStructure, logic: LogicMap) -> SampleRespondent | None:
    if not responses or not logic.attitude_groups:
        return None
    frame = _position_frame(responses, structure, logic, 0)
    if frame.empty:
        return None
    counts = frame.notna().sum(axis=1)
    index = int(counts.idxmax())
    level = float(frame.iloc[index].mean())
    attitude = next((label for cut, label in ATTITUDE_LABELS if level >= cut), "rất tiêu cực")
    return SampleRespondent(attitude=attitude, answers={e: list(a.values) for e, a in responses[index].answers.items()})


def review_logic(
    structure: ParsedFormStructure,
    rules: Sequence[QuestionRuleConfig],
    spss_groups: Sequence[SpssGroupConfig],
    logic: LogicMap,
    n: int = 200,
    seed: int = REVIEW_SEED,
) -> LogicReviewResult:
    plain = SurveyDataGenerator(structure, rules, spss_groups, seed=seed).generate(n)
    generator = SurveyDataGenerator(structure, rules, spss_groups, seed=seed, logic=logic)
    checked = generator.generate(n)
    stats = generator.filter_stats
    checker = ResponseChecker(structure, logic)

    before: Counter[tuple[str, str]] = Counter()
    after: Counter[tuple[str, str]] = Counter()
    inconsistent_before = inconsistent_after = 0
    for response in plain:
        found = checker.violations(response.answers)
        inconsistent_before += any(not v.soft for v in found)
        before.update({(v.kind.value, v.key) for v in found if not v.soft})
    for response in checked:
        found = checker.blocking(response.answers)
        inconsistent_after += bool(found)
        after.update({(v.kind.value, v.key) for v in found})

    violations = [
        ViolationCount(kind=kind, key=key, before=before[(kind, key)], after=after[(kind, key)])
        for kind, key in sorted(set(before) | set(after))
    ]
    correlations = [
        GroupCorrelation(
            group_id=group.group_id, name=group.name,
            before=mean_correlation(_position_frame(plain, structure, logic, i)),
            after=mean_correlation(_position_frame(checked, structure, logic, i)),
        )
        for i, group in enumerate(logic.attitude_groups)
    ]
    return LogicReviewResult(
        sample_size=n,
        inconsistent_before=inconsistent_before,
        inconsistent_after=inconsistent_after,
        repaired=stats.repaired if stats else 0,
        regenerated=stats.rejected if stats else 0,
        violations=violations,
        correlations=correlations,
        drifts=_drifts(structure, plain, checked),
        sample=_sample(checked, structure, logic),
        logic=logic,
        ready=inconsistent_after == 0,
    )
