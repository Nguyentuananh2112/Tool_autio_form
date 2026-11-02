import type { ReactNode } from 'react';

import { cn } from '@/lib/cn';

export type BadgeTone = 'neutral' | 'accent' | 'warn' | 'ok' | 'bad';

const TONES: Record<BadgeTone, string> = {
  neutral: 'bg-sunken text-muted',
  accent: 'bg-accent-soft text-accent',
  warn: 'bg-warn-soft text-warn',
  ok: 'bg-ok-soft text-ok',
  bad: 'bg-bad-soft text-bad',
};

export function Badge({ tone = 'neutral', dot = false, children, className }: {
  tone?: BadgeTone;
  dot?: boolean;
  children: ReactNode;
  className?: string;
}) {
  return (
    <span className={cn('inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-semibold', TONES[tone], className)}>
      {dot && <span aria-hidden className="size-1.5 rounded-full bg-current" />}
      {children}
    </span>
  );
}

/** Nhãn nhỏ dạng thẻ (mã câu, loại câu). */
export function Tag({ children, mono = false, tone = 'neutral' }: { children: ReactNode; mono?: boolean; tone?: BadgeTone }) {
  return (
    <span className={cn('rounded-md px-2 py-0.5 text-xs', TONES[tone], mono && 'font-mono font-medium text-ink')}>{children}</span>
  );
}
