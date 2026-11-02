"""Form giả lập theo cấu trúc FB_PUBLIC_LOAD_DATA_ (Mục 5.1 spec): rẽ nhánh, grid, checkbox, Other."""

import json
from typing import Any

SECTION_2_ID = 900001
SECTION_3_ID = 900002
SATISFACTION_ENTRIES = ["1003", "1004", "1005", "1006"]

_LIKERT = [[str(i), None, None] for i in range(1, 6)]
_GRID_COLUMNS = [["1"], ["2"], ["3"], ["4"], ["5"]]


def build_raw_data() -> list[Any]:
    items: list[Any] = [
        [101, "Giới tính", None, 2, [[1001, [["Nam", None, None], ["Nữ", None, None], ["", None, None, None, 1]], 1]]],
        [102, "Có dùng sản phẩm?", None, 2, [[1002, [["Có", None, SECTION_2_ID], ["Không", None, -2]], 1]]],
        [SECTION_2_ID, "Phần 2", None, 8, None, -1],
        [103, "Ma trận hài lòng", None, 7, [
            [int(entry), _GRID_COLUMNS, 1, [f"HL{i + 1}"]] for i, entry in enumerate(SATISFACTION_ENTRIES)
        ]],
        [104, "Kênh biết đến", None, 4, [[1007, [["FB", None, None], ["TikTok", None, None], ["Bạn bè", None, None]], 1]]],
        [SECTION_3_ID, "Phần 3", None, 8, None],
        [105, "Góp ý", None, 1, [[1008, None, 0]]],
        [106, "Mức độ quay lại", None, 5, [[1009, _LIKERT, 1, ["Thấp", "Cao"]]]],
    ]
    form_info = ["Mô tả", items, None, None, None, None, None, None, "Khảo sát thử"]
    return [None, form_info, None, "file-name", *([None] * 10), "-123456"]


def build_html(fbzx: str = "-987") -> str:
    data = json.dumps(build_raw_data(), ensure_ascii=False)
    return (
        f'<html><body><input type="hidden" name="fbzx" value="{fbzx}">'
        f"<script>var FB_PUBLIC_LOAD_DATA_ = {data};</script></body></html>"
    )


FINAL_URL = "https://docs.google.com/forms/d/e/ABC/viewform?usp=sf_link"
