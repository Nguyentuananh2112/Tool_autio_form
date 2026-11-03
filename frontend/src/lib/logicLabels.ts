import type { ParsedQuestion } from '@/types/form';
import type { Consistency, KeySlot, KeyState, LogicRule, RuleStrength, ThenOp } from '@/types/logic';

import { questionCode } from './questions';

/** Mã ngắn hiển thị cho câu hỏi: "C10" / "C10 · Uy tín" (hàng ma trận) / "Câu 3". */
export function questionShortLabel(question: ParsedQuestion | undefined, index = 0): string {
  if (!question) return '?';
  const code = questionCode(question) ?? `Câu ${index + 1}`;
  return question.row_label ? `${code} · ${question.row_label}` : code;
}

export function questionFullTitle(question: ParsedQuestion | undefined): string {
  if (!question) return 'Câu không còn trong form';
  return question.row_label ? `${question.grid_title ?? question.title} — ${question.row_label}` : question.title;
}

export const CONSISTENCY_LEVELS: { value: Consistency; label: string; hint: string }[] = [
  { value: 'VARIED', label: 'Đa dạng', hint: 'Mỗi người chấm các câu khá khác nhau; chỉ chặn trường hợp ngược hẳn (5 với 1).' },
  { value: 'MODERATE', label: 'Vừa phải', hint: 'Phần lớn người chấm các câu lệch nhau ≤ 1 điểm, thỉnh thoảng 2 điểm — giống người thật.' },
  { value: 'UNIFORM', label: 'Rất đồng đều', hint: 'Các câu gần như cùng mức; số liệu đẹp nhưng dễ bị nghi là điền máy.' },
];

export function ruleLevel(rule: Pick<LogicRule, 'then_op' | 'strength'>): { label: string; tone: 'accent' | 'bad' | 'neutral' } {
  if (rule.strength === 'USUALLY') return { label: rule.then_op === 'IS' ? 'Thường là (75%)' : 'Thường không (75%)', tone: 'neutral' };
  return rule.then_op === 'IS' ? { label: 'Luôn', tone: 'accent' } : { label: 'Không bao giờ', tone: 'bad' };
}

/** Ba lựa chọn mức độ trong hộp thoại sửa ràng buộc. */
export const RULE_LEVELS: { id: string; label: string; then_op: ThenOp; strength: RuleStrength }[] = [
  { id: 'always', label: 'Luôn là', then_op: 'IS', strength: 'ALWAYS' },
  { id: 'never', label: 'Không bao giờ là', then_op: 'IS_NOT', strength: 'ALWAYS' },
  { id: 'usually', label: 'Thường là (75%)', then_op: 'IS', strength: 'USUALLY' },
  { id: 'rarely', label: 'Thường không là (75%)', then_op: 'IS_NOT', strength: 'USUALLY' },
];

export const KEY_SLOT_LABELS: Record<KeySlot, string> = {
  USER: 'Key riêng của bạn',
  SHARED: 'Key chung của app',
  BACKUP: 'Key dự phòng',
};

export const KEY_STATE_LABELS: Record<KeyState, { label: string; tone: 'neutral' | 'bad' | 'ok' }> = {
  MISSING: { label: 'Chưa có', tone: 'neutral' },
  EXHAUSTED: { label: 'Hết lượt', tone: 'bad' },
  INVALID: { label: 'Không hợp lệ', tone: 'bad' },
  OK: { label: 'Dùng được', tone: 'ok' },
};

export const VIOLATION_KIND_LABELS = {
  RULE: 'Vi phạm ràng buộc',
  EXCLUSIVE: 'Ô loại trừ đi kèm ô khác',
  SPREAD: 'Các câu cùng thái độ lệch quá xa',
} as const;
