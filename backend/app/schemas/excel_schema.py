"""DTO cho luồng nhập dữ liệu từ Excel/CSV (artboard 8 — ExcelImport)."""

from __future__ import annotations

from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, Field


class ColumnMatchKind(StrEnum):
    CODE = "CODE"  # khớp theo mã câu (A1, C10...)
    TITLE = "TITLE"  # khớp theo độ giống tiêu đề
    MANUAL = "MANUAL"  # người dùng tự chọn
    NONE = "NONE"  # bỏ qua cột


class ColumnMapping(BaseModel):
    column: str
    entry_id: str | None = None
    question_title: str | None = None
    kind: ColumnMatchKind = ColumnMatchKind.NONE
    score: float = Field(default=0.0, ge=0.0, le=1.0)

    @property
    def needs_review(self) -> bool:
        return self.kind == ColumnMatchKind.TITLE and self.score < 0.8


class RowIssue(BaseModel):
    row_number: int  # số dòng như trong Excel (dòng tiêu đề = 1)
    entry_id: str | None = None
    column: str | None = None
    severity: Literal["ERROR", "WARNING"]
    message: str


class ExcelPreview(BaseModel):
    filename: str
    sheet_names: list[str] = Field(default_factory=list)
    columns: list[str]
    row_count: int
    mappings: list[ColumnMapping]
    preview_rows: list[dict[str, Any]]


class ConversionReport(BaseModel):
    total_rows: int
    valid_rows: int
    invalid_rows: int
    issues: list[RowIssue] = Field(default_factory=list)
