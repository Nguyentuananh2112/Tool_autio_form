import { X } from 'lucide-react';
import { useEffect, useId, useRef, type ReactNode } from 'react';
import { createPortal } from 'react-dom';

import { cn } from '@/lib/cn';

/** Hộp thoại modal: Esc để đóng, khóa cuộn nền, đưa focus vào hộp thoại. */
export function Dialog({ open, onClose, title, description, children, footer, size = 'md' }: {
  open: boolean;
  onClose: () => void;
  title: ReactNode;
  description?: ReactNode;
  children: ReactNode;
  footer?: ReactNode;
  size?: 'md' | 'lg' | 'xl';
}) {
  const titleId = useId();
  const panel = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return undefined;
    const previous = document.activeElement as HTMLElement | null;
    panel.current?.focus();
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose();
    };
    document.addEventListener('keydown', onKey);
    const overflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      document.removeEventListener('keydown', onKey);
      document.body.style.overflow = overflow;
      previous?.focus();
    };
  }, [open, onClose]);

  if (!open) return null;
  const width = { md: 'max-w-[620px]', lg: 'max-w-[880px]', xl: 'max-w-[1120px]' }[size];
  return createPortal(
    <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-[var(--dim)] px-4 py-10" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <div
        ref={panel}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        tabIndex={-1}
        className={cn('flex w-full flex-col rounded-2xl border border-line bg-surface shadow-2xl outline-none', width)}
      >
        <header className="flex items-start justify-between gap-4 border-b border-line px-6 py-5">
          <div className="flex flex-col gap-1">
            <h2 id={titleId} className="m-0 text-xl font-bold">{title}</h2>
            {description && <p className="m-0 text-sm text-muted">{description}</p>}
          </div>
          <button type="button" aria-label="Đóng" onClick={onClose} className="flex size-11 shrink-0 cursor-pointer items-center justify-center rounded-[10px] text-muted hover:bg-sunken">
            <X aria-hidden className="size-5" />
          </button>
        </header>
        <div className="px-6 py-5">{children}</div>
        {footer && <footer className="flex flex-wrap justify-end gap-2 border-t border-line px-6 py-4">{footer}</footer>}
      </div>
    </div>,
    document.body,
  );
}
