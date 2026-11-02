import { Button } from '@/components/ui/Button';
import { cn } from '@/lib/cn';
import type { ConversionReport } from '@/types/excel';

export function ConversionSummary({ report, inUse, onUse, onCancelUse }: {
  report: ConversionReport;
  inUse: boolean;
  onUse: () => void;
  onCancelUse: () => void;
}) {
  const issues = report.issues.slice(0, 12);
  return (
    <aside aria-label="Kiểm tra dữ liệu" className="flex flex-col gap-4 self-start rounded-xl border border-line bg-surface p-5">
      <h2 className="m-0 text-[17px] font-semibold">Kiểm tra dữ liệu</h2>
      <div className="grid grid-cols-2 gap-2.5">
        <div className="flex flex-col gap-0.5 rounded-[10px] bg-ok-soft p-3 text-ok"><span className="tabular text-2xl font-bold">{report.valid_rows}</span><span className="text-xs">dòng hợp lệ</span></div>
        <div className="flex flex-col gap-0.5 rounded-[10px] bg-bad-soft p-3 text-bad"><span className="tabular text-2xl font-bold">{report.invalid_rows}</span><span className="text-xs">dòng lỗi, sẽ bỏ qua</span></div>
      </div>
      <ul className="m-0 flex max-h-72 list-none flex-col gap-2 overflow-y-auto p-0 text-[13px]">
        {issues.map((issue, i) => (
          <li key={`${issue.row_number}-${i}`} className={cn('flex gap-2', issue.severity === 'ERROR' ? 'text-bad' : 'text-warn')}>
            <span aria-hidden className="font-bold">{issue.severity === 'ERROR' ? '×' : '!'}</span>
            <span>Dòng {issue.row_number}: {issue.message}</span>
          </li>
        ))}
        {report.issues.length > issues.length && <li className="text-muted">… và {report.issues.length - issues.length} ghi chú khác</li>}
        <li className="flex gap-2 text-muted"><span aria-hidden className="font-bold">i</span><span>Câu ở trang không đi qua (theo rẽ nhánh) sẽ được bỏ, dù file có giá trị.</span></li>
      </ul>
      <div className="flex flex-col gap-2 border-t border-line pt-3.5">
        <span className="text-[13px] text-muted">Mỗi dòng hợp lệ là một phản hồi. Cách gửi và thời lượng chỉnh ở tab Tỷ lệ.</span>
        {inUse ? (
          <Button onClick={onCancelUse}>Thôi dùng file này (quay lại tỷ lệ %)</Button>
        ) : (
          <Button variant="primary" size="lg" disabled={report.valid_rows === 0} onClick={onUse}>Dùng {report.valid_rows} dòng này</Button>
        )}
      </div>
    </aside>
  );
}
