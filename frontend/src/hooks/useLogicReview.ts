import { useCallback, useEffect, useRef, useState } from 'react';

import { type ApiError, toApiError } from '@/api/client';
import { logicApi } from '@/api/endpoints';
import type { FormConfig } from '@/store/formConfigStore';
import type { KeyAttempt, LogicMap, LogicReviewResult } from '@/types/logic';

export type LogicPhase = 'loading' | 'analyzing' | 'reviewing' | 'idle';

export interface QuotaPrompt {
  keys: KeyAttempt[];
  message: string;
  retry: () => void;
}

/**
 * Màn Soát logic: tải bản đồ → (chưa có thì) AI đọc câu hỏi → soát mẫu thử → người dùng sửa → xác nhận.
 * Hết lượt AI: mở hộp thoại dán key (màn 12) và chạy lại đúng bước đang dở.
 */
export function useLogicReview(formId: string, config: FormConfig) {
  const [draft, setDraft] = useState<LogicMap | null>(null);
  const [result, setResult] = useState<LogicReviewResult | null>(null);
  const [reviewedJson, setReviewedJson] = useState<string | null>(null);
  const [phase, setPhase] = useState<LogicPhase>('loading');
  const [error, setError] = useState<ApiError | null>(null);
  const [quota, setQuota] = useState<QuotaPrompt | null>(null);
  const configRef = useRef(config);
  configRef.current = config;

  const fail = useCallback((err: unknown, retry: () => void) => {
    const apiError = toApiError(err);
    if (apiError.code === 'AI_KEYS_UNAVAILABLE') {
      setQuota({ keys: (apiError.details.keys as KeyAttempt[] | undefined) ?? [], message: apiError.message, retry });
    } else {
      setError(apiError);
    }
    setPhase('idle');
  }, []);

  const review = useCallback(async (logic: LogicMap) => {
    setPhase('reviewing');
    setError(null);
    try {
      const current = configRef.current;
      const next = await logicApi.review(formId, { rules: Object.values(current.rules), spss_groups: current.groups, logic });
      setResult(next);
      setDraft(next.logic);
      setReviewedJson(JSON.stringify({ ...next.logic, confirmed: false }));
      setPhase('idle');
    } catch (err) {
      fail(err, () => void review(logic));
    }
  }, [formId, fail]);

  const analyze = useCallback(async () => {
    setPhase('analyzing');
    setError(null);
    setResult(null);
    try {
      const logic = await logicApi.analyze(formId);
      setDraft(logic);
      await review(logic);
    } catch (err) {
      fail(err, () => void analyze());
    }
  }, [formId, review, fail]);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const stored = await logicApi.get(formId);
        if (cancelled) return;
        if (stored) {
          setDraft(stored);
          await review(stored);
        } else {
          await analyze();
        }
      } catch (err) {
        if (!cancelled) fail(err, () => void analyze());
      }
    })();
    return () => {
      cancelled = true;
    };
    // Chỉ tự chạy khi mở màn hình; soát lại do người dùng bấm
  }, [formId]);

  /** Lưu bản đồ đã soát kèm cờ xác nhận — bắt buộc trước khi tạo chiến dịch. */
  const confirm = useCallback(async () => {
    if (!draft) return false;
    try {
      setDraft(await logicApi.save(formId, { ...draft, confirmed: true }));
      return true;
    } catch (err) {
      setError(toApiError(err));
      return false;
    }
  }, [draft, formId]);

  // Chưa soát lần nào (đang soát lần đầu) thì không coi là "đã sửa"
  const dirty = draft !== null && reviewedJson !== null && JSON.stringify({ ...draft, confirmed: false }) !== reviewedJson;

  return {
    draft,
    setDraft,
    result,
    phase,
    error,
    quota,
    dirty,
    ready: Boolean(result?.ready) && !dirty && phase === 'idle',
    analyze,
    review: () => draft && void review(draft),
    confirm,
    closeQuota: () => setQuota(null),
  };
}
