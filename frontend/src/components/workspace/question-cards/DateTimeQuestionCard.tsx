import { useId } from 'react';

import { Field, TextInput } from '@/components/ui/Field';
import { useQuestionRule } from '@/hooks/useQuestionRule';
import { QuestionType, type ParsedQuestion } from '@/types/form';

import { QuestionCardFrame } from './QuestionCardFrame';

/** Câu Ngày / Giờ: chọn ngẫu nhiên trong khoảng (mặc định: 1 năm gần nhất / 08:00–21:00). */
export function DateTimeQuestionCard({ formId, question }: { formId: string; question: ParsedQuestion }) {
  const { rule, update } = useQuestionRule(formId, question);
  const fromId = useId();
  const toId = useId();
  const isDate = question.type_id === QuestionType.DATE;
  const [fromKey, toKey] = isDate ? (['date_start', 'date_end'] as const) : (['time_start', 'time_end'] as const);

  return (
    <QuestionCardFrame question={question}>
      <p className="m-0 text-[13px] text-muted">App chọn ngẫu nhiên một {isDate ? 'ngày' : 'giờ'} trong khoảng dưới đây. Để trống = dùng mặc định.</p>
      <div className="flex flex-wrap gap-3">
        <div className="min-w-[180px] flex-1">
          <Field label="Từ" htmlFor={fromId}>
            <TextInput id={fromId} type={isDate ? 'date' : 'time'} value={rule?.[fromKey] ?? ''} onChange={(e) => update({ [fromKey]: e.target.value || undefined })} />
          </Field>
        </div>
        <div className="min-w-[180px] flex-1">
          <Field label="Đến" htmlFor={toId}>
            <TextInput id={toId} type={isDate ? 'date' : 'time'} value={rule?.[toKey] ?? ''} onChange={(e) => update({ [toKey]: e.target.value || undefined })} />
          </Field>
        </div>
      </div>
    </QuestionCardFrame>
  );
}
