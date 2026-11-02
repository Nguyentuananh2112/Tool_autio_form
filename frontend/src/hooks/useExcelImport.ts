import { useState } from 'react';

import { type ApiError, toApiError } from '@/api/client';
import { excelApi } from '@/api/endpoints';
import type { ColumnMapping, ExcelConvertResponse, ExcelPreview } from '@/types/excel';

/** Đọc file → gợi ý ghép cột → người dùng sửa → chuyển đổi & kiểm tra từng dòng. */
export function useExcelImport(formId: string) {
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<ExcelPreview | null>(null);
  const [mappings, setMappings] = useState<ColumnMapping[]>([]);
  const [result, setResult] = useState<ExcelConvertResponse | null>(null);
  const [busy, setBusy] = useState<'read' | 'convert' | null>(null);
  const [error, setError] = useState<ApiError | null>(null);

  const convert = async (target: File, nextMappings: ColumnMapping[]) => {
    setBusy('convert');
    setError(null);
    try {
      setResult(await excelApi.convert(formId, target, nextMappings));
    } catch (err) {
      setError(toApiError(err));
    } finally {
      setBusy(null);
    }
  };

  const load = async (next: File) => {
    setFile(next);
    setResult(null);
    setBusy('read');
    setError(null);
    try {
      const data = await excelApi.preview(formId, next);
      setPreview(data);
      setMappings(data.mappings);
      await convert(next, data.mappings);
    } catch (err) {
      setError(toApiError(err));
      setBusy(null);
    }
  };

  const changeMapping = (index: number, entryId: string | null) => {
    const next = mappings.map((m, i) => (i === index ? { ...m, entry_id: entryId, kind: entryId ? ('MANUAL' as const) : ('NONE' as const), score: entryId ? 1 : 0 } : m));
    setMappings(next);
    if (file) void convert(file, next);
  };

  return { file, preview, mappings, result, busy, error, load, changeMapping };
}
