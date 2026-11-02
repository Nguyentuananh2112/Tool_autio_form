import type { HTMLAttributes, ReactNode } from 'react';

import { cn } from '@/lib/cn';

export function Card({ className, ...rest }: HTMLAttributes<HTMLElement>) {
  return <section className={cn('rounded-xl border border-line bg-surface', className)} {...rest} />;
}

export function CardHeader({ title, description, actions, id }: {
  title: ReactNode;
  description?: ReactNode;
  actions?: ReactNode;
  id?: string;
}) {
  return (
    <div className="flex flex-wrap items-center justify-between gap-3 border-b border-line px-5 py-4">
      <div className="flex flex-col gap-0.5">
        <h2 id={id} className="m-0 text-[17px] font-semibold">{title}</h2>
        {description && <p className="m-0 text-[13px] text-muted">{description}</p>}
      </div>
      {actions}
    </div>
  );
}
