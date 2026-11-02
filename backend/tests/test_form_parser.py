import pytest

from app.schemas.form_schema import OTHER_OPTION_VALUE, NavigationAction
from app.services.form_parser import (
    FormStructureError,
    InvalidFormUrlError,
    build_form_urls,
    normalize_form_url,
    parse_form_html,
)
from tests.fixtures.sample_form import FINAL_URL, SECTION_2_ID, build_html


def test_parse_basic_structure() -> None:
    form = parse_form_html(build_html(), FINAL_URL)
    assert form.title == "Khảo sát thử"
    assert form.fbzx == "-987"
    assert form.total_pages == 3
    assert len(form.questions) == 9  # 4 hàng grid được tách riêng
    assert [s.section_item_id for s in form.sections] == [None, SECTION_2_ID, 900002]


def test_urls_built_from_final_url() -> None:
    view_url, submit_url = build_form_urls(FINAL_URL)
    assert view_url == "https://docs.google.com/forms/d/e/ABC/viewform"
    assert submit_url == "https://docs.google.com/forms/d/e/ABC/formResponse"


def test_other_option_and_branching() -> None:
    form = parse_form_html(build_html(), FINAL_URL)
    gender = form.get_question("1001")
    assert gender is not None and gender.options[-1].is_other
    assert gender.options[-1].value == OTHER_OPTION_VALUE
    usage = form.get_question("1002")
    assert usage is not None
    assert [o.jump_to_section_id for o in usage.options] == [SECTION_2_ID, -2]


def test_grid_rows_and_scale() -> None:
    form = parse_form_html(build_html(), FINAL_URL)
    row = form.get_question("1003")
    assert row is not None and row.grid_item_id == 103 and row.row_label == "HL1"
    assert row.page_index == 1 and not row.is_multi_select
    scale = form.get_question("1009")
    assert scale is not None and scale.scale_low_label == "Thấp" and scale.page_index == 2


def test_page_break_sets_previous_section_navigation() -> None:
    form = parse_form_html(build_html(), FINAL_URL)
    assert form.sections[0].navigation_action == NavigationAction.NEXT_PAGE


@pytest.mark.parametrize(
    "url",
    ["https://evil.com/forms/x", "https://docs.google.com/forms/d/ABC/edit", "https://docs.google.com/document/d/1", ""],
)
def test_rejects_invalid_urls(url: str) -> None:
    with pytest.raises(InvalidFormUrlError):
        normalize_form_url(url)


def test_accepts_short_link_without_scheme() -> None:
    assert normalize_form_url("forms.gle/abc123") == "https://forms.gle/abc123"


def test_missing_fb_data_raises() -> None:
    with pytest.raises(FormStructureError):
        parse_form_html("<html></html>", FINAL_URL)
