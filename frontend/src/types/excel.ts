// Khớp backend/app/schemas/excel_schema.py

export type ColumnMatchKind = 'CODE' | 'TITLE' | 'MANUAL' | 'NONE';

export interface ColumnMapping {
  column: string;
  entry_id: string | null;
  question_title: string | null;
  kind: ColumnMatchKind;
  score: number;
}

export interface RowIssue {
  row_number: number;
  entry_id: string | null;
  column: string | null;
  severity: 'ERROR' | 'WARNING';
  message: string;
}

export interface ExcelPreview {
  filename: string;
  sheet_names: string[];
  columns: string[];
  row_count: number;
  mappings: ColumnMapping[];
  preview_rows: Record<string, unknown>[];
}

export interface ConversionReport {
  total_rows: number;
  valid_rows: number;
  invalid_rows: number;
  issues: RowIssue[];
}

export interface ExcelConvertResponse {
  report: ConversionReport;
  records: Record<string, unknown>[];
}
