"""Unit test cho app/services/spss/answers.py (đóng gói payload POST /formResponse)."""

from app.services.spss.answers import (
    ANSWER_KIND_DATE,
    ANSWER_KIND_TEXT,
    ANSWER_KIND_TIME,
    Answer,
    GeneratedResponse,
    build_payload_tuples,
)


def _response(answers: dict[str, Answer], history: list[int] | None = None) -> GeneratedResponse:
    response = GeneratedResponse(sequence_number=1, answers=answers)
    if history is not None:
        response.page_history = history
    return response


def test_ngay_tach_nam_thang_ngay_khong_dem_so_0() -> None:
    payload = build_payload_tuples(_response({"11": Answer(values=["2024-03-05"], kind=ANSWER_KIND_DATE)}), None)
    assert payload[:3] == [("entry.11_year", "2024"), ("entry.11_month", "3"), ("entry.11_day", "5")]


def test_gio_tach_gio_phut_co_dem_so_0() -> None:
    payload = build_payload_tuples(_response({"12": Answer(values=["8:5"], kind=ANSWER_KIND_TIME)}), None)
    assert payload[:2] == [("entry.12_hour", "08"), ("entry.12_minute", "05")]


def test_gio_co_giay_bi_bo_giay() -> None:
    payload = build_payload_tuples(_response({"12": Answer(values=["14:30:59"], kind=ANSWER_KIND_TIME)}), None)
    assert payload[:2] == [("entry.12_hour", "14"), ("entry.12_minute", "30")]


def test_muc_khac_them_other_option_response() -> None:
    answer = Answer(values=["__other_option__"], other_text="Ý kiến riêng")
    payload = build_payload_tuples(_response({"13": answer}), None)
    assert payload[:2] == [("entry.13", "__other_option__"), ("entry.13.other_option_response", "Ý kiến riêng")]


def test_other_text_rong_van_duoc_gui() -> None:
    payload = build_payload_tuples(_response({"13": Answer(values=["x"], other_text="")}), None)
    assert ("entry.13.other_option_response", "") in payload


def test_checkbox_lap_lai_khoa_entry() -> None:
    payload = build_payload_tuples(_response({"14": Answer(values=["A", "C"])}), None)
    assert payload[:2] == [("entry.14", "A"), ("entry.14", "C")]


def test_fbzx_none_hoac_rong_bi_bo() -> None:
    for token in (None, ""):
        keys = [key for key, _ in build_payload_tuples(_response({}), token)]
        assert keys == ["fvv", "pageHistory"]


def test_thu_tu_truong_entry_roi_fvv_pagehistory_fbzx() -> None:
    answers = {
        "1": Answer(values=["A"]),
        "2": Answer(values=["Chữ"], kind=ANSWER_KIND_TEXT),
        "3": Answer(values=["2023-12-31"], kind=ANSWER_KIND_DATE),
    }
    payload = build_payload_tuples(_response(answers, [0, 2, 3]), "-123")
    assert payload == [
        ("entry.1", "A"),
        ("entry.2", "Chữ"),
        ("entry.3_year", "2023"),
        ("entry.3_month", "12"),
        ("entry.3_day", "31"),
        ("fvv", "1"),
        ("pageHistory", "0,2,3"),
        ("fbzx", "-123"),
    ]


def test_page_history_mac_dinh() -> None:
    response = GeneratedResponse(sequence_number=7, answers={})
    assert response.page_history == [0] and response.page_history_str == "0"
    assert ("pageHistory", "0") in build_payload_tuples(response, None)
