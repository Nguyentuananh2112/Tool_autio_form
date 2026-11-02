import type { RuntimeConfig } from '@/types/settings';

/**
 * Địa chỉ backend và mã ứng dụng (X-App-Token).
 * - App desktop: vỏ desktop gắn `window.__AUTOFORM_CONFIG__` trước khi nạp giao diện.
 * - Phát triển (npm run dev): dùng proxy của Vite, backend không cần token.
 */
export function getRuntimeConfig(): RuntimeConfig {
  const injected = window.__AUTOFORM_CONFIG__ ?? {};
  const wsDefault = `${window.location.protocol === 'https:' ? 'wss' : 'ws'}://${window.location.host}`;
  return {
    apiBase: injected.apiBase ?? import.meta.env.VITE_API_BASE ?? '/api/v1',
    wsBase: injected.wsBase ?? import.meta.env.VITE_WS_BASE ?? wsDefault,
    token: injected.token ?? import.meta.env.VITE_APP_TOKEN ?? null,
  };
}
