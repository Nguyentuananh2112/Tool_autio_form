import type { ReactNode } from 'react';

import { Tag } from '@/components/ui/Badge';
import { cn } from '@/lib/cn';
import { questionCode, TYPE_LABELS } from '@/lib/questions';
import type { ParsedQuestion } from '@/types/form';

export type CardState = 'normal' | 'branch' | 'missing';

/** Khung chung cho mọi thẻ câu hỏi: mã, loại, bắt buộc, tiêu đề; phần thân do từng loại câu tự vẽ. */
export function QuestionCardFrame({ question, state = 'normal', badges, children, tourId }: {
  question: ParsedQuestion;
  state?: CardState;
  badges?: ReactNode;
  children: ReactNode;
  tourId?: string;
}) {
  const code = questionCode(question);
  return (
    <article
      id={`q-${question.entry_id}`}
      data-tour={tourId}
      className={cn(
        'flex flex-col gap-3.5 rounded-xl border bg-surface px-5 py-4',
        state === 'missing' ? 'border-warn' : state === 'branch' ? 'border-accent-line' : 'border-line',
      )}
    >
      <div className="flex flex-wrap gap-1.5">
        {code && <Tag mono>{code}</Tag>}
        <Tag>{TYPE_LABELS[question.type_name] ?? question.type_name}</Tag>
        {question.is_required && <Tag tone="bad">Bắt buộc</Tag>}
        {badges}
      </div>
      <h3 className="m-0 whitespace-pre-line text-base font-semibold">{question.grid_title ? question.row_label : question.title}</h3>
      {children}
    </article>
  );
}
