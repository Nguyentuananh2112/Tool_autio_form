const numberFormat = new Intl.NumberFormat('vi-VN');
const decimalFormat = new Intl.NumberFormat('vi-VN', { minimumFractionDigits: 1, maximumFractionDigits: 1 });
const twoDecimals = new Intl.NumberFormat('vi-VN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });

export const formatNumber = (value: number): string => numberFormat.format(value);
export const formatPercent = (value: number): string => `${decimalFormat.format(value)}%`;
export const formatDecimal = (value: number | null | undefined): string =>
  value === null || value === undefined ? '—' : twoDecimals.format(value);

export function formatDuration(totalSeconds: number): string {
  if (!Number.isFinite(totalSeconds) || totalSeconds <= 0) return '—';
  const minutes = Math.round(totalSeconds / 60);
  if (minutes < 1) return `${Math.round(totalSeconds)} giây`;
  if (minutes < 60) return `${minutes} phút`;
  const hours = Math.floor(minutes / 60);
  const rest = minutes % 60;
  return rest ? `${hours} giờ ${rest} phút` : `${hours} giờ`;
}

export function formatDateTime(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  return date.toLocaleString('vi-VN', { hour: '2-digit', minute: '2-digit', day: '2-digit', month: '2-digit' });
}

export function formatTime(iso: string): string {
  const date = new Date(iso);
  return Number.isNaN(date.getTime()) ? iso : date.toLocaleTimeString('vi-VN', { hour12: false });
}
