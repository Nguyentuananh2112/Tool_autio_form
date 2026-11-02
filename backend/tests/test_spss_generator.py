import numpy as np
import pytest

from app.schemas.campaign_schema import QuestionRuleConfig, SpssGroupConfig
from app.services.form_parser import parse_form_html
from app.services.spss_generator import (
    GeneratorConfigError,
    SurveyDataGenerator,
    build_payload_tuples,
    cronbach_alpha,
    responses_to_dataframe,
)
from tests.fixtures.sample_form import FINAL_URL, SATISFACTION_ENTRIES, build_html

RULES = [
    QuestionRuleConfig(entry_id="1001", question_type=2, weights={"Nam": 45, "Nữ": 50, "__other_option__": 5},
                       other_text_pool=["Không tiết lộ"]),
    QuestionRuleConfig(entry_id="1002", question_type=2, weights={"Có": 80, "Không": 20}),
    QuestionRuleConfig(entry_id="1007", question_type=4, weights={"FB": 70, "TikTok": 40, "Bạn bè": 20}, max_checked=2),
    QuestionRuleConfig(entry_id="1008", question_type=1, text_pool=["Tốt", "Cần cải thiện giá"], answer_rate=60),
]
GROUP = SpssGroupConfig(group_id="g1", name="Hài lòng", mean=4.1, std=0.7, alpha_target=0.85,
                        entries=SATISFACTION_ENTRIES, reversed_entries=["1006"])


@pytest.fixture(scope="module")
def generator() -> SurveyDataGenerator:
    form = parse_form_html(build_html(), FINAL_URL)
    gen = SurveyDataGenerator(form, RULES, [GROUP], seed=42)
    gen.validate()
    return gen


def test_cronbach_alpha_known_values() -> None:
    perfect = np.array([[1, 1], [2, 2], [3, 3], [4, 4]])
    assert cronbach_alpha(perfect) == pytest.approx(1.0)
    assert np.isnan(cronbach_alpha(np.ones((5, 3))))


def test_preview_hits_targets(generator: SurveyDataGenerator) -> None:
    preview = generator.preview_spss_groups(400)[0]
    assert preview.cronbach_alpha is not None and abs(preview.cronbach_alpha - 0.85) < 0.05
    assert abs(preview.achieved_mean - 4.1) < 0.15


def test_branching_and_page_history(generator: SurveyDataGenerator) -> None:
    responses = generator.generate(1000)
    for response in responses:
        if response.answers["1002"].values == ["Không"]:
            assert response.page_history == [0]
            assert "1003" not in response.answers
        else:
            assert response.page_history == [0, 1, 2]


def test_checkbox_limits(generator: SurveyDataGenerator) -> None:
    for response in generator.generate(500):
        if "1007" in response.answers:
            assert 1 <= len(response.answers["1007"].values) <= 2


def test_generated_group_alpha(generator: SurveyDataGenerator) -> None:
    responses = [r for r in generator.generate(2000) if "1003" in r.answers]
    matrix = np.array([[r.answers[e].numeric_value for e in SATISFACTION_ENTRIES] for r in responses])
    matrix[:, 3] = 6 - matrix[:, 3]  # đảo lại biến ngược chiều
    assert cronbach_alpha(matrix) > 0.8


def test_payload_format(generator: SurveyDataGenerator) -> None:
    response = generator.generate(1)[0]
    payload = build_payload_tuples(response, "-987")
    assert payload[-3:] == [("fvv", "1"), ("pageHistory", response.page_history_str), ("fbzx", "-987")]
    assert all(key.startswith("entry.") for key, _ in payload[:-3])


def test_dataframe_export(generator: SurveyDataGenerator) -> None:
    form = generator.structure
    df = responses_to_dataframe(form, generator.generate(50))
    assert len(df) == 50 and "page_history" in df.columns


def test_required_text_without_pool_fails() -> None:
    form = parse_form_html(build_html(), FINAL_URL)
    for question in form.questions:
        if question.entry_id == "1008":
            question.is_required = True
    with pytest.raises(GeneratorConfigError):
        SurveyDataGenerator(form, [], []).validate()
