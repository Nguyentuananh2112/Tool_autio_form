import type { ReactNode } from 'react';

/** Màn hình/ô trống luôn nói việc tiếp theo (quy tắc 4 trong CLAUDE.md). */
export function EmptyState({ title, description, action }: { title: string; description: string; action?: ReactNode }) {
  return (
    <div className="flex flex-col items-center gap-3 px-6 py-10 text-center">
      <strong className="text-base">{title}</strong>
      <p className="m-0 max-w-md text-sm text-muted">{description}</p>
      {action}
    </div>
  );
}

export function Spinner({ label = 'Đang tải…' }: { label?: string }) {
  return (
    <div role="status" className="flex items-center gap-3 px-2 py-6 text-sm text-muted">
      <span aria-hidden className="size-5 animate-spin rounded-full border-2 border-accent border-r-transparent" />
      {label}
    </div>
  );
}
