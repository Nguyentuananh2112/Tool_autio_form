import { useCallback } from 'react';

import { presetWeights } from '@/lib/presets';
import { choiceOptions } from '@/lib/questions';
import { useFormConfig, useFormConfigStore } from '@/store/formConfigStore';
import type { QuestionRuleConfig } from '@/types/campaign';
import type { ParsedQuestion } from '@/types/form';

const DEFAULT_CHECKBOX_PERCENT = 50;

/** Trọng số đang áp dụng: theo luật đã lưu, hoặc mặc định giống backend (đều nhau / 50% cho hộp kiểm). */
export function effectiveWeights(question: ParsedQuestion, rule: QuestionRuleConfig | undefined): Record<string, number> {
  if (rule?.weights && Object.keys(rule.weights).length > 0) {
    return Object.fromEntries(question.options.map((o) => [o.value, rule.weights?.[o.value] ?? 0]));
  }
  if (question.is_multi_select) {
    return Object.fromEntries(question.options.map((o) => [o.value, o.is_other ? 0 : DEFAULT_CHECKBOX_PERCENT]));
  }
  const uniform = presetWeights('uniform', choiceOptions(question).length);
  let index = 0;
  return Object.fromEntries(question.options.map((o) => [o.value, o.is_other ? 0 : uniform[index++] ?? 0]));
}

export function useQuestionRule(formId: string, question: ParsedQuestion) {
  const config = useFormConfig(formId);
  const updateRule = useFormConfigStore((s) => s.updateRule);
  const rule = config.rules[question.entry_id];
  const base: QuestionRuleConfig = rule ?? { entry_id: question.entry_id, question_type: question.type_id };

  const update = useCallback(
    (patch: Partial<QuestionRuleConfig>) => updateRule(formId, { ...base, ...patch, entry_id: question.entry_id, question_type: question.type_id }),
    [base, formId, question.entry_id, question.type_id, updateRule],
  );

  return {
    rule,
    weights: effectiveWeights(question, rule),
    inGroup: config.groups.find((g) => g.entries.includes(question.entry_id)) ?? null,
    update,
    setWeight: (value: string, percent: number) =>
      update({ weights: { ...effectiveWeights(question, rule), [value]: percent } }),
  };
}
