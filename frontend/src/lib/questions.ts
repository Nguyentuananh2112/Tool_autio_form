import { type ParsedFormStructure, type ParsedQuestion, QuestionType } from '@/types/form';

export const TYPE_LABELS: Record<string, string> = {
  SHORT_ANSWER: 'Tự luận ngắn',
  PARAGRAPH: 'Tự luận dài',
  MULTIPLE_CHOICE: 'Trắc nghiệm',
  DROPDOWN: 'Danh sách thả xuống',
  CHECKBOX: 'Hộp kiểm (chọn nhiều)',
  LINEAR_SCALE: 'Thang đo',
  GRID: 'Lưới trắc nghiệm',
  CHECKBOX_GRID: 'Lưới hộp kiểm',
  DATE: 'Ngày',
  TIME: 'Giờ',
  RATING: 'Đánh giá (sao)',
};

export const isText = (q: ParsedQuestion): boolean =>
  q.type_id === QuestionType.SHORT_ANSWER || q.type_id === QuestionType.PARAGRAPH;

export const isDateOrTime = (q: ParsedQuestion): boolean => q.type_id === QuestionType.DATE || q.type_id === QuestionType.TIME;

export const isSingleChoice = (q: ParsedQuestion): boolean =>
  !q.is_multi_select && q.options.length > 0 && !isText(q) && !isDateOrTime(q);

export const isBranching = (q: ParsedQuestion): boolean =>
  q.options.some((o) => o.jump_to_section_id !== null && o.jump_to_section_id !== -2);

export const choiceOptions = (q: ParsedQuestion) => q.options.filter((o) => !o.is_other);

/** Mã câu ở đầu tiêu đề, VD "A2: Độ tuổi..." → "A2". */
export function questionCode(q: ParsedQuestion): string | null {
  const source = q.grid_title ?? q.title;
  const match = /^\s*([A-Za-z]{1,3}\d{1,3})(?=$|[\s:.\-_)\]])/.exec(source);
  return match?.[1]?.toUpperCase() ?? null;
}

/** "Chọn tối đa 3" chỉ nằm trong tiêu đề, không phải validation của Google (dev-notes SPEC-009). */
export function detectMaxChecked(q: ParsedQuestion): number | null {
  const match = /tối đa\s*(\d+)/i.exec(q.title);
  return match?.[1] ? Number(match[1]) : null;
}

/** Thang đo dạng số: dùng giá trị thật nếu là dãy số nguyên liên tiếp, ngược lại 1..K (giống backend). */
export function scaleValues(q: ParsedQuestion): number[] {
  const options = choiceOptions(q);
  const numbers = options.map((o) => Number(o.value.trim()));
  const consecutive = numbers.every((n, i) => Number.isInteger(n) && (i === 0 || n - (numbers[i - 1] ?? n) === 1));
  return options.length > 0 && consecutive ? numbers : options.map((_, i) => i + 1);
}

export function questionsByPage(structure: ParsedFormStructure): Map<number, ParsedQuestion[]> {
  const pages = new Map<number, ParsedQuestion[]>();
  for (const question of structure.questions) {
    pages.set(question.page_index, [...(pages.get(question.page_index) ?? []), question]);
  }
  return pages;
}

export function sectionTitle(structure: ParsedFormStructure, sectionId: number | null): string {
  if (sectionId === -3) return 'Gửi biểu mẫu';
  const section = structure.sections.find((s) => s.section_item_id === sectionId);
  return section ? section.title : 'Trang tiếp theo';
}
