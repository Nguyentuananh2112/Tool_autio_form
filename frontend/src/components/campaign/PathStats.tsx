import type { LiveLogLine } from '@/hooks/useCampaignLive';
import type { ParsedFormStructure } from '@/types/form';

/** Đường đi rẽ nhánh thực tế (đếm theo pageHistory của các lần gửi thành công). */
export function PathStats({ lines, structure }: { lines: LiveLogLine[]; structure: ParsedFormStructure | null }) {
  const counts = new Map<string, number>();
  for (const line of lines) if (line.ok && line.pageHistory) counts.set(line.pageHistory, (counts.get(line.pageHistory) ?? 0) + 1);
  const rows = [...counts.entries()].sort((a, b) => b[1] - a[1]).slice(0, 5);
  const label = (history: string) =>
    history.split(',').map((page) => structure?.sections.find((s) => s.page_index === Number(page))?.title.slice(0, 18) ?? `Trang ${Number(page) + 1}`).join(' → ');

  if (rows.length === 0) return <p className="m-0 text-sm text-muted">Chưa có phản hồi thành công.</p>;
  return (
    <ul className="m-0 flex list-none flex-col gap-2 p-0">
      {rows.map(([history, count]) => (
        <li key={history} className="grid grid-cols-[minmax(0,1fr)_48px] gap-2 text-[13px]">
          <span className="text-muted">{label(history)}</span>
          <span className="tabular text-right font-semibold">{count}</span>
        </li>
      ))}
    </ul>
  );
}
