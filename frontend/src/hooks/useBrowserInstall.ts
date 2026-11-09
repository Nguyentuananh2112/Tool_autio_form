import { useCallback, useEffect, useRef, useState } from 'react';

import { type ApiError, toApiError } from '@/api/client';
import { settingsApi } from '@/api/endpoints';
import type { BrowserStatus } from '@/types/settings';

const POLL_MS = 1000;

/** Lần mở app đầu tiên (hoặc lần trước tải dở / mất mạng): chưa có trình duyệt thì tự tải, mỗi phiên chỉ tự thử 1 lần. */
export function shouldAutoInstall(status: BrowserStatus | null, alreadyTried: boolean): boolean {
  return !alreadyTried && status !== null && !status.installed && !status.installing && !status.error;
}

/**
 * Trạng thái & tải trình duyệt dự phòng; tự hỏi lại tiến độ mỗi giây khi đang tải.
 * `autoInstall`: tự tải khi chưa có (dùng ở khung app để người dùng không phải làm gì).
 */
export function useBrowserInstall({ autoInstall = false }: { autoInstall?: boolean } = {}) {
  const [status, setStatus] = useState<BrowserStatus | null>(null);
  const [error, setError] = useState<ApiError | null>(null);
  const autoTried = useRef(false);

  const refresh = useCallback(async () => {
    try {
      setStatus(await settingsApi.browserStatus());
      setError(null);
    } catch (err) {
      setError(toApiError(err));
    }
  }, []);

  const install = useCallback(async () => {
    try {
      setStatus(await settingsApi.installBrowser());
      setError(null);
    } catch (err) {
      setError(toApiError(err));
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  useEffect(() => {
    if (!autoInstall || !shouldAutoInstall(status, autoTried.current)) return;
    autoTried.current = true;
    void install();
  }, [autoInstall, status, install]);

  useEffect(() => {
    if (!status?.installing) return undefined;
    const timer = setInterval(() => void refresh(), POLL_MS);
    return () => clearInterval(timer);
  }, [status?.installing, refresh]);

  return { status, error, install };
}
