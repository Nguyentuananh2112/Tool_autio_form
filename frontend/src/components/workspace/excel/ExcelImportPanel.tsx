import { ErrorAlert } from '@/components/ui/Alert';
import { Card, CardHeader } from '@/components/ui/Card';
import { useExcelImport } from '@/hooks/useExcelImport';
import { useFormConfig, useFormConfigStore } from '@/store/formConfigStore';
import type { ParsedFormStructure } from '@/types/form';

import { ConversionSummary } from './ConversionSummary';
import { ExcelDropzone } from './ExcelDropzone';
import { ExcelPreviewTable } from './ExcelPreviewTable';
import { MappingTable } from './MappingTable';

/** Tab "Nhập từ Excel / CSV" (artboard 8). */
export function ExcelImportPanel({ formId, structure }: { formId: string; structure: ParsedFormStructure }) {
  const config = useFormConfig(formId);
  const patch = useFormConfigStore((s) => s.patchConfig);
  const excel = useExcelImport(formId);
  const mapped = excel.mappings.filter((m) => m.entry_id).length;

  return (
    <div className="flex flex-col gap-4">
      {config.dataSource === 'EXCEL' && config.excel && !excel.preview && (
        <p className="m-0 rounded-xl bg-accent-soft px-4 py-3 text-sm text-accent">
          Đang dùng {config.excel.validRows} dòng từ <strong>{config.excel.fileName}</strong>. Chọn file khác để thay.
        </p>
      )}
      <ExcelDropzone fileName={excel.file?.name ?? null} rowCount={excel.preview?.row_count ?? null} columnCount={excel.preview?.columns.length ?? null} onFile={(f) => void excel.load(f)} busy={excel.busy !== null} />
      <ErrorAlert error={excel.error} />
      {excel.preview && (
        <div className="flex flex-wrap items-start gap-5">
          <div className="flex min-w-0 basis-[520px] flex-[3] flex-col gap-4">
            <Card>
              <CardHeader title="Ghép cột Excel với câu hỏi" description={`${mapped} / ${excel.mappings.length} cột đã ghép · cột còn lại sẽ bỏ qua`} />
              <MappingTable mappings={excel.mappings} questions={structure.questions} onChange={excel.changeMapping} />
            </Card>
            <Card>
              <CardHeader title="Xem trước 5 dòng đầu" description="Số 1–5 ở câu thang đo được hiểu là thứ tự đáp án (dữ liệu đã mã hóa cho SPSS)." />
              <ExcelPreviewTable columns={excel.preview.columns} rows={excel.preview.preview_rows} />
            </Card>
          </div>
          <div className="min-w-[260px] max-w-[360px] flex-1">
            {excel.result && (
              <ConversionSummary
                report={excel.result.report}
                inUse={config.dataSource === 'EXCEL' && config.excel?.fileName === excel.file?.name}
                onUse={() => patch(formId, {
                  dataSource: 'EXCEL',
                  excel: { fileName: excel.file?.name ?? 'file', records: excel.result?.records ?? [], validRows: excel.result?.report.valid_rows ?? 0 },
                })}
                onCancelUse={() => patch(formId, { dataSource: 'PROBABILITY', excel: null })}
              />
            )}
          </div>
        </div>
      )}
    </div>
  );
}
