import axios, { AxiosError } from 'axios';

import { getRuntimeConfig } from '@/config/runtime';
import type { ApiErrorBody } from '@/types/settings';

const config = getRuntimeConfig();

export const api = axios.create({
  baseURL: config.apiBase,
  timeout: 60_000,
  headers: config.token ? { 'X-App-Token': config.token } : {},
});

/** Lỗi đã chuẩn hóa: `message` để hiện cho người dùng, `errors` là danh sách chi tiết (nếu có). */
export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
    public readonly errors: string[] = [],
    /** Mã lỗi máy đọc được, VD "AI_KEYS_UNAVAILABLE" → mở hộp thoại dán key (màn 12) */
    public readonly code: string | null = null,
    /** Dữ liệu kèm theo lỗi (VD trạng thái từng API key) */
    public readonly details: Record<string, unknown> = {},
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

function isErrorBody(value: unknown): value is ApiErrorBody {
  return typeof value === 'object' && value !== null && 'message' in value;
}

export function toApiError(error: unknown): ApiError {
  if (error instanceof ApiError) return error;
  if (error instanceof AxiosError) {
    if (!error.response) {
      return new ApiError('Không kết nối được tới bộ xử lý của app. Hãy mở lại ứng dụng.', 0);
    }
    const detail = (error.response.data as { detail?: unknown } | undefined)?.detail;
    if (isErrorBody(detail)) {
      const { message, errors, code, ...details } = detail;
      return new ApiError(message, error.response.status, errors ?? [], code ?? null, details);
    }
    if (Array.isArray(detail)) {
      // Lỗi kiểm tra dữ liệu của FastAPI (422)
      const errors = detail.map((d: { msg?: string }) => d.msg ?? String(d));
      return new ApiError('Dữ liệu gửi đi chưa hợp lệ.', error.response.status, errors);
    }
    return new ApiError(`Lỗi ${error.response.status}.`, error.response.status);
  }
  return new ApiError(error instanceof Error ? error.message : 'Lỗi không xác định.', 0);
}

export async function request<T>(run: () => Promise<{ data: T }>): Promise<T> {
  try {
    return (await run()).data;
  } catch (error) {
    throw toApiError(error);
  }
}
