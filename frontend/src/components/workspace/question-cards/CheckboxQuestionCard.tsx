import { useEffect, useId } from 'react';

import { Badge } from '@/components/ui/Badge';
import { useQuestionRule } from '@/hooks/useQuestionRule';
import { detectMaxChecked } from '@/lib/questions';
import { OTHER_OPTION_VALUE, type ParsedQuestion } from '@/types/form';

import { LinesEditor } from '../weights/LinesEditor';
import { WeightSliderRow } from '../weights/WeightSliderRow';
import { QuestionCardFrame } from './QuestionCardFrame';

/** Hộp kiểm: mỗi ô một xác suất độc lập + giới hạn số ô được tích. */
export function CheckboxQuestionCard({ formId, question }: { formId: string; question: ParsedQuestion }) {
  const { rule, weights, update, setWeight } = useQuestionRule(formId, question);
  const minId = useId();
  const maxId = useId();
  const detectedMax = detectMaxChecked(question);
  const otherOn = (weights[OTHER_OPTION_VALUE] ?? 0) > 0;

  // Tự áp dụng "tối đa N" đọc được từ tiêu đề lần đầu (người dùng vẫn sửa được)
  useEffect(() => {
    if (detectedMax && rule?.max_checked === undefined) update({ max_checked: detectedMax, min_checked: question.is_required ? 1 : 0 });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [detectedMax]);

  const setLimit = (key: 'min_checked' | 'max_checked', raw: string) => {
    const value = Math.max(0, Math.min(question.options.length, Number(raw) || 0));
    update({ [key]: key === 'max_checked' && value === 0 ? null : value });
  };

  return (
    <QuestionCardFrame question={question} state={otherOn && !rule?.other_text_pool?.length ? 'missing' : 'normal'}>
      <p className="m-0 text-[13px] text-muted">Mỗi ô có xác suất được tích riêng, không cần cộng đủ 100%.</p>
      <div className="flex flex-col gap-2.5">
        {question.options.map((option) => (
          <WeightSliderRow key={option.value} label={option.label} value={weights[option.value] ?? 0} onChange={(p) => setWeight(option.value, p)} />
        ))}
      </div>
      {otherOn && (
        <LinesEditor label="Nội dung cho “Mục khác”" value={rule?.other_text_pool ?? []} rows={2} onChange={(lines) => update({ other_text_pool: lines })} />
      )}
      <div className="flex flex-wrap items-center gap-3 border-t border-line pt-3 text-sm">
        <label htmlFor={minId}>Số ô được tích: từ</label>
        <input id={minId} type="number" min={0} value={rule?.min_checked ?? (question.is_required ? 1 : 0)} onChange={(e) => setLimit('min_checked', e.target.value)} className="w-16 rounded-lg border border-line bg-bg px-2.5 py-2" />
        <label htmlFor={maxId}>đến</label>
        <input id={maxId} type="number" min={1} value={rule?.max_checked ?? question.options.length} onChange={(e) => setLimit('max_checked', e.target.value)} className="w-16 rounded-lg border border-line bg-bg px-2.5 py-2" />
        {detectedMax && <Badge tone="accent">Tự nhận “tối đa {detectedMax}” từ tiêu đề</Badge>}
      </div>
    </QuestionCardFrame>
  );
}
