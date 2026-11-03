import { useCallback, useEffect, useState } from 'react';

import { type ApiError, toApiError } from '@/api/client';
import { settingsApi } from '@/api/endpoints';
import type { BrowserStatus } from '@/types/settings';

const POLL_MS = 1000;

/** Trạng thái & tải trình duyệt dự phòng; tự hỏi lại tiến độ mỗi giây khi đang tải. */
export function useBrowserInstall() {
  const [status, setStatus] = useState<BrowserStatus | null>(null);
  const [error, setError] = useState<ApiError | null>(null);

  const refresh = useCallback(async () => {
    try {
      setStatus(await settingsApi.browserStatus());
      setError(null);
    } catch (err) {
      setError(toApiError(err));
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  useEffect(() => {
    if (!status?.installing) return undefined;
    const timer = setInterval(() => void refresh(), POLL_MS);
    return () => clearInterval(timer);
  }, [status?.installing, refresh]);

  const install = async () => {
    try {
      setStatus(await settingsApi.installBrowser());
    } catch (err) {
      setError(toApiError(err));
    }
  };

  return { status, error, install };
}
