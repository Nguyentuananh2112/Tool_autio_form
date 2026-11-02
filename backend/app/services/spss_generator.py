"""Điểm vào `services/spss_generator.py` theo cấu trúc thư mục của spec (Mục 3).

Phần cài đặt nằm trong package `app/services/spss/` (tách nhỏ để tránh God Module — CLAUDE.md).
Module này chỉ gom lại API công khai để các nơi khác import ổn định.
"""

from app.services.spss.answers import (
    ANSWER_KIND_CHOICE,
    ANSWER_KIND_DATE,
    ANSWER_KIND_TEXT,
    ANSWER_KIND_TIME,
    Answer,
    GeneratedResponse,
    build_payload_tuples,
)
from app.services.spss.calibration import calibrate_latent_correlation, calibrate_latent_moments
from app.services.spss.columns import TextMutator
from app.services.spss.export import responses_to_dataframe
from app.services.spss.generator import SurveyDataGenerator, generate_responses, preview_spss
from app.services.spss.scales import numeric_codes, scale_values_for
from app.services.spss.statistics import (
    alpha_from_r,
    cronbach_alpha,
    discretized_moments,
    mean_inter_item_correlation,
    r_from_alpha,
)
from app.services.spss.validation import GeneratorConfigError

__all__ = [
    "ANSWER_KIND_CHOICE",
    "ANSWER_KIND_DATE",
    "ANSWER_KIND_TEXT",
    "ANSWER_KIND_TIME",
    "Answer",
    "GeneratedResponse",
    "GeneratorConfigError",
    "SurveyDataGenerator",
    "TextMutator",
    "alpha_from_r",
    "build_payload_tuples",
    "calibrate_latent_correlation",
    "calibrate_latent_moments",
    "cronbach_alpha",
    "discretized_moments",
    "generate_responses",
    "mean_inter_item_correlation",
    "numeric_codes",
    "preview_spss",
    "r_from_alpha",
    "responses_to_dataframe",
    "scale_values_for",
]
