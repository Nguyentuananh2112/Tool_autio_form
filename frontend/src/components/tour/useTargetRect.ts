import { useEffect, useState } from 'react';

const FIND_TIMEOUT_MS = 4000;
const POLL_MS = 100;

/** Tìm phần tử `[data-tour=target]` (chờ tới khi màn hình vẽ xong), cuộn tới và theo dõi vị trí. */
export function useTargetRect(target: string): { rect: DOMRect | null; missing: boolean } {
  const [rect, setRect] = useState<DOMRect | null>(null);
  const [missing, setMissing] = useState(false);

  useEffect(() => {
    let element: Element | null = null;
    let frame = 0;
    const started = Date.now();
    const measure = () => {
      if (element) setRect(element.getBoundingClientRect());
    };
    const onChange = () => {
      cancelAnimationFrame(frame);
      frame = requestAnimationFrame(measure);
    };
    const observer = new ResizeObserver(onChange);

    const find = setInterval(() => {
      element = document.querySelector(`[data-tour="${target}"]`);
      if (element) {
        clearInterval(find);
        element.scrollIntoView({ block: 'center', inline: 'nearest' });
        observer.observe(element);
        // chờ cuộn xong rồi đo
        setTimeout(measure, 350);
      } else if (Date.now() - started > FIND_TIMEOUT_MS) {
        clearInterval(find);
        setMissing(true);
      }
    }, POLL_MS);

    window.addEventListener('resize', onChange);
    window.addEventListener('scroll', onChange, true);
    return () => {
      clearInterval(find);
      cancelAnimationFrame(frame);
      observer.disconnect();
      window.removeEventListener('resize', onChange);
      window.removeEventListener('scroll', onChange, true);
    };
  }, [target]);

  return { rect, missing };
}
