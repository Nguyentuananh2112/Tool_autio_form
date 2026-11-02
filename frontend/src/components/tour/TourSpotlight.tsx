import { createPortal } from 'react-dom';

import { computePopoverPosition } from './popoverPosition';
import { TourPopover } from './TourPopover';
import type { TourStep } from './tourSteps';
import { useTargetRect } from './useTargetRect';

const PADDING = 6;

/** Làm sáng đúng một tính năng (phần còn lại tối đi) + đặt bong bóng giải thích cạnh nó. */
export function TourSpotlight({ step, index, total, onNext, onBack, onSkip }: {
  step: TourStep;
  index: number;
  total: number;
  onNext: () => void;
  onBack: () => void;
  onSkip: () => void;
}) {
  const { rect, missing } = useTargetRect(step.target);
  const vw = window.innerWidth;
  const vh = window.innerHeight;

  // Không tìm thấy phần tử (VD form không có câu rẽ nhánh): hiện bong bóng giữa màn hình
  const position = rect
    ? computePopoverPosition(rect, step.placement, vw, vh)
    : { top: Math.max(16, vh / 2 - 120), left: Math.max(16, vw / 2 - 170) };

  return createPortal(
    <>
      {/* Lớp chặn bấm nhầm vào giao diện phía sau */}
      <div aria-hidden className="fixed inset-0 z-[60]" style={{ background: rect ? 'transparent' : 'var(--dim)' }} />
      {rect && (
        <div
          aria-hidden
          className="pointer-events-none fixed z-[61] rounded-xl transition-all duration-200"
          style={{
            top: rect.top - PADDING,
            left: rect.left - PADDING,
            width: rect.width + PADDING * 2,
            height: rect.height + PADDING * 2,
            boxShadow: '0 0 0 3px var(--accent), 0 0 0 9999px var(--dim)',
          }}
        />
      )}
      {(rect || missing) && (
        <TourPopover
          title={step.title}
          text={step.text}
          index={index}
          total={total}
          style={{ top: position.top, left: position.left }}
          onNext={onNext}
          onBack={onBack}
          onSkip={onSkip}
        />
      )}
    </>,
    document.body,
  );
}
