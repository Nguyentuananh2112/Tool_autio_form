import { Check, HelpCircle } from 'lucide-react';
import { Fragment } from 'react';
import { Link } from 'react-router-dom';

import { cn } from '@/lib/cn';

const STEPS = ['Phân tích form', 'Cấu hình câu trả lời', 'Soát logic', 'Chạy & theo dõi'];

/** Thanh 4 bước ① Phân tích → ② Cấu hình → ③ Soát logic → ④ Chạy (artboard 2 + 11, quy tắc 4 & 6). */
export function StepIndicator({ current }: { current: 1 | 2 | 3 | 4 }) {
  return (
    <ol aria-label="Các bước" data-tour="steps" className="m-0 flex list-none flex-wrap items-center gap-2 self-start rounded-[10px] bg-surface p-0 px-3 py-2 text-[13px]">
      {STEPS.map((label, index) => {
        const step = index + 1;
        const done = step < current;
        const active = step === current;
        return (
          <Fragment key={label}>
            {index > 0 && <li aria-hidden className="h-0.5 w-8 bg-line" />}
            <li aria-current={active ? 'step' : undefined} className={cn('inline-flex items-center gap-2', done && 'font-semibold text-ok', active && 'font-semibold text-accent', !done && !active && 'text-muted')}>
              <span aria-hidden className={cn('inline-flex size-6 items-center justify-center rounded-full', done && 'bg-ok-soft', active && 'bg-accent text-accent-ink', !done && !active && 'border border-line')}>
                {done ? <Check className="size-3.5" /> : step}
              </span>
              {label}
            </li>
          </Fragment>
        );
      })}
      <li className="ml-2">
        <Link to="/help" className="inline-flex min-h-8 items-center gap-1.5 font-semibold text-accent no-underline">
          <HelpCircle aria-hidden className="size-4" />Màn hình này dùng thế nào?
        </Link>
      </li>
    </ol>
  );
}
