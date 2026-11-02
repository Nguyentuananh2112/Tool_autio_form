import { estimateBranchPaths } from '@/lib/branchPaths';
import { formatNumber } from '@/lib/format';
import { useFormConfig } from '@/store/formConfigStore';
import type { ParsedFormStructure } from '@/types/form';

/** "Đường đi dự kiến": bao nhiêu phản hồi đi vào mỗi nhánh với tỷ lệ hiện tại. */
export function BranchPathPreview({ formId, structure }: { formId: string; structure: ParsedFormStructure }) {
  const config = useFormConfig(formId);
  const paths = estimateBranchPaths(structure, config.rules);
  if (paths.length <= 1) return null;
  const target = config.dataSource === 'EXCEL' ? config.excel?.validRows ?? 0 : config.target;
  return (
    <div className="flex flex-col gap-2 rounded-[10px] bg-sunken px-3.5 py-3">
      <span className="text-[13px] font-semibold">Đường đi dự kiến của {formatNumber(target)} phản hồi</span>
      {paths.slice(0, 6).map((path) => (
        <div key={path.pages.join(',')} className="grid grid-cols-[minmax(0,1fr)_120px_56px] items-center gap-3 text-[13px]">
          <span className="text-muted">{path.label}</span>
          <span className="h-1.5 overflow-hidden rounded-full bg-line"><span className="block h-full bg-accent" style={{ width: `${path.probability * 100}%` }} /></span>
          <span className="tabular text-right font-semibold">{formatNumber(Math.round(path.probability * target))}</span>
        </div>
      ))}
    </div>
  );
}
