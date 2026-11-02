import { useState } from 'react';
import { useNavigate } from 'react-router-dom';

import { type ApiError, toApiError } from '@/api/client';
import { formsApi } from '@/api/endpoints';

/** Phân tích link form hoặc mở form mẫu, rồi chuyển sang màn hình Cấu hình. */
export function useFormParse() {
  const navigate = useNavigate();
  const [busy, setBusy] = useState<'parse' | 'demo' | null>(null);
  const [error, setError] = useState<ApiError | null>(null);

  const run = async (kind: 'parse' | 'demo', action: () => ReturnType<typeof formsApi.parse>) => {
    setBusy(kind);
    setError(null);
    try {
      const form = await action();
      navigate(`/forms/${form.id}`);
    } catch (err) {
      setError(toApiError(err));
    } finally {
      setBusy(null);
    }
  };

  return {
    busy,
    error,
    parse: (url: string) => run('parse', () => formsApi.parse(url)),
    openDemo: () => run('demo', formsApi.openDemo),
  };
}
