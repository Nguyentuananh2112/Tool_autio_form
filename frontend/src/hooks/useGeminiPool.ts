import { useState } from 'react';

import { type ApiError, toApiError } from '@/api/client';
import { aiApi } from '@/api/endpoints';

export const POOL_SIZE = 50;

/** Gọi Gemini sinh trước một pool câu trả lời tự luận (không gọi trong lúc gửi form — Mục 5.3 spec). */
export function useGeminiPool() {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);

  const generate = async (questionTitle: string, context: string, persona?: string): Promise<string[] | null> => {
    setBusy(true);
    setError(null);
    try {
      const result = await aiApi.generatePool({ question_title: questionTitle, survey_context: context, count: POOL_SIZE, persona });
      return result.answers;
    } catch (err) {
      setError(toApiError(err));
      return null;
    } finally {
      setBusy(false);
    }
  };

  return { busy, error, generate };
}
