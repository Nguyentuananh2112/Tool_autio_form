"""Kiểm tra đọc file .xlsx / .csv (app/services/excel_reader.py)."""

import io

import pandas as pd
import pytest
from openpyxl import Workbook

from app.services import excel_reader
from app.services.excel_reader import ExcelReadError, list_sheets, read_table


def _xlsx(sheets: dict[str, list[list]]) -> bytes:
    workbook = Workbook()
    workbook.remove(workbook.active)
    for name, rows in sheets.items():
        sheet = workbook.create_sheet(name)
        for row in rows:
            sheet.append(row)
    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


ROWS = [["Giới tính", "Tuổi"], ["Nam", 20], ["Nữ", 31]]


def test_doc_xlsx_co_ban() -> None:
    frame = read_table(_xlsx({"Sheet1": ROWS}), "data.xlsx")
    assert list(frame.columns) == ["Giới tính", "Tuổi"]
    assert frame["Giới tính"].tolist() == ["Nam", "Nữ"]
    assert frame["Tuổi"].tolist() == [20, 31]  # dtype=object: giữ nguyên số


def test_duoi_file_khong_phan_biet_hoa_thuong() -> None:
    assert len(read_table(_xlsx({"S": ROWS}), "DATA.XLSX")) == 2


def test_chon_sheet_theo_ten_va_chi_so() -> None:
    content = _xlsx({"Một": ROWS, "Hai": [["Cột"], ["x"], ["y"], ["z"]]})
    assert list_sheets(content, "a.xlsx") == ["Một", "Hai"]
    assert read_table(content, "a.xlsx", sheet="Hai")["Cột"].tolist() == ["x", "y", "z"]
    assert read_table(content, "a.xlsx", sheet=1)["Cột"].tolist() == ["x", "y", "z"]
    assert list(read_table(content, "a.xlsx").columns) == ["Giới tính", "Tuổi"]


def test_sheet_khong_ton_tai_bao_loi() -> None:
    with pytest.raises(ExcelReadError, match="Excel"):
        read_table(_xlsx({"A": ROWS}), "a.xlsx", sheet="Không có")


def test_list_sheets_csv_tra_rong_va_file_hong_bao_loi() -> None:
    assert list_sheets(b"a,b\n1,2", "a.csv") == []
    with pytest.raises(ExcelReadError, match="Không mở được"):
        list_sheets(b"day khong phai excel", "a.xlsx")


def test_xlsx_hong_bao_loi() -> None:
    with pytest.raises(ExcelReadError):
        read_table(b"PK\x03\x04 rac", "a.xlsx")


def test_bo_dong_cot_rong_va_cot_unnamed() -> None:
    rows = [["A", None, "B", None], ["1", None, "2", "lẻ"], [None, None, None, None], ["3", None, "4", None]]
    frame = read_table(_xlsx({"S": rows}), "a.xlsx")
    # cột tiêu đề trống nhưng có dữ liệu → "Unnamed: 3" bị bỏ; cột trống hoàn toàn bị bỏ
    assert list(frame.columns) == ["A", "B"]
    assert frame["A"].tolist() == ["1", "3"]
    assert list(frame.index) == [0, 1]


def test_tieu_de_duoc_strip() -> None:
    frame = read_table("  Tên  ,Tuổi \nAn,20\n".encode(), "a.csv")
    assert list(frame.columns) == ["Tên", "Tuổi"]


@pytest.mark.parametrize("sep", [",", ";", "\t"])
def test_csv_tu_nhan_dau_phan_cach(sep: str) -> None:
    text = sep.join(["Tên", "Điểm"]) + "\n" + sep.join(["An", "5"]) + "\n" + sep.join(["Bình", "4"]) + "\n"
    frame = read_table(text.encode("utf-8"), "a.csv")
    assert list(frame.columns) == ["Tên", "Điểm"]
    assert frame["Điểm"].tolist() == ["5", "4"]  # CSV giữ chuỗi


def test_csv_utf8_sig_bo_bom() -> None:
    frame = read_table("Họ tên,Ý kiến\nAn,Rất tốt\n".encode("utf-8-sig"), "a.csv")
    assert list(frame.columns)[0] == "Họ tên"


def test_csv_bang_ma_cp1258() -> None:
    content = "Tên,Ghi chú\nAn,Đông vui\n".encode("cp1258")
    with pytest.raises(UnicodeDecodeError):
        content.decode("utf-8")
    frame = read_table(content, "a.csv")
    assert frame["Ghi chú"].tolist() == ["Đông vui"]


def test_file_rong() -> None:
    with pytest.raises(ExcelReadError, match="File rỗng"):
        read_table(b"", "a.csv")


def test_csv_chi_co_tieu_de_khong_co_dong() -> None:
    with pytest.raises(ExcelReadError, match="không có dòng"):
        read_table(b"A,B\n", "a.csv")


def test_xlsx_khong_co_dong_du_lieu() -> None:
    with pytest.raises(ExcelReadError, match="không có dòng"):
        read_table(_xlsx({"S": [["A", "B"]]}), "a.xlsx")


def test_file_qua_lon(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(excel_reader, "MAX_FILE_BYTES", 10)
    with pytest.raises(ExcelReadError, match="quá lớn"):
        read_table(b"A,B\n1,2\n3,4\n", "a.csv")


def test_qua_nhieu_dong_va_cot(monkeypatch: pytest.MonkeyPatch) -> None:
    content = b"A,B,C\n1,2,3\n4,5,6\n7,8,9\n"
    monkeypatch.setattr(excel_reader, "MAX_ROWS", 2)
    with pytest.raises(ExcelReadError, match="3 dòng"):
        read_table(content, "a.csv")
    monkeypatch.setattr(excel_reader, "MAX_ROWS", 100)
    monkeypatch.setattr(excel_reader, "MAX_COLUMNS", 2)
    with pytest.raises(ExcelReadError, match="3 cột"):
        read_table(content, "a.csv")


@pytest.mark.parametrize(("name", "message"), [("a.xls", ".xls cũ"), ("a.txt", "Chỉ hỗ trợ"), ("noext", "Chỉ hỗ trợ")])
def test_dinh_dang_khong_ho_tro(name: str, message: str) -> None:
    with pytest.raises(ExcelReadError, match=message):
        read_table(b"A,B\n1,2\n", name)


def test_tra_ve_dataframe_object() -> None:
    frame = read_table(b"A\n1\n", "a.csv")
    assert isinstance(frame, pd.DataFrame) and frame["A"].dtype == object


@pytest.mark.parametrize("text", ["Tên\nAn\nBình\n", "A\n1\n2\n"])
def test_csv_mot_cot_khong_bi_tach_nham(text: str) -> None:
    """Trước đây Sniffer chọn nhầm chữ cái làm dấu phân cách khi file chỉ có một cột."""
    frame = read_table(text.encode("utf-8"), "a.csv")
    assert list(frame.columns) == [text.split("\n")[0]]
    assert frame.iloc[:, 0].tolist() == text.split("\n")[1:3]


def test_csv_dau_cham_phay_co_dau_phay_trong_o() -> None:
    frame = read_table("Tên;Ý kiến\nAn;Tốt, rẻ\nBình;Ổn, nhanh\n".encode(), "a.csv")
    assert frame["Ý kiến"].tolist() == ["Tốt, rẻ", "Ổn, nhanh"]
