import type { ParsedFormStructure, ParsedQuestion } from '@/types/form';

import { isSingleChoice, questionCode, scaleValues } from './questions';

/** Một "bộ lọc" trong hộp thoại SPSS: một câu lưới hoặc các câu thang đo lẻ có cùng thang. */
export interface CandidateGroup {
  key: string;
  label: string;
  scaleKey: string;
  questions: ParsedQuestion[];
}

const scaleKeyOf = (q: ParsedQuestion): string => scaleValues(q).join(',');
/** "B2: Bạn hài lòng…" → "Bạn hài lòng…" (mã đã hiện riêng ở nhãn). */
const CODE_PREFIX = /^\s*[A-Za-z]{1,3}\d{1,3}\s*[:.)-]?\s*/;

/** Câu đủ điều kiện vào nhóm SPSS: một lựa chọn; hàng lưới ≥ 2 mức, câu lẻ ≥ 3 mức (backend chấp nhận ≥ 2). */
export function spssCandidates(structure: ParsedFormStructure): CandidateGroup[] {
  // Câu lẻ cần ≥ 3 mức (VD Likert) — câu 2 lựa chọn như Giới tính không phải thang đo
  const eligible = structure.questions.filter(
    (q) => isSingleChoice(q) && scaleValues(q).length >= (q.grid_item_id !== null ? 2 : 3),
  );
  const groups = new Map<string, CandidateGroup>();
  for (const question of eligible) {
    const key = question.grid_item_id !== null ? `grid-${question.grid_item_id}` : `scale-${scaleKeyOf(question)}`;
    const existing = groups.get(key);
    if (existing) {
      existing.questions.push(question);
      continue;
    }
    const code = questionCode(question);
    const values = scaleValues(question);
    const label = question.grid_item_id !== null
      ? `${code ? `${code} · ` : ''}${(question.grid_title ?? '').replace(CODE_PREFIX, '').slice(0, 30)}`
      : `Câu lẻ thang ${values[0]}–${values[values.length - 1]}`;
    groups.set(key, { key, label, scaleKey: scaleKeyOf(question), questions: [question] });
  }
  // Câu lưới (thường là các biến Likert của một nhân tố) lên trước, nhiều biến hơn lên trước
  return [...groups.values()].sort((a, b) => Number(b.key.startsWith('grid-')) - Number(a.key.startsWith('grid-')) || b.questions.length - a.questions.length);
}

export const itemLabel = (q: ParsedQuestion): string => q.row_label ?? q.title;

export function scaleRange(q: ParsedQuestion): [number, number] {
  const values = scaleValues(q);
  return [values[0] ?? 1, values[values.length - 1] ?? 5];
}
