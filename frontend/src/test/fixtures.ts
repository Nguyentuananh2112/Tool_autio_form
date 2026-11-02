import type { ParsedFormStructure, ParsedOption, ParsedQuestion } from '@/types/form';

const option = (value: string, jump: number | null = null, isOther = false): ParsedOption => ({
  label: isOther ? 'Mục khác' : value,
  value: isOther ? '__other_option__' : value,
  is_other: isOther,
  jump_to_section_id: jump,
});

const question = (entry: string, title: string, page: number, options: ParsedOption[], extra: Partial<ParsedQuestion> = {}): ParsedQuestion => ({
  item_id: Number(entry),
  entry_id: entry,
  title,
  description: null,
  type_id: 2,
  type_name: 'MULTIPLE_CHOICE',
  page_index: page,
  is_required: true,
  options,
  scale_low_label: null,
  scale_high_label: null,
  grid_item_id: null,
  grid_title: null,
  row_label: null,
  is_multi_select: false,
  ...extra,
});

/** Giống form mẫu ở backend: A3 rẽ nhánh sang B (→ D) hoặc C. */
export function sampleStructure(): ParsedFormStructure {
  return {
    title: 'Form thử',
    description: null,
    view_url: 'https://example.invalid/viewform',
    submit_url: 'https://example.invalid/formResponse',
    fbzx: null,
    total_pages: 4,
    sections: [
      { page_index: 0, section_item_id: null, title: 'A. Chung', description: null, navigation_action: 'NEXT_PAGE', jump_to_section_id: null },
      { page_index: 1, section_item_id: 11, title: 'B. Thói quen', description: null, navigation_action: 'GO_TO_PAGE', jump_to_section_id: 33 },
      { page_index: 2, section_item_id: 22, title: 'C. Lý do', description: null, navigation_action: 'NEXT_PAGE', jump_to_section_id: null },
      { page_index: 3, section_item_id: 33, title: 'D. Góp ý', description: null, navigation_action: 'NEXT_PAGE', jump_to_section_id: null },
    ],
    questions: [
      question('1', 'A1: Giới tính?', 0, [option('Nam'), option('Nữ'), option('', null, true)]),
      question('2', 'A3: Có uống cà phê?', 0, [option('Có', 11), option('Không', 22)]),
      question('3', 'B1: Mua ở đâu? (Chọn tối đa 2)', 1, [option('Quán'), option('Nhà')], { type_id: 4, type_name: 'CHECKBOX', is_multi_select: true }),
      question('4', 'C1: Vì sao?', 2, [option('Đắng'), option('Trà')]),
      question('5', 'D1: Góp ý?', 3, [], { type_id: 0, type_name: 'SHORT_ANSWER' }),
    ],
  };
}
