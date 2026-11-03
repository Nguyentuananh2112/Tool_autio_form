"""Kiểm tra xuất dữ liệu đã gửi ra CSV / Excel (app/services/export_service.py)."""

import io
from datetime import UTC, datetime

import pandas as pd
from openpyxl import load_workbook

from app.schemas.form_schema import OTHER_OPTION_VALUE, QuestionType
from app.services.export_service import (
    META_COLUMNS,
    build_numeric_frame,
    build_text_frame,
    to_csv_bytes,
    to_xlsx_bytes,
)
from tests.unit._form_builders import form, log, question

GENDER = question("1", QuestionType.MULTIPLE_CHOICE, ["Nam", "Nữ"], other=True, title="Giới tính")
CHANNELS = question("2", QuestionType.CHECKBOX, ["FB", "TikTok"], other=True, title="Kênh")
SCALE = question("3", QuestionType.LINEAR_SCALE, ["1", "2", "3", "4", "5"], title="Hài lòng")
LEVEL = question("4", QuestionType.DROPDOWN, ["Thấp", "Vừa", "Cao"], title="Mức")
DAY = question("5", QuestionType.DATE, title="Ngày")
HOUR = question("6", QuestionType.TIME, title="Giờ")
NOTE = question("7", QuestionType.SHORT_ANSWER, title="Giới tính")  # trùng tiêu đề với câu 1

FORM = form(GENDER, CHANNELS, SCALE, LEVEL, DAY, HOUR, NOTE)
FULL = {
    "entry.1": [OTHER_OPTION_VALUE], "entry.1.other_option_response": ["Không tiết lộ"],
    "entry.2": ["FB", "TikTok"], "entry.3": ["4"], "entry.4": ["Cao"],
    "entry.5_year": ["2026"], "entry.5_month": ["3"], "entry.5_day": ["7"],
    "entry.6_hour": ["08"], "entry.6_minute": ["05"], "entry.7": ["Ghi chú"], "pageHistory": "0",
}


def test_khung_chu_cot_meta_va_tieu_de_duy_nhat() -> None:
    frame = build_text_frame(FORM, [])
    assert list(frame.columns)[: len(META_COLUMNS)] == list(META_COLUMNS)
    assert list(frame.columns)[len(META_COLUMNS):] == [
        "Giới tính", "Kênh", "Hài lòng", "Mức", "Ngày", "Giờ", "Giới tính (7)",
    ]
    assert frame.empty


def test_khung_chu_hien_thi_gia_tri() -> None:
    row = build_text_frame(FORM, [log(1, FULL)]).iloc[0]
    assert row["Giới tính"] == "Khác: Không tiết lộ"
    assert row["Kênh"] == "FB; TikTok"
    assert row["Hài lòng"] == "4" and row["Mức"] == "Cao"
    assert row["Ngày"] == "2026-03-07"
    assert row["Giờ"] == "08:05"
    assert row["Giới tính (7)"] == "Ghi chú"
    assert row["Đường đi"] == "0"


def test_muc_khac_khong_co_chu_giu_nguyen_ma() -> None:
    row = build_text_frame(FORM, [log(1, {"entry.1": [OTHER_OPTION_VALUE]})]).iloc[0]
    assert row["Giới tính"] == OTHER_OPTION_VALUE


def test_ngay_gio_thieu_phan_thi_de_trong() -> None:
    payload = {"entry.5_year": ["2026"], "entry.5_month": ["3"], "entry.6_hour": ["9"]}
    row = build_text_frame(FORM, [log(1, payload)]).iloc[0]
    assert row["Ngày"] is None and row["Giờ"] is None
    assert row["Giới tính"] is None and row["Kênh"] is None


def test_khung_chu_gom_ca_log_that_bai_va_meta() -> None:
    logs = [log(1, FULL), log(2, {"entry.3": "2"}, ok=False, status=400, error="Lỗi kiểm tra", engine="PLAYWRIGHT")]
    frame = build_text_frame(FORM, logs)
    assert frame["STT"].tolist() == [1, 2]
    assert frame["Thành công"].tolist() == ["Có", "Không"]
    assert frame["Công cụ"].tolist() == ["HTTPX", "PLAYWRIGHT"]
    assert frame["Mã HTTP"].tolist() == [200, 400]
    assert frame["Lỗi"].tolist()[1] == "Lỗi kiểm tra"
    assert frame["Hài lòng"].tolist()[1] == "2"  # giá trị đơn (không phải list)


def test_thoi_diem_gui_doi_sang_gio_may() -> None:
    naive = log(1, {}, at=datetime(2026, 1, 2, 3, 4, 5))
    aware = log(2, {}, at=datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC))
    frame = build_text_frame(FORM, [naive, aware])
    expected = datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC).astimezone().strftime("%Y-%m-%d %H:%M:%S")
    assert frame["Thời điểm gửi"].tolist() == [expected, expected]
    assert build_text_frame(FORM, [log(3, {}, at=None)])["Thời điểm gửi"].tolist() == [None]


def test_khung_so_ma_hoa_va_cot_hop_kiem() -> None:
    frame = build_numeric_frame(FORM, [log(1, FULL)])
    row = frame.iloc[0]
    assert row["STT"] == 1
    assert row["Giới tính"] == 3.0  # "Mục khác" = K + 1
    assert (row["Kênh [FB]"], row["Kênh [TikTok]"], row["Kênh [Mục khác]"]) == (1, 1, 0)
    assert row["Hài lòng"] == 4.0  # thang số giữ giá trị thật
    assert row["Mức"] == 3.0  # nhãn chữ → mã 1..K
    assert row["Ngày"] == "2026-03-07" and row["Giờ"] == "08:05"
    assert row["Giới tính (7)"] == "Ghi chú"
    assert "Kênh" not in frame.columns


def test_khung_so_bo_log_that_bai_va_o_trong() -> None:
    logs = [log(1, {"entry.3": ["2"]}), log(2, FULL, ok=False)]
    frame = build_numeric_frame(FORM, logs)
    assert frame["STT"].tolist() == [1]
    row = frame.iloc[0]
    assert pd.isna(row["Giới tính"]) and pd.isna(row["Kênh [FB]"])  # chưa trả lời ≠ 0
    assert row["Hài lòng"] == 2.0


def test_khung_so_gia_tri_la_tra_ve_none() -> None:
    frame = build_numeric_frame(FORM, [log(1, {"entry.4": ["Không có"]})])
    assert pd.isna(frame.iloc[0]["Mức"])


def test_csv_co_bom_va_doc_lai_duoc() -> None:
    frame = build_text_frame(FORM, [log(1, FULL)])
    content = to_csv_bytes(frame)
    assert content.startswith(b"\xef\xbb\xbf")
    back = pd.read_csv(io.BytesIO(content), encoding="utf-8-sig", dtype=str)
    assert list(back.columns) == list(frame.columns)
    assert back.loc[0, "Giới tính"] == "Khác: Không tiết lộ"


def test_xlsx_co_hai_trang() -> None:
    logs = [log(1, FULL), log(2, FULL, ok=False)]
    content = to_xlsx_bytes(build_text_frame(FORM, logs), build_numeric_frame(FORM, logs))
    workbook = load_workbook(io.BytesIO(content))
    assert workbook.sheetnames == ["Dữ liệu", "SPSS (mã số)"]
    assert workbook["Dữ liệu"].max_row == 3 and workbook["SPSS (mã số)"].max_row == 2
    assert workbook["Dữ liệu"].cell(1, 1).value == "STT"
