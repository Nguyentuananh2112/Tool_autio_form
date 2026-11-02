import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';

import { useChartColors } from '@/hooks/useChartColors';
import type { LiveLogLine } from '@/hooks/useCampaignLive';

const BUCKET_MINUTES = 5;
const MAX_BUCKETS = 12;

/** Gom các lần gửi thành công theo khung 5 phút. */
function buckets(lines: LiveLogLine[]): { label: string; count: number }[] {
  const counts = new Map<number, number>();
  for (const line of lines) {
    if (!line.ok) continue;
    const time = new Date(line.time).getTime();
    if (Number.isNaN(time)) continue;
    const key = Math.floor(time / (BUCKET_MINUTES * 60_000));
    counts.set(key, (counts.get(key) ?? 0) + 1);
  }
  const keys = [...counts.keys()].sort((a, b) => a - b).slice(-MAX_BUCKETS);
  return keys.map((key) => ({
    label: new Date(key * BUCKET_MINUTES * 60_000).toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit', hour12: false }),
    count: counts.get(key) ?? 0,
  }));
}

export function PaceChart({ lines }: { lines: LiveLogLine[] }) {
  const colors = useChartColors();
  const data = buckets(lines);
  if (data.length < 2) return <p className="m-0 text-sm text-muted">Biểu đồ nhịp gửi sẽ hiện khi đã có phản hồi trong ít nhất 2 khung 5 phút.</p>;
  return (
    <div className="h-44" role="img" aria-label={`Nhịp gửi: ${data.map((d) => `${d.label} ${d.count} phản hồi`).join(', ')}`}>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: -20 }}>
          <CartesianGrid vertical={false} stroke={colors.grid} />
          <XAxis dataKey="label" tick={{ fill: colors.muted, fontSize: 12 }} axisLine={{ stroke: colors.grid }} tickLine={false} />
          <YAxis allowDecimals={false} tick={{ fill: colors.muted, fontSize: 12 }} axisLine={false} tickLine={false} />
          <Tooltip
            cursor={{ stroke: colors.muted, strokeDasharray: '3 3' }}
            contentStyle={{ background: colors.surface, border: `1px solid ${colors.grid}`, borderRadius: 8, color: colors.ink, fontSize: 13 }}
            formatter={(value: number) => [`${value} phản hồi`, `Trong ${BUCKET_MINUTES} phút`]}
          />
          <Line type="monotone" dataKey="count" stroke={colors.series1} strokeWidth={2} dot={{ r: 4, strokeWidth: 2, stroke: colors.surface, fill: colors.series1 }} activeDot={{ r: 5 }} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
