import { type CSSProperties, useEffect, useId, useRef } from 'react';

import { Button } from '@/components/ui/Button';

import { POPOVER_WIDTH } from './popoverPosition';

/** Bong bóng giải thích của tour (artboard TourPopover). */
export function TourPopover({ title, text, index, total, style, onNext, onBack, onSkip }: {
  title: string;
  text: string;
  index: number;
  total: number;
  style: CSSProperties;
  onNext: () => void;
  onBack: () => void;
  onSkip: () => void;
}) {
  const titleId = useId();
  const textId = useId();
  const nextRef = useRef<HTMLButtonElement>(null);
  const last = index === total - 1;

  useEffect(() => {
    nextRef.current?.focus();
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onSkip();
    };
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [onSkip]);

  return (
    <section
      role="dialog"
      aria-labelledby={titleId}
      aria-describedby={textId}
      style={{ ...style, width: POPOVER_WIDTH }}
      className="fixed z-[70] flex flex-col gap-2.5 rounded-[14px] border border-accent-line bg-surface p-4.5 text-ink shadow-2xl"
    >
      <div className="flex items-center justify-between gap-2">
        <span className="text-xs font-semibold text-accent">Bước {index + 1} / {total}</span>
        <button type="button" onClick={onSkip} className="min-h-8 cursor-pointer border-0 bg-transparent px-1.5 text-xs font-medium text-muted hover:text-ink">Bỏ qua tour</button>
      </div>
      <h2 id={titleId} className="m-0 text-[17px] font-bold">{title}</h2>
      <p id={textId} className="m-0 text-sm leading-relaxed text-muted">{text}</p>
      <div aria-hidden className="h-1 overflow-hidden rounded-full bg-sunken"><div className="h-full bg-accent" style={{ width: `${((index + 1) / total) * 100}%` }} /></div>
      <div className="flex justify-between gap-2">
        <Button size="sm" onClick={onBack} disabled={index === 0}>Quay lại</Button>
        <Button ref={nextRef} size="sm" variant="primary" onClick={onNext}>{last ? 'Hoàn tất' : 'Tiếp'}</Button>
      </div>
    </section>
  );
}
