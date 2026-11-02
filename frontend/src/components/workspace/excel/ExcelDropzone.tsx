import { FileSpreadsheet } from 'lucide-react';
import { type DragEvent, useId, useState } from 'react';

import { cn } from '@/lib/cn';

export function ExcelDropzone({ fileName, rowCount, columnCount, onFile, busy }: {
  fileName: string | null;
  rowCount: number | null;
  columnCount: number | null;
  onFile: (file: File) => void;
  busy: boolean;
}) {
  const inputId = useId();
  const [dragging, setDragging] = useState(false);
  const drop = (event: DragEvent) => {
    event.preventDefault();
    setDragging(false);
    const file = event.dataTransfer.files[0];
    if (file) onFile(file);
  };
  return (
    <section
      aria-label="File dữ liệu"
      onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
      onDragLeave={() => setDragging(false)}
      onDrop={drop}
      className={cn('flex flex-wrap items-center gap-4 rounded-xl border-2 border-dashed bg-surface px-5 py-4', dragging ? 'border-accent bg-accent-soft' : 'border-accent-line')}
    >
      <span aria-hidden className="flex size-12 items-center justify-center rounded-xl bg-ok-soft text-ok"><FileSpreadsheet className="size-6" /></span>
      <div className="flex min-w-[260px] flex-1 flex-col gap-0.5">
        <strong className="text-[15px]">{fileName ?? 'Kéo thả file .xlsx hoặc .csv vào đây'}</strong>
        <span className="text-[13px] text-muted">
          {fileName && rowCount !== null ? `${rowCount} dòng · ${columnCount} cột · kéo thả file khác để thay` : 'Mỗi dòng là một người trả lời, dòng đầu là tên cột. Tối đa 20 MB.'}
        </span>
      </div>
      <label htmlFor={inputId} className="inline-flex min-h-11 cursor-pointer items-center rounded-[10px] border border-line bg-surface px-4 text-sm font-semibold hover:bg-sunken">
        {busy ? 'Đang đọc…' : fileName ? 'Chọn file khác' : 'Chọn file'}
      </label>
      <input id={inputId} type="file" accept=".xlsx,.xlsm,.csv" className="sr-only" onChange={(e) => { const f = e.target.files?.[0]; if (f) onFile(f); e.target.value = ''; }} />
    </section>
  );
}
