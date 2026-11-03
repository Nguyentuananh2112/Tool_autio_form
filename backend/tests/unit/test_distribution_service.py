"""Kiểm tra phân phối đáp án đã gửi so với mục tiêu (app/services/distribution_service.py)."""

import pytest

from app.schemas.form_schema import OTHER_OPTION_VALUE, QuestionType
from app.services.distribution_service import build_distributions
from tests.unit._form_builders import form, log, question, rule

GENDER = question("1", QuestionType.MULTIPLE_CHOICE, ["Nam", "Nữ"], other=True)
CHANNELS = question("2", QuestionType.CHECKBOX, ["FB", "TikTok"], other=True)
COMMENT = question("3", QuestionType.PARAGRAPH)


def _by_label(dist) -> dict:
    return {o.label: o for o in dist.options}


def test_bo_qua_cau_khong_co_lua_chon() -> None:
    result = build_distributions(form(GENDER, COMMENT), [], [])
    assert [d.entry_id for d in result] == ["1"]


def test_dem_chi_log_thanh_cong_va_tinh_phan_tram() -> None:
    logs = [
        log(1, {"entry.1": ["Nam"]}),
        log(2, {"entry.1": "Nữ"}),  # giá trị đơn (không phải list) vẫn đếm được
        log(3, {"entry.1": ["Nam"]}),
        log(4, {"entry.1": ["Nữ"]}, ok=False),
    ]
    dist = build_distributions(form(GENDER), [], logs)[0]
    assert dist.answered == 3
    opts = _by_label(dist)
    assert opts["Nam"].sent_count == 2 and opts["Nam"].sent_pct == pytest.approx(66.7)
    assert opts["Nữ"].sent_count == 1 and opts["Nữ"].sent_pct == pytest.approx(33.3)
    assert opts["Mục khác"].sent_count == 0


def test_cau_chua_ai_tra_loi() -> None:
    dist = build_distributions(form(GENDER), [], [log(1, {"entry.9": ["x"]}), log(2, {"entry.1": None})])[0]
    assert dist.answered == 0
    assert all(o.sent_pct == 0.0 and o.sent_count == 0 for o in dist.options)


def test_muc_tieu_mac_dinh_chia_deu_khong_tinh_muc_khac() -> None:
    dist = build_distributions(form(GENDER), [], [])[0]
    assert [o.target_pct for o in dist.options] == [50.0, 50.0, 0.0]


def test_muc_tieu_chuan_hoa_theo_trong_so() -> None:
    rules = [rule("1", 2, {"weights": {"Nam": 30, "Nữ": 60, OTHER_OPTION_VALUE: 10}})]
    dist = build_distributions(form(GENDER), rules, [])[0]
    assert [o.target_pct for o in dist.options] == [30.0, 60.0, 10.0]
    # trọng số không cộng đủ 100 vẫn được quy về phần trăm
    rules = [rule("1", 2, {"weights": {"Nam": 1, "Nữ": 3}})]
    dist = build_distributions(form(GENDER), rules, [])[0]
    assert [o.target_pct for o in dist.options] == [25.0, 75.0, 0.0]


def test_trong_so_toan_khong_thi_khong_co_muc_tieu() -> None:
    rules = [rule("1", 2, {"weights": {"Nam": 0, "Nữ": 0}})]
    dist = build_distributions(form(GENDER), rules, [])[0]
    assert all(o.target_pct is None for o in dist.options)


def test_luat_khong_co_weights_dung_mac_dinh() -> None:
    dist = build_distributions(form(GENDER), [rule("1", 2, {"answer_rate": 50})], [])[0]
    assert [o.target_pct for o in dist.options] == [50.0, 50.0, 0.0]


def test_hop_kiem_mac_dinh_50_phan_tram_muc_khac_0() -> None:
    dist = build_distributions(form(CHANNELS), [], [])[0]
    assert [o.target_pct for o in dist.options] == [50.0, 50.0, 0.0]


def test_hop_kiem_xac_suat_doc_lap_khong_chuan_hoa() -> None:
    rules = [rule("2", 4, {"weights": {"FB": 80, "TikTok": 70}})]
    dist = build_distributions(form(CHANNELS), rules, [])[0]
    assert [o.target_pct for o in dist.options] == [80.0, 70.0, 0.0]


def test_hop_kiem_thieu_khoa_la_0_giong_luc_sinh_du_lieu() -> None:
    """Có weights thì ô thiếu khoá = 0% — đúng như resolve_weights khi sinh dữ liệu (trước đây hiển thị 50%)."""
    rules = [rule("2", 4, {"weights": {"FB": 10, OTHER_OPTION_VALUE: 5}})]
    dist = build_distributions(form(CHANNELS), rules, [])[0]
    assert [o.target_pct for o in dist.options] == [10.0, 0.0, 5.0]


def test_hop_kiem_gioi_han_toi_da_dung_muc_mac_dinh_moi() -> None:
    """BUG-014: có max_checked, không weights → mục tiêu = xác suất mặc định mới (giữa [min, max])."""
    many = question("2", QuestionType.CHECKBOX, [f"L{i}" for i in range(10)], other=True)
    rules = [rule("2", 4, {"max_checked": 3})]
    dist = build_distributions(form(many), rules, [])[0]
    assert [o.target_pct for o in dist.options] == [15.0] * 10 + [0.0]  # (0 + 3) / 2 / 10 ô


def test_hop_kiem_dem_nhieu_lua_chon_moi_phan_hoi() -> None:
    logs = [log(1, {"entry.2": ["FB", "TikTok"]}), log(2, {"entry.2": ["FB"]}), log(3, {"entry.2": []})]
    dist = build_distributions(form(CHANNELS), [], logs)[0]
    assert dist.answered == 2  # danh sách rỗng = không trả lời
    opts = _by_label(dist)
    assert opts["FB"].sent_pct == 100.0 and opts["TikTok"].sent_pct == 50.0


def test_luat_cua_cau_khac_khong_anh_huong() -> None:
    rules = [rule("2", 4, {"weights": {"FB": 90}})]
    dist = build_distributions(form(GENDER), rules, [])[0]
    assert [o.target_pct for o in dist.options] == [50.0, 50.0, 0.0]


def test_tieu_de_va_thu_tu_giu_nguyen() -> None:
    result = build_distributions(form(CHANNELS, GENDER), [], [])
    assert [(d.entry_id, d.title) for d in result] == [("2", "Câu 2"), ("1", "Câu 1")]
    assert [o.label for o in result[1].options] == ["Nam", "Nữ", "Mục khác"]
