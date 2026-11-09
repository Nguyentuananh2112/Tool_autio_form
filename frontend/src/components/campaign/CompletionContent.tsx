import { Check, TriangleAlert, X } from 'lucide-react';

import { cn } from '@/lib/cn';
import type { CompletionKind } from '@/lib/completion';
import { formatDuration } from '@/lib/format';
import type { CampaignSummary } from '@/types/campaign';

const ICON: Record<CompletionKind, { Icon: typeof Check; box: string }> = {
  success: { Icon: Check, box: 'bg-ok-soft text-ok' },
  partial: { Icon: TriangleAlert, box: 'bg-warn-soft text-warn' },
  failed: { Icon: X, box: 'bg-bad-soft text-bad' },
};

export function CompletionIcon({ kind }: { kind: CompletionKind }) {
  const { Icon, box } = ICON[kind];
  return (
    <span aria-hidden className={cn('inline-flex size-11 shrink-0 items-center justify-center rounded-full', box)}>
      <Icon className="size-6" strokeWidth={2.5} />
    </span>
  );
}

function Stat({ label, value, tone }: { label: string; value: string; tone?: 'ok' | 'bad' }) {
  return (
    <div className="flex flex-col gap-0.5 rounded-[10px] bg-sunken px-3 py-2.5">
      <span className="text-xs text-muted">{label}</span>
      <span className={cn('text-xl font-bold tabular-nums', tone === 'ok' && 'text-ok', tone === 'bad' && 'text-bad')}>{value}</span>
    </div>
  );
}

/** Số liệu + thanh xanh/đỏ + lỗi gom theo lý do kèm cách xử lý (màn 13). Dùng chung cho hộp thoại và trang chiến dịch. */
export function CompletionContent({ summary }: { summary: CampaignSummary }) {
  const { completed_count: ok, failed_count: bad, total_target: total } = summary;
  const width = (part: number) => `${total ? Math.min(100, (part / total) * 100) : 0}%`;
  return (
    <div className="flex flex-col gap-3.5">
      <div className="grid grid-cols-3 gap-2">
        <Stat label="Thành công" value={String(ok)} tone="ok" />
        <Stat label="Lỗi" value={String(bad)} tone={bad > 0 ? 'bad' : undefined} />
        <Stat label="Thời gian" value={formatDuration(summary.duration_seconds)} />
      </div>
      <div role="progressbar" aria-label={`${ok} thành công, ${bad} lỗi trên ${total}`} aria-valuemin={0} aria-valuemax={total} aria-valuenow={ok}
        className="flex h-2 overflow-hidden rounded-full bg-sunken">
        <span className="bg-ok" style={{ width: width(ok) }} />
        <span className="bg-bad" style={{ width: width(bad) }} />
      </div>
      {summary.remaining > 0 && <span className="text-[13px] text-muted">Còn {summary.remaining} phản hồi chưa gửi.</span>}
      {summary.reasons.map((reason) => (
        <div key={`${reason.category}-${reason.detail}`} className="flex flex-col gap-1.5 rounded-[10px] border border-line px-3.5 py-3">
          <div className="flex justify-between gap-2 text-sm">
            <b>{reason.title}</b>
            <span className="shrink-0 rounded-full bg-bad-soft px-2 py-0.5 text-xs font-semibold text-bad">{reason.count} lần</span>
          </div>
          {reason.detail && <span className="text-[13px] text-muted">Google báo: “{reason.detail}”</span>}
          <span className="text-[13px]"><b>Cách xử lý:</b> {reason.fix}</span>
        </div>
      ))}
    </div>
  );
}
