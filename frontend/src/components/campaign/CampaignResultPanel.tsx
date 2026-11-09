import { campaignsApi } from '@/api/endpoints';
import { Card } from '@/components/ui/Card';
import { useAsyncData } from '@/hooks/useAsyncData';
import { completionView, hasEnded } from '@/lib/completion';
import type { CampaignRead } from '@/types/campaign';

import { CompletionActions } from './CompletionActions';
import { CompletionContent, CompletionIcon } from './CompletionContent';

/** Kết quả trên trang chiến dịch — xem lại thông báo kết thúc sau khi đã đóng hộp thoại (màn 13). */
export function CampaignResultPanel({ campaign }: { campaign: CampaignRead }) {
  const ended = hasEnded(campaign);
  const key = `${campaign.status}:${campaign.completed_count}:${campaign.failed_count}`;
  const summary = useAsyncData(() => (ended ? campaignsApi.summary(campaign.id) : Promise.resolve(null)), [campaign.id, ended, key]);
  const data = summary.data;
  if (!ended || !data) return null;
  const view = completionView(data);
  if (view.kind === 'success') return null; // thành công trọn vẹn: phần tiến độ phía trên đã đủ rõ

  return (
    <Card aria-labelledby="result-title" className="flex flex-col gap-4 p-5">
      <div className="flex items-start gap-3.5">
        <CompletionIcon kind={view.kind} />
        <div className="flex flex-col gap-1">
          <h2 id="result-title" className="m-0 text-[17px] font-semibold">{view.title}</h2>
          <p className="m-0 text-[13px] text-muted">{view.subtitle}</p>
        </div>
      </div>
      <CompletionContent summary={data} />
      <CompletionActions summary={data} actions={view.actions.filter((a) => a !== 'view' && a !== 'log')} onDone={() => undefined} />
    </Card>
  );
}
