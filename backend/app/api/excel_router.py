"""Nhập Excel/CSV cho một form (Mục 6.2 spec + artboard 8)."""

from __future__ import annotations

import asyncio
import json
import uuid
from typing import Annotated

from fastapi import APIRouter, File, Form, UploadFile
from pydantic import TypeAdapter, ValidationError

from app.api.deps import DbSession
from app.schemas.campaign_api import ExcelConvertResponse
from app.schemas.excel_schema import ColumnMapping, ExcelPreview
from app.services.campaign_service import get_form, structure_of
from app.services.excel_mapper import build_records, preview_file, records_to_responses
from app.services.excel_reader import MAX_FILE_BYTES, ExcelReadError, read_table

router = APIRouter(prefix="/forms/{form_id}", tags=["excel"])
MAPPINGS_ADAPTER = TypeAdapter(list[ColumnMapping])


async def _read_upload(upload: UploadFile) -> bytes:
    content = await upload.read(MAX_FILE_BYTES + 1)
    if len(content) > MAX_FILE_BYTES:
        raise ExcelReadError("File quá lớn (tối đa 20 MB).")
    return content


def _sheet(value: str | None) -> str | int:
    return value if value else 0


@router.post("/parse-excel", response_model=ExcelPreview)
async def parse_excel(
    form_id: uuid.UUID,
    session: DbSession,
    file: Annotated[UploadFile, File()],
    sheet: Annotated[str | None, Form()] = None,
) -> ExcelPreview:
    structure = structure_of(await get_form(session, form_id))
    content = await _read_upload(file)
    return await asyncio.to_thread(preview_file, content, file.filename or "upload.xlsx", structure, sheet=_sheet(sheet))


@router.post("/excel-convert", response_model=ExcelConvertResponse)
async def convert_excel(
    form_id: uuid.UUID,
    session: DbSession,
    file: Annotated[UploadFile, File()],
    mappings: Annotated[str, Form(description="JSON list[ColumnMapping] sau khi người dùng chỉnh")],
    sheet: Annotated[str | None, Form()] = None,
) -> ExcelConvertResponse:
    structure = structure_of(await get_form(session, form_id))
    try:
        column_mappings = MAPPINGS_ADAPTER.validate_python(json.loads(mappings))
    except (json.JSONDecodeError, ValidationError) as exc:
        raise ExcelReadError(f"Danh sách ghép cột không hợp lệ: {exc}") from exc
    content = await _read_upload(file)

    def convert() -> ExcelConvertResponse:
        frame = read_table(content, file.filename or "upload.xlsx", sheet=_sheet(sheet))
        records = build_records(frame, column_mappings)
        _, report = records_to_responses(records, structure)
        return ExcelConvertResponse(report=report, records=records)

    return await asyncio.to_thread(convert)
