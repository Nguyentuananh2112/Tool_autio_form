import { cn } from '@/lib/cn';
import type { Readiness } from '@/lib/readiness';
import type { FormConfig } from '@/store/formConfigStore';

export function ReadinessChecklist({ readiness, config }: { readiness: Readiness; config: FormConfig }) {
  const items: { ok: boolean; text: string }[] = [
    { ok: readiness.issues.length === 0, text: `${readiness.configuredCount} / ${readiness.totalCount} câu đã cấu hình` },
  ];
  if (readiness.missingTextCount > 0) items.push({ ok: false, text: `${readiness.missingTextCount} câu tự luận thiếu câu trả lời mẫu` });
  if (config.groups.length > 0) items.push({ ok: true, text: `${config.groups.length} nhóm tương quan SPSS` });
  if (config.dataSource === 'EXCEL') items.push({ ok: Boolean(config.excel?.validRows), text: `Dùng ${config.excel?.validRows ?? 0} dòng từ ${config.excel?.fileName ?? 'file Excel'}` });

  return (
    <div className="flex flex-col gap-2 rounded-[10px] bg-sunken p-3.5">
      <span className="text-[13px] font-semibold">Kiểm tra trước khi chạy</span>
      <ul className="m-0 flex list-none flex-col gap-1.5 p-0">
        {items.map((item) => (
          <li key={item.text} className={cn('flex gap-2 text-[13px]', item.ok ? 'text-ok' : 'text-warn')}>
            <span aria-hidden className="font-bold">{item.ok ? '✓' : '!'}</span>
            <span>{item.text}</span>
          </li>
        ))}
        {readiness.issues.slice(0, 3).map((issue) => (
          <li key={issue.entryId} className="pl-5 text-xs text-muted">
            <a href={`#q-${issue.entryId}`} className="text-muted">{issue.message}</a>
          </li>
        ))}
      </ul>
    </div>
  );
}
