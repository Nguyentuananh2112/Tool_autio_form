import io

import pandas as pd
import pytest

from app.schemas.excel_schema import ColumnMatchKind
from app.services.excel_mapper import build_records, preview_file, records_to_responses, suggest_mappings
from app.services.excel_reader import ExcelReadError, read_table
from app.services.form_parser import parse_form_html
from tests.fixtures.sample_form import FINAL_URL, build_html

FORM = parse_form_html(build_html(), FINAL_URL)


def _xlsx(frame: pd.DataFrame) -> bytes:
    buffer = io.BytesIO()
    frame.to_excel(buffer, index=False)
    return buffer.getvalue()


def _frame() -> pd.DataFrame:
    return pd.DataFrame({
        "Thời gian": ["01/11", "01/11", "02/11", "02/11"],
        "Giới tính": ["Nam", "nữ", "Không tiết lộ", "Nam"],
        "Có dùng sản phẩm?": ["Có", "Không", "Có", "Có"],
        "HL1": [4, None, 5, 3], "HL2": [4, None, 4, 3], "HL3": [5, None, 4, None], "HL4": [2, None, 1, 3],
        "Kênh biết đến": ["FB, TikTok", None, "Bạn bè; Zalo", "FB"],
        "Mức độ quay lại": [5, None, 4, 3],
    })


def test_suggest_mappings_by_title_and_grid_row() -> None:
    mappings = {m.column: m for m in suggest_mappings(list(_frame().columns), FORM)}
    assert mappings["Giới tính"].entry_id == "1001"
    assert mappings["HL3"].entry_id == "1005"
    assert mappings["Thời gian"].kind == ColumnMatchKind.NONE
    assert len({m.entry_id for m in mappings.values() if m.entry_id}) == sum(1 for m in mappings.values() if m.entry_id)


def test_rows_convert_with_branching_other_and_errors() -> None:
    frame = _frame()
    records = build_records(frame, suggest_mappings(list(frame.columns), FORM))
    responses, report = records_to_responses(records, FORM)
    # Dòng 4: "Kênh biết đến" có "Zalo" nhưng câu không có Mục khác → lỗi; dòng 5 thiếu HL3 bắt buộc
    assert report.valid_rows == 2 and report.invalid_rows == 2
    first, second = responses
    assert first.page_history == [0, 1, 2] and first.answers["1007"].values == ["FB", "TikTok"]
    assert first.answers["1003"].values == ["4"] and first.answers["1003"].numeric_value == 4.0
    assert second.page_history == [0] and "1003" not in second.answers
    assert any("Mục khác" in i.message and i.row_number == 4 for i in report.issues if i.severity == "WARNING")
    assert {i.row_number for i in report.issues if i.severity == "ERROR"} == {4, 5}


def test_preview_and_reader_errors() -> None:
    preview = preview_file(_xlsx(_frame()), "data.xlsx", FORM)
    assert preview.row_count == 4 and len(preview.preview_rows) == 4 and preview.sheet_names
    csv_bytes = _frame().to_csv(index=False, sep=";").encode("utf-8-sig")
    assert list(read_table(csv_bytes, "data.csv").columns) == list(_frame().columns)
    with pytest.raises(ExcelReadError):
        read_table(b"abc", "data.xls")
