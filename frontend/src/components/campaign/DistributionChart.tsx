import { useId, useState } from 'react';
import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';

import { Button } from '@/components/ui/Button';
import { Select } from '@/components/ui/Field';
import { useChartColors } from '@/hooks/useChartColors';
import { formatPercent } from '@/lib/format';
import type { QuestionDistribution } from '@/types/campaign';

/** Phân phối đáp án đã gửi so với tỷ lệ mục tiêu (2 chuỗi, có chú thích + bảng thay thế). */
export function DistributionChart({ items }: { items: QuestionDistribution[] }) {
  const colors = useChartColors();
  const selectId = useId();
  const [entryId, setEntryId] = useState<string | null>(null);
  const [asTable, setAsTable] = useState(false);
  const current = items.find((d) => d.entry_id === entryId) ?? items[0];

  if (!current) {
    return <p className="m-0 text-sm text-muted">Chưa có phản hồi nào được gửi.</p>;
  }
  const data = current.options.map((o) => ({ label: o.label, sent: o.sent_pct, target: o.target_pct ?? 0, count: o.sent_count }));
  const hasTarget = current.options.some((o) => o.target_pct !== null);

  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap items-center gap-2">
        <label htmlFor={selectId} className="sr-only">Chọn câu hỏi</label>
        <Select id={selectId} value={current.entry_id} onChange={(e) => setEntryId(e.target.value)} className="max-w-md min-h-10 text-[13px]">
          {items.map((d) => <option key={d.entry_id} value={d.entry_id}>{d.title.slice(0, 80)}</option>)}
        </Select>
        <Button size="sm" variant="quiet" onClick={() => setAsTable((v) => !v)}>{asTable ? 'Xem biểu đồ' : 'Xem dạng bảng'}</Button>
        <span className="text-xs text-muted">{current.answered} phản hồi đã trả lời câu này</span>
      </div>
      {asTable ? (
        <table className="w-full border-collapse text-sm">
          <thead><tr className="text-left text-xs text-muted"><th className="py-2 font-semibold">Đáp án</th><th className="py-2 text-right font-semibold">Đã gửi</th><th className="py-2 text-right font-semibold">Mục tiêu</th></tr></thead>
          <tbody>
            {data.map((d) => (
              <tr key={d.label} className="border-t border-line">
                <td className="py-2">{d.label}</td>
                <td className="tabular py-2 text-right">{formatPercent(d.sent)} ({d.count})</td>
                <td className="tabular py-2 text-right">{hasTarget ? formatPercent(d.target) : '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : (
        <div className="h-64" role="img" aria-label={`Phân phối ${current.title}: ${data.map((d) => `${d.label} đã gửi ${d.sent}%${hasTarget ? `, mục tiêu ${d.target}%` : ''}`).join('; ')}`}>
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={data} barGap={2} margin={{ top: 8, right: 8, bottom: 0, left: -12 }}>
              <CartesianGrid vertical={false} stroke={colors.grid} />
              <XAxis dataKey="label" tick={{ fill: colors.muted, fontSize: 12 }} axisLine={{ stroke: colors.grid }} tickLine={false} interval={0} />
              <YAxis unit="%" tick={{ fill: colors.muted, fontSize: 12 }} axisLine={false} tickLine={false} width={48} />
              <Tooltip
                cursor={{ fill: colors.grid, opacity: 0.4 }}
                contentStyle={{ background: colors.surface, border: `1px solid ${colors.grid}`, borderRadius: 8, color: colors.ink, fontSize: 13 }}
                formatter={(value: number, name: string) => [formatPercent(value), name]}
              />
              <Legend wrapperStyle={{ fontSize: 13, color: colors.muted }} />
              <Bar dataKey="sent" name="Đã gửi" fill={colors.series1} radius={[4, 4, 0, 0]} maxBarSize={36} />
              {hasTarget && <Bar dataKey="target" name="Mục tiêu đã đặt" fill={colors.series2} radius={[4, 4, 0, 0]} maxBarSize={36} />}
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}
