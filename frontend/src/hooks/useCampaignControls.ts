import { useState } from 'react';

import { type ApiError, toApiError } from '@/api/client';
import { campaignsApi } from '@/api/endpoints';
import type { CampaignRead } from '@/types/campaign';

type Action = 'pause' | 'resume' | 'stop' | 'export';

/** Tạm dừng / Tiếp tục / Dừng hẳn / Xuất dữ liệu. */
export function useCampaignControls(campaignId: string, onChanged: (campaign: CampaignRead) => void) {
  const [busy, setBusy] = useState<Action | null>(null);
  const [error, setError] = useState<ApiError | null>(null);

  const run = async (action: Exclude<Action, 'export'>) => {
    setBusy(action);
    setError(null);
    try {
      onChanged(await campaignsApi[action](campaignId));
    } catch (err) {
      setError(toApiError(err));
    } finally {
      setBusy(null);
    }
  };

  const exportData = async (format: 'xlsx' | 'csv') => {
    setBusy('export');
    setError(null);
    try {
      const blob = await campaignsApi.exportFile(campaignId, format);
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `chien-dich-${campaignId.slice(0, 8)}.${format}`;
      link.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      setError(toApiError(err));
    } finally {
      setBusy(null);
    }
  };

  return {
    busy,
    error,
    pause: () => run('pause'),
    resume: () => run('resume'),
    stop: () => run('stop'),
    exportData,
  };
}
