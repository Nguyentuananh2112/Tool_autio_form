import { useState } from 'react';
import { useNavigate } from 'react-router-dom';

import { type ApiError, toApiError } from '@/api/client';
import { campaignsApi } from '@/api/endpoints';
import type { CompletionAction } from '@/lib/completion';
import type { CampaignSummary } from '@/types/campaign';

/** Các nút của thông báo kết thúc (màn 13). `onDone` chạy sau khi thao tác xong (VD đóng hộp thoại). */
export function useCompletionActions(summary: CampaignSummary, onDone: () => void) {
  const navigate = useNavigate();
  const [busy, setBusy] = useState<CompletionAction | null>(null);
  const [error, setError] = useState<ApiError | null>(null);
  const id = summary.campaign_id;

  const guarded = async (action: CompletionAction, work: () => Promise<void>) => {
    setBusy(action);
    setError(null);
    try {
      await work();
      onDone();
    } catch (err) {
      setError(toApiError(err));
    } finally {
      setBusy(null);
    }
  };

  const run = (action: CompletionAction) => {
    switch (action) {
      case 'view':
        return guarded(action, async () => navigate(`/campaigns/${id}`));
      case 'log':
        return guarded(action, async () => navigate(`/campaigns/${id}#nhat-ky`));
      case 'again':
        return guarded(action, async () => navigate(`/forms/${summary.form_id}?tab=weights`));
      case 'config':
        return guarded(action, async () => navigate(`/forms/${summary.form_id}?tab=weights`));
      case 'retry':
        return guarded(action, async () => {
          await campaignsApi.retryFailed(id);
          navigate(`/campaigns/${id}`);
        });
      case 'resume':
        return guarded(action, async () => {
          await campaignsApi.resume(id);
          navigate(`/campaigns/${id}`);
        });
      case 'export':
        return guarded(action, async () => {
          const blob = await campaignsApi.exportFile(id, 'xlsx');
          const url = URL.createObjectURL(blob);
          const link = document.createElement('a');
          link.href = url;
          link.download = `chien-dich-${id.slice(0, 8)}.xlsx`;
          link.click();
          URL.revokeObjectURL(url);
        });
      default:
        return undefined;
    }
  };

  return { busy, error, run };
}
