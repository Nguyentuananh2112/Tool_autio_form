import { cn } from '@/lib/cn';

export function ProgressBar({ value, max = 100, label, tone = 'accent', size = 'md' }: {
  value: number;
  max?: number;
  label: string;
  tone?: 'accent' | 'ok' | 'warn' | 'bad';
  size?: 'sm' | 'md' | 'lg';
}) {
  const percent = max > 0 ? Math.min(100, Math.max(0, (value / max) * 100)) : 0;
  const fill = { accent: 'bg-accent', ok: 'bg-ok', warn: 'bg-warn', bad: 'bg-bad' }[tone];
  const height = { sm: 'h-1.5', md: 'h-2', lg: 'h-3' }[size];
  return (
    <div role="progressbar" aria-label={label} aria-valuemin={0} aria-valuemax={max} aria-valuenow={value} className={cn('overflow-hidden rounded-full bg-sunken', height)}>
      <div className={cn('h-full transition-[width] duration-300', fill)} style={{ width: `${percent}%` }} />
    </div>
  );
}
