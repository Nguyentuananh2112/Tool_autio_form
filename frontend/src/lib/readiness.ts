import type { QuestionRuleConfig, SpssGroupConfig } from '@/types/campaign';
import { OTHER_OPTION_VALUE, type ParsedFormStructure, type ParsedQuestion } from '@/types/form';

import { isText } from './questions';

/** Bản sao phía giao diện của các kiểm tra quan trọng nhất ở backend (validation.py) — để khóa nút Bắt đầu kèm lý do. */
export interface ReadinessIssue {
  entryId: string;
  pageIndex: number;
  message: string;
}

export interface Readiness {
  issues: ReadinessIssue[];
  configuredCount: number;
  totalCount: number;
  missingTextCount: number;
}

function questionIssue(question: ParsedQuestion, rule: QuestionRuleConfig | undefined): string | null {
  if (rule?.strategy === 'SKIP') return question.is_required ? 'câu bắt buộc không thể bỏ qua' : null;
  if (rule?.strategy === 'FIXED') return null;
  if (isText(question)) {
    return question.is_required && !(rule?.text_pool && rule.text_pool.length > 0) ? 'chưa có câu trả lời mẫu' : null;
  }
  const otherWeight = rule?.weights?.[OTHER_OPTION_VALUE] ?? 0;
  if (otherWeight > 0 && !(rule?.other_text_pool && rule.other_text_pool.length > 0)) {
    return '“Mục khác” > 0% nhưng chưa có câu trả lời mẫu';
  }
  if (!question.is_multi_select && rule?.weights && Object.keys(rule.weights).length > 0) {
    const total = Object.values(rule.weights).reduce((s, w) => s + w, 0);
    if (total <= 0 && question.is_required) return 'tổng tỷ lệ bằng 0';
  }
  return null;
}

export function computeReadiness(
  structure: ParsedFormStructure,
  rules: Record<string, QuestionRuleConfig>,
  groups: SpssGroupConfig[],
): Readiness {
  const grouped = new Set(groups.flatMap((g) => g.entries));
  const issues: ReadinessIssue[] = [];
  let missingTextCount = 0;
  for (const question of structure.questions) {
    if (grouped.has(question.entry_id)) continue;
    const message = questionIssue(question, rules[question.entry_id]);
    if (message) {
      issues.push({ entryId: question.entry_id, pageIndex: question.page_index, message: `${question.title}: ${message}` });
      if (isText(question)) missingTextCount += 1;
    }
  }
  // Câu bắt buộc app chưa điền được: Google sẽ từ chối mọi phản hồi (BUG-017) → không cho chạy
  for (const item of structure.unsupported_items ?? []) {
    if (item.is_required) {
      issues.push({ entryId: `unsupported-${item.item_id}`, pageIndex: item.page_index, message: `${item.title}: kiểu câu hỏi app chưa điền được` });
    }
  }
  return {
    issues,
    configuredCount: structure.questions.length - issues.length,
    totalCount: structure.questions.length,
    missingTextCount,
  };
}
