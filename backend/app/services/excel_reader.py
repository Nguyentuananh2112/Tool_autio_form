"""Đọc file .xlsx / .csv do người dùng tải lên thành DataFrame sạch (chuỗi, không NaN lộn xộn)."""

from __future__ import annotations

import csv
import io
import zipfile
from pathlib import PurePath

import pandas as pd
from openpyxl import load_workbook
from openpyxl.utils.exceptions import InvalidFileException

MAX_FILE_BYTES = 20 * 1024 * 1024
MAX_ROWS = 20_000
MAX_COLUMNS = 500
CSV_ENCODINGS: tuple[str, ...] = ("utf-8-sig", "cp1258", "cp1252")
EXCEL_SUFFIXES = frozenset({".xlsx", ".xlsm"})


class ExcelReadError(ValueError):
    pass


def _suffix(filename: str) -> str:
    return PurePath(filename).suffix.lower()


def list_sheets(content: bytes, filename: str) -> list[str]:
    if _suffix(filename) not in EXCEL_SUFFIXES:
        return []
    try:
        workbook = load_workbook(io.BytesIO(content), read_only=True)
    except (InvalidFileException, zipfile.BadZipFile, OSError, KeyError) as exc:
        raise ExcelReadError(f"Không mở được file Excel: {exc}") from exc
    try:
        return list(workbook.sheetnames)
    finally:
        workbook.close()


CSV_DELIMITERS = ",;	|"


def _detect_delimiter(sample: str) -> str:
    # Chỉ đoán trong các dấu phân cách hợp lệ: để Sniffer tự do sẽ chọn nhầm một chữ cái
    # khi file chỉ có một cột (VD "Tên" → tách theo "n")
    try:
        return csv.Sniffer().sniff(sample, delimiters=CSV_DELIMITERS).delimiter
    except csv.Error:
        return ","


def _read_csv(content: bytes) -> pd.DataFrame:
    last_error: Exception | None = None
    for encoding in CSV_ENCODINGS:
        try:
            text = content.decode(encoding)
        except UnicodeDecodeError as exc:
            last_error = exc
            continue
        try:
            return pd.read_csv(io.StringIO(text), sep=_detect_delimiter(text[:20_000]), dtype=object)
        except (pd.errors.ParserError, pd.errors.EmptyDataError, ValueError) as exc:
            raise ExcelReadError(f"Không đọc được file CSV: {exc}") from exc
    raise ExcelReadError(f"Không nhận ra bảng mã của file CSV: {last_error}")


def _clean(frame: pd.DataFrame) -> pd.DataFrame:
    frame = frame.dropna(how="all").dropna(axis=1, how="all")
    frame.columns = [str(column).strip() for column in frame.columns]
    frame = frame.loc[:, [not column.startswith("Unnamed:") for column in frame.columns]]
    return frame.reset_index(drop=True)


def read_table(content: bytes, filename: str, *, sheet: str | int = 0) -> pd.DataFrame:
    if not content:
        raise ExcelReadError("File rỗng.")
    if len(content) > MAX_FILE_BYTES:
        raise ExcelReadError("File quá lớn (tối đa 20 MB).")

    suffix = _suffix(filename)
    if suffix in EXCEL_SUFFIXES:
        try:
            frame = pd.read_excel(io.BytesIO(content), sheet_name=sheet, dtype=object, engine="openpyxl")
        except (ValueError, KeyError, InvalidFileException, zipfile.BadZipFile, OSError) as exc:
            raise ExcelReadError(f"Không đọc được file Excel: {exc}") from exc
    elif suffix == ".csv":
        frame = _read_csv(content)
    elif suffix == ".xls":
        raise ExcelReadError("Định dạng .xls cũ chưa được hỗ trợ. Hãy lưu lại thành .xlsx hoặc .csv.")
    else:
        raise ExcelReadError("Chỉ hỗ trợ file .xlsx hoặc .csv.")

    frame = _clean(frame)
    if frame.empty:
        raise ExcelReadError("File không có dòng dữ liệu nào.")
    if len(frame) > MAX_ROWS:
        raise ExcelReadError(f"File có {len(frame)} dòng, vượt giới hạn {MAX_ROWS} dòng.")
    if len(frame.columns) > MAX_COLUMNS:
        raise ExcelReadError(f"File có {len(frame.columns)} cột, vượt giới hạn {MAX_COLUMNS} cột.")
    return frame
