import { AlertTriangle, CheckCircle2, Info, XCircle } from 'lucide-react';
import type { ReactNode } from 'react';

import { cn } from '@/lib/cn';

export type AlertTone = 'info' | 'warn' | 'ok' | 'bad';

const STYLES: Record<AlertTone, { box: string; Icon: typeof Info }> = {
  info: { box: 'bg-accent-soft text-accent', Icon: Info },
  warn: { box: 'bg-warn-soft text-warn', Icon: AlertTriangle },
  ok: { box: 'bg-ok-soft text-ok', Icon: CheckCircle2 },
  bad: { box: 'bg-bad-soft text-bad', Icon: XCircle },
};

export function Alert({ tone = 'info', title, children, action, className }: {
  tone?: AlertTone;
  title?: ReactNode;
  children?: ReactNode;
  action?: ReactNode;
  className?: string;
}) {
  const { box, Icon } = STYLES[tone];
  return (
    <div role={tone === 'bad' || tone === 'warn' ? 'alert' : 'status'} className={cn('flex flex-wrap items-start gap-3 rounded-xl px-4 py-3 text-sm', box, className)}>
      <Icon aria-hidden className="mt-0.5 size-5 shrink-0" />
      <div className="flex min-w-[240px] flex-1 flex-col gap-1">
        {title && <strong className="font-semibold">{title}</strong>}
        {children && <div className="leading-relaxed">{children}</div>}
      </div>
      {action}
    </div>
  );
}

/** Hiện lỗi API kèm danh sách chi tiết. */
export function ErrorAlert({ error }: { error: { message: string; errors?: string[] } | null }) {
  if (!error) return null;
  return (
    <Alert tone="bad" title={error.message}>
      {error.errors && error.errors.length > 0 && (
        <ul className="m-0 list-disc pl-5">
          {error.errors.slice(0, 8).map((e) => <li key={e}>{e}</li>)}
          {error.errors.length > 8 && <li>… và {error.errors.length - 8} lỗi khác</li>}
        </ul>
      )}
    </Alert>
  );
}
