import { useState } from 'react';

import type { LiveLogLine } from '@/hooks/useCampaignLive';
import type { SocketStatus } from '@/hooks/useCampaignSocket';
import { cn } from '@/lib/cn';
import { formatTime } from '@/lib/format';

const ENGINE_LABEL: Record<string, string> = { HTTPX: 'HTTPX', PLAYWRIGHT: 'TRÌNH DUYỆT', SIMULATED: 'MÔ PHỎNG' };

/** "Nhật ký gửi trực tiếp" — khung chữ kiểu terminal (artboard 4). */
export function LiveLog({ lines, socket }: { lines: LiveLogLine[]; socket: SocketStatus }) {
  const [errorsOnly, setErrorsOnly] = useState(false);
  const shown = (errorsOnly ? lines.filter((l) => !l.ok) : lines).slice(0, 120);
  const errorCount = lines.filter((l) => !l.ok).length;
  const filterClass = (active: boolean) => cn('min-h-9 cursor-pointer rounded-[7px] border-0 px-3 text-[13px] text-code-ink', active ? 'bg-white/10 font-semibold' : 'bg-transparent');

  return (
    <section aria-labelledby="log-title" data-tour="log" className="flex flex-col rounded-xl bg-code text-code-ink">
      <div className="flex flex-wrap items-center justify-between gap-2.5 border-b border-white/10 px-4.5 py-3.5">
        <h2 id="log-title" className="m-0 flex items-center gap-2 text-[15px] font-semibold">
          Nhật ký gửi trực tiếp
          <span className={cn('size-2 rounded-full', socket === 'open' ? 'bg-ok' : 'bg-warn')} aria-label={socket === 'open' ? 'Đang kết nối' : 'Đang kết nối lại'} role="img" />
        </h2>
        <div className="flex gap-1.5">
          <button type="button" aria-pressed={!errorsOnly} onClick={() => setErrorsOnly(false)} className={filterClass(!errorsOnly)}>Tất cả</button>
          <button type="button" aria-pressed={errorsOnly} onClick={() => setErrorsOnly(true)} className={filterClass(errorsOnly)}>Chỉ lỗi ({errorCount})</button>
        </div>
      </div>
      <ol aria-live="polite" className="m-0 flex max-h-96 list-none flex-col gap-1.5 overflow-y-auto px-4.5 py-3 font-mono text-[13px] leading-normal">
        {shown.length === 0 && <li className="text-code-muted">Chưa có dòng nào.</li>}
        {shown.map((line) => (
          <li key={line.key} className="flex flex-wrap gap-3">
            <span className="text-code-muted">{formatTime(line.time)}</span>
            <span>#{line.sequence}</span>
            <span className={line.engine === 'PLAYWRIGHT' ? 'text-[#f8b864]' : 'text-[#8db1ff]'}>{ENGINE_LABEL[line.engine] ?? line.engine}</span>
            <span className={line.ok ? 'text-[#6ee7a0]' : 'text-[#ff8a8a]'}>{line.ok ? '200 OK' : `${line.statusCode || ''} lỗi`.trim()}</span>
            <span className="text-code-muted">{line.note}</span>
          </li>
        ))}
      </ol>
    </section>
  );
}
