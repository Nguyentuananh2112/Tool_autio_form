"""Chuyển các phản hồi thành bảng dữ liệu kiểu SPSS (1 dòng / phản hồi)."""

from __future__ import annotations

from collections.abc import Sequence

import pandas as pd

from app.schemas.form_schema import OTHER_OPTION_VALUE, ParsedFormStructure, ParsedOption, ParsedQuestion
from app.services.spss.answers import GeneratedResponse


def responses_to_dataframe(
    structure: ParsedFormStructure, responses: Sequence[GeneratedResponse], *, numeric: bool = True
) -> pd.DataFrame:
    """Checkbox tách thành các biến nhị phân 0/1; câu một lựa chọn dùng mã số khi `numeric=True`."""
    used_names: set[str] = set()

    def column_name(base: str, entry_id: str) -> str:
        name = base if base not in used_names else f"{base} ({entry_id})"
        used_names.add(name)
        return name

    column_specs: list[tuple[str, ParsedQuestion, ParsedOption | None]] = []
    for question in structure.questions:
        if question.is_multi_select:
            for option in question.options:
                column_specs.append((column_name(f"{question.title} [{option.label}]", question.entry_id), question, option))
        else:
            column_specs.append((column_name(question.title, question.entry_id), question, None))

    records: list[dict[str, object]] = []
    for response in responses:
        record: dict[str, object] = {"sequence_number": response.sequence_number, "page_history": response.page_history_str}
        for name, question, option in column_specs:
            answer = response.answers.get(question.entry_id)
            if answer is None:
                record[name] = None
            elif option is not None:
                record[name] = 1 if option.value in answer.values else 0
            elif numeric and answer.numeric_value is not None:
                record[name] = answer.numeric_value
            elif answer.values and answer.values[0] == OTHER_OPTION_VALUE:
                record[name] = answer.other_text
            else:
                record[name] = ", ".join(answer.values)
        records.append(record)

    return pd.DataFrame.from_records(records, columns=["sequence_number", "page_history"] + [c[0] for c in column_specs])
