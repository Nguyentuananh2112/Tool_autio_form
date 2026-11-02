"""Tính đường đi rẽ nhánh `pageHistory` (Mục 5.2.C spec, mã rẽ nhánh theo CONF-001)."""

from __future__ import annotations

import logging
from collections.abc import Mapping

from app.schemas.form_schema import BRANCHING_TYPES, NavigationAction, ParsedFormStructure, ParsedQuestion, decode_jump
from app.services.spss.answers import Answer

logger = logging.getLogger(__name__)


class PageNavigator:
    def __init__(self, structure: ParsedFormStructure) -> None:
        self._total_pages = structure.total_pages
        self._questions_by_page: dict[int, list[ParsedQuestion]] = {}
        for question in structure.questions:
            self._questions_by_page.setdefault(question.page_index, []).append(question)
        self._sections_by_page = {section.page_index: section for section in structure.sections}
        self._page_of_section: dict[int, int] = {
            s.section_item_id: s.page_index for s in structure.sections if s.section_item_id is not None
        }
        self._option_jumps: dict[str, dict[str, int | None]] = {
            q.entry_id: {o.value: o.jump_to_section_id for o in q.options}
            for q in structure.questions
            if q.type_id in BRANCHING_TYPES
        }

    def _next_action(self, page_index: int, answers: Mapping[str, Answer]) -> tuple[NavigationAction, int | None]:
        jump: int | None = None
        for question in self._questions_by_page.get(page_index, []):
            jumps = self._option_jumps.get(question.entry_id)
            answer = answers.get(question.entry_id)
            if not jumps or answer is None or not answer.values:
                continue
            option_jump = jumps.get(answer.values[0])
            if option_jump is not None:
                jump = option_jump  # Google Forms áp dụng câu rẽ nhánh cuối cùng trong trang
        if jump is not None:
            return decode_jump(jump)
        section = self._sections_by_page.get(page_index)
        if section is None:
            return NavigationAction.NEXT_PAGE, None
        return section.navigation_action, section.jump_to_section_id

    def page_history(self, answers: Mapping[str, Answer]) -> list[int]:
        """Mô phỏng người điền đi qua các trang theo luật rẽ nhánh."""
        current = 0
        visited = [0]
        visited_set = {0}
        while True:
            action, target = self._next_action(current, answers)
            if action == NavigationAction.SUBMIT:
                break
            next_page = current + 1
            if action == NavigationAction.GO_TO_PAGE and target is not None:
                resolved = self._page_of_section.get(target)
                if resolved is None:
                    logger.warning("Section đích %s không tồn tại, chuyển sang trang kế tiếp", target)
                else:
                    next_page = resolved
            if next_page >= self._total_pages or next_page in visited_set:
                # Hết trang, hoặc nhảy ngược về trang đã đi qua (tránh vòng lặp vô hạn) -> nộp
                break
            visited.append(next_page)
            visited_set.add(next_page)
            current = next_page
        return visited
