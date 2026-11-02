import { HelpCircle } from 'lucide-react';
import { useId, useState } from 'react';

/** Nút "?" giải thích thuật ngữ bằng lời thường (quy tắc 4 trong CLAUDE.md). */
export function InfoHint({ term, children }: { term: string; children: string }) {
  const [open, setOpen] = useState(false);
  const id = useId();
  return (
    <span className="relative inline-flex">
      <button
        type="button"
        aria-label={`Giải thích: ${term}`}
        aria-expanded={open}
        aria-controls={id}
        onClick={() => setOpen((v) => !v)}
        onBlur={() => setOpen(false)}
        className="inline-flex size-6 cursor-pointer items-center justify-center rounded-full text-muted hover:text-accent"
      >
        <HelpCircle aria-hidden className="size-4" />
      </button>
      {open && (
        <span id={id} role="tooltip" className="absolute left-1/2 top-7 z-40 w-64 -translate-x-1/2 rounded-lg bg-ink px-3 py-2 text-[13px] font-normal leading-relaxed text-surface shadow-lg">
          <strong className="block">{term}</strong>
          {children}
        </span>
      )}
    </span>
  );
}
