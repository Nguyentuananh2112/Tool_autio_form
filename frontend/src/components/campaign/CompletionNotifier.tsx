import { useCallback, useState } from 'react';
import { useNavigate } from 'react-router-dom';

import { useCampaignWatcher } from '@/hooks/useCampaignWatcher';
import { completionView } from '@/lib/completion';
import { notifyDesktop } from '@/lib/desktopNotify';
import type { CampaignSummary } from '@/types/campaign';

import { CompletionDialog } from './CompletionDialog';

const DESKTOP_PREFIX = { success: '✓ ', partial: '! ', failed: '✕ ' } as const;

/** Gắn một lần ở gốc app: chiến dịch nào kết thúc thì hiện hộp thoại + thông báo Windows (màn 13). */
export function CompletionNotifier() {
  const navigate = useNavigate();
  const [queue, setQueue] = useState<CampaignSummary[]>([]);

  const onEnded = useCallback((summary: CampaignSummary) => {
    setQueue((current) => [...current.filter((s) => s.campaign_id !== summary.campaign_id), summary]);
    const view = completionView(summary);
    const reason = summary.reasons[0];
    notifyDesktop(
      `${DESKTOP_PREFIX[view.kind]}${view.title}`,
      reason ? `${reason.title} · bấm để xem lý do` : summary.name,
      () => navigate(`/campaigns/${summary.campaign_id}`),
    );
  }, [navigate]);

  useCampaignWatcher(onEnded);

  const current = queue[0];
  if (!current) return null;
  return <CompletionDialog key={current.campaign_id} summary={current} onClose={() => setQueue((q) => q.slice(1))} />;
}
