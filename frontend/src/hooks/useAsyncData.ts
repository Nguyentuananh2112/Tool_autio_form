import { useCallback, useEffect, useRef, useState } from 'react';

import { type ApiError, toApiError } from '@/api/client';

export interface AsyncData<T> {
  data: T | null;
  error: ApiError | null;
  loading: boolean;
  reload: () => Promise<void>;
  setData: (value: T | null | ((prev: T | null) => T | null)) => void;
}

/** Tải dữ liệu một lần khi `deps` đổi; trả về hàm reload để tải lại thủ công. */
export function useAsyncData<T>(load: () => Promise<T>, deps: readonly unknown[]): AsyncData<T> {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<ApiError | null>(null);
  const [loading, setLoading] = useState(true);
  const loadRef = useRef(load);
  loadRef.current = load;
  const requestId = useRef(0);

  const reload = useCallback(async () => {
    const id = ++requestId.current;
    setLoading(true);
    try {
      const value = await loadRef.current();
      if (id === requestId.current) {
        setData(value);
        setError(null);
      }
    } catch (err) {
      if (id === requestId.current) setError(toApiError(err));
    } finally {
      if (id === requestId.current) setLoading(false);
    }
  }, []);

  useEffect(() => {
    void reload();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  return { data, error, loading, reload, setData };
}
