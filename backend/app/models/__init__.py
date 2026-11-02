"""Import mọi model để SQLAlchemy registry giải quyết được các relationship dạng chuỗi.

Không có model `User`: app desktop một người dùng/máy (dev-notes SPEC-011).
"""

from app.models.campaign import Campaign, CampaignStatus, DataSource
from app.models.form import Form
from app.models.question_rule import QuestionRule
from app.models.submission_log import EngineUsed, SubmissionLog

__all__ = [
    "Campaign",
    "CampaignStatus",
    "DataSource",
    "EngineUsed",
    "Form",
    "QuestionRule",
    "SubmissionLog",
]
