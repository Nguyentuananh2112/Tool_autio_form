import { useState } from 'react';
import { useNavigate } from 'react-router-dom';

import { type ApiError, toApiError } from '@/api/client';
import { campaignsApi } from '@/api/endpoints';
import { buildCampaignPayload } from '@/lib/campaignPayload';
import type { FormConfig } from '@/store/formConfigStore';
import type { TrialSubmitResponse } from '@/types/campaign';

/** "Gửi thử 1 phản hồi" và "Bắt đầu chạy" cho màn hình Cấu hình. */
export function useCampaignActions(formId: string, formTitle: string, config: FormConfig) {
  const navigate = useNavigate();
  const [busy, setBusy] = useState<'trial' | 'start' | null>(null);
  const [error, setError] = useState<ApiError | null>(null);
  const [trial, setTrial] = useState<TrialSubmitResponse | null>(null);

  const runTrial = async (dryRun: boolean) => {
    setBusy('trial');
    setError(null);
    try {
      setTrial(await campaignsApi.trialSubmit({
        form_id: formId,
        rules: Object.values(config.rules),
        spss_groups: config.groups,
        proxy: config.proxy.trim() || null,
        dry_run: dryRun,
      }));
    } catch (err) {
      setError(toApiError(err));
    } finally {
      setBusy(null);
    }
  };

  const start = async () => {
    setBusy('start');
    setError(null);
    try {
      const campaign = await campaignsApi.create(buildCampaignPayload(formId, formTitle, config));
      await campaignsApi.start(campaign.id);
      navigate(`/campaigns/${campaign.id}`);
    } catch (err) {
      setError(toApiError(err));
      setBusy(null);
    }
  };

  return { busy, error, trial, clearTrial: () => setTrial(null), runTrial, start };
}
