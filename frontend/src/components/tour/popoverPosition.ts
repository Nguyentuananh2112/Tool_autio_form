import type { Placement } from './tourSteps';

export const POPOVER_WIDTH = 340;
const POPOVER_HEIGHT_GUESS = 240;
const GAP = 16;
const MARGIN = 16;

export interface PopoverPosition {
  top: number;
  left: number;
  placement: Placement;
}

const clamp = (value: number, min: number, max: number) => Math.max(min, Math.min(max, value));

function fits(placement: Placement, rect: DOMRect, vw: number, vh: number): boolean {
  if (placement === 'right') return rect.right + GAP + POPOVER_WIDTH <= vw - MARGIN;
  if (placement === 'left') return rect.left - GAP - POPOVER_WIDTH >= MARGIN;
  if (placement === 'below') return rect.bottom + GAP + POPOVER_HEIGHT_GUESS <= vh - MARGIN;
  return rect.top - GAP - POPOVER_HEIGHT_GUESS >= MARGIN;
}

/** Đặt bong bóng cạnh phần tử theo hướng mong muốn; không đủ chỗ thì thử hướng khác, luôn nằm trong màn hình. */
export function computePopoverPosition(rect: DOMRect, preferred: Placement, vw: number, vh: number): PopoverPosition {
  const order: Placement[] = [preferred, 'below', 'above', 'right', 'left'];
  const placement = order.find((p) => fits(p, rect, vw, vh)) ?? 'below';
  const maxLeft = vw - POPOVER_WIDTH - MARGIN;
  const maxTop = vh - POPOVER_HEIGHT_GUESS - MARGIN;
  switch (placement) {
    case 'right':
      return { placement, left: rect.right + GAP, top: clamp(rect.top, MARGIN, maxTop) };
    case 'left':
      return { placement, left: rect.left - GAP - POPOVER_WIDTH, top: clamp(rect.top, MARGIN, maxTop) };
    case 'above':
      return { placement, left: clamp(rect.left, MARGIN, maxLeft), top: clamp(rect.top - GAP - POPOVER_HEIGHT_GUESS, MARGIN, maxTop) };
    default:
      return { placement, left: clamp(rect.left, MARGIN, maxLeft), top: clamp(rect.bottom + GAP, MARGIN, maxTop) };
  }
}
