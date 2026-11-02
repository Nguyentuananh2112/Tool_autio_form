import { KpiGrid, type Kpi } from '@/components/dashboard/KpiGrid';
import { Alert } from '@/components/ui/Alert';
import type { LiveLogLine } from '@/hooks/useCampaignLive';
import { formatDecimal, formatDuration, formatPercent } from '@/lib/format';
import type { CampaignRead } from '@/types/campaign';

function averageGapSeconds(campaign: CampaignRead, lines: LiveLogLine[]): number | null {
  if (campaign.schedule.mode === 'SCHEDULED' && campaign.schedule.duration_minutes) {
    return (campaign.schedule.duration_minutes * 60) / Math.max(1, campaign.total_target);
  }
  const times = lines.filter((l) => l.ok).slice(0, 20).map((l) => new Date(l.time).getTime()).filter((t) => !Number.isNaN(t));
  if (times.length < 2) return null;
  return (Math.max(...times) - Math.min(...times)) / 1000 / (times.length - 1);
}

/** 4 thẻ KPI + thanh tiến độ (artboard 4). */
export function LiveProgress({ campaign, lines, nextDelay }: { campaign: CampaignRead; lines: LiveLogLine[]; nextDelay: number | null }) {
  const done = campaign.completed_count + campaign.failed_count;
  const remaining = Math.max(0, campaign.total_target - done);
  const gap = averageGapSeconds(campaign, lines);
  const browserCount = lines.filter((l) => l.engine === 'PLAYWRIGHT').length;
  const pct = (part: number) => (campaign.total_target ? (part / campaign.total_target) * 100 : 0);

  const kpis: Kpi[] = [
    { label: 'Tiến độ', value: formatPercent(pct(done)), hint: `${done} / ${campaign.total_target} phản hồi` },
    { label: 'Tỷ lệ thành công', value: done ? formatPercent((campaign.completed_count * 100) / done) : '—', hint: `${campaign.completed_count} thành công · ${campaign.failed_count} lỗi` },
    { label: 'Thời gian còn lại', value: gap && remaining ? `~${formatDuration(gap * remaining)}` : '—', hint: gap ? `trung bình ${formatDecimal(gap)} giây / phản hồi` : 'đang tính' },
    { label: 'Dùng trình duyệt dự phòng', value: `${browserCount} lần`, hint: 'khi form từ chối dữ liệu gửi trực tiếp' },
  ];

  return (
    <div data-tour="kpi" className="flex flex-col gap-4">
      <KpiGrid items={kpis} />
      <section aria-label="Tiến độ" className="flex flex-col gap-2.5 rounded-xl border border-line bg-surface px-5 py-4">
        <div className="flex flex-wrap justify-between gap-2 text-sm">
          <strong>{done} / {campaign.total_target} phản hồi</strong>
          {campaign.status === 'RUNNING' && nextDelay !== null && <span className="text-muted">Phản hồi tiếp theo sau {formatDecimal(nextDelay)} giây</span>}
        </div>
        <div role="progressbar" aria-valuemin={0} aria-valuemax={campaign.total_target} aria-valuenow={done} aria-label="Tiến độ chiến dịch" className="flex h-3 gap-0.5 overflow-hidden rounded-full bg-sunken">
          <span className="bg-ok transition-[width]" style={{ width: `${pct(campaign.completed_count)}%` }} />
          <span className="bg-bad transition-[width]" style={{ width: `${pct(campaign.failed_count)}%` }} />
        </div>
        <div className="flex flex-wrap gap-4 text-[13px] text-muted">
          <span className="inline-flex items-center gap-1.5"><span aria-hidden className="size-2.5 rounded-sm bg-ok" />Thành công {campaign.completed_count}</span>
          <span className="inline-flex items-center gap-1.5"><span aria-hidden className="size-2.5 rounded-sm bg-bad" />Lỗi {campaign.failed_count}</span>
          <span className="inline-flex items-center gap-1.5"><span aria-hidden className="size-2.5 rounded-sm border border-line bg-sunken" />Còn lại {remaining}</span>
          <span>Có thể thu nhỏ ứng dụng, chiến dịch vẫn chạy. Không tắt máy hoặc cho máy ngủ.</span>
        </div>
      </section>
      {campaign.status === 'PAUSED' && campaign.pause_reason && <Alert tone="warn" title="Chiến dịch đang tạm dừng">{campaign.pause_reason}</Alert>}
      {campaign.status === 'FAILED' && <Alert tone="bad" title="Chiến dịch dừng vì lỗi">{campaign.pause_reason ?? 'Xem nhật ký bên dưới để biết chi tiết.'}</Alert>}
    </div>
  );
}
