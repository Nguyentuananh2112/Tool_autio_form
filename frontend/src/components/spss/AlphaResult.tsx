import { Alert } from '@/components/ui/Alert';
import { Badge } from '@/components/ui/Badge';
import { formatDecimal } from '@/lib/format';
import type { SpssGroupPreview } from '@/types/campaign';

function alphaVerdict(alpha: number | null): { text: string; tone: 'ok' | 'warn' | 'bad' } {
  if (alpha === null) return { text: 'Không tính được', tone: 'bad' };
  if (alpha >= 0.9) return { text: 'Rất tốt · ≥ 0,9', tone: 'ok' };
  if (alpha >= 0.7) return { text: 'Đạt · ≥ 0,7', tone: 'ok' };
  return { text: 'Chưa đạt · < 0,7', tone: 'warn' };
}

export function AlphaResult({ preview }: { preview: SpssGroupPreview }) {
  const verdict = alphaVerdict(preview.cronbach_alpha);
  const stats = [
    { label: 'Trung bình đạt', value: formatDecimal(preview.achieved_mean), hint: `mục tiêu ${formatDecimal(preview.target_mean)}` },
    { label: 'Độ lệch chuẩn', value: formatDecimal(preview.achieved_std), hint: `mục tiêu ${formatDecimal(preview.target_std)}` },
    { label: 'r trung bình', value: formatDecimal(preview.mean_inter_item_r), hint: preview.target_r !== null ? `mục tiêu ${formatDecimal(preview.target_r)}` : 'theo alpha' },
  ];
  return (
    <div aria-live="polite" className="flex flex-col gap-3.5 rounded-xl bg-sunken p-4">
      <div className="flex flex-wrap items-baseline gap-3">
        <span className="text-[13px] font-medium text-muted">Cronbach’s Alpha dự kiến</span>
        <span className="tabular text-4xl font-bold tracking-tight">{formatDecimal(preview.cronbach_alpha)}</span>
        <Badge tone={verdict.tone}>{verdict.text}</Badge>
      </div>
      <div className="grid grid-cols-3 gap-2.5">
        {stats.map((s) => (
          <div key={s.label} className="flex flex-col gap-0.5 rounded-lg bg-surface px-3 py-2.5">
            <span className="text-xs text-muted">{s.label}</span>
            <span className="tabular text-lg font-bold">{s.value}</span>
            <span className="text-xs text-muted">{s.hint}</span>
          </div>
        ))}
      </div>
      <div className="flex flex-col gap-2">
        <span className="text-[13px] font-semibold">Phân phối từng biến</span>
        {preview.items.slice(0, 6).map((item) => {
          const counts = Object.values(item.distribution);
          const max = Math.max(1, ...counts);
          return (
            <div key={item.entry_id} className="grid grid-cols-[minmax(0,1fr)_120px_110px] items-end gap-2.5">
              <span className="truncate text-xs">{item.title}{item.is_reversed && ' (đảo chiều)'}</span>
              <div role="img" aria-label={`Phân phối ${item.title}: ${Object.entries(item.distribution).map(([k, v]) => `${k}: ${v}`).join(', ')}`} className="flex h-9 items-end gap-1">
                {counts.map((count, i) => <span key={i} className="flex-1 rounded-t-sm bg-accent" style={{ height: `${Math.max(4, (count / max) * 100)}%` }} />)}
              </div>
              <span className="tabular text-xs text-muted">M {formatDecimal(item.mean)} · SD {formatDecimal(item.std)}</span>
            </div>
          );
        })}
      </div>
      {preview.warnings.map((w) => <Alert key={w} tone="warn">{w}</Alert>)}
      <span className="text-xs text-muted">Ước tính từ {preview.n_samples} mẫu chạy thử trong máy; dữ liệu thật có thể lệch nhẹ.</span>
    </div>
  );
}
