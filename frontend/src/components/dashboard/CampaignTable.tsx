import { Link } from 'react-router-dom';

import { ProgressBar } from '@/components/ui/ProgressBar';
import { StatusBadge, statusTone } from '@/components/ui/StatusBadge';
import { formatDateTime } from '@/lib/format';
import type { CampaignRead } from '@/types/campaign';

const MODE_LABEL = { BURST: 'Tốc độ tối đa', SCHEDULED: 'Rải đều tự nhiên' } as const;

function modeText(campaign: CampaignRead): string {
  const { mode, duration_minutes: minutes } = campaign.schedule;
  return mode === 'SCHEDULED' && minutes ? `${MODE_LABEL[mode]} · ${minutes} phút` : MODE_LABEL[mode];
}

function barTone(campaign: CampaignRead) {
  const tone = statusTone(campaign.status);
  return tone === 'neutral' ? 'accent' : tone;
}

export function CampaignTable({ campaigns }: { campaigns: CampaignRead[] }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[820px] border-collapse text-sm">
        <thead>
          <tr className="text-left text-xs uppercase tracking-wide text-muted">
            <th scope="col" className="px-5 py-3 font-semibold">Chiến dịch</th>
            <th scope="col" className="px-3 py-3 font-semibold">Trạng thái</th>
            <th scope="col" className="w-56 px-3 py-3 font-semibold">Tiến độ</th>
            <th scope="col" className="px-3 py-3 font-semibold">Cách gửi</th>
            <th scope="col" className="px-5 py-3 font-semibold">Tạo lúc</th>
          </tr>
        </thead>
        <tbody>
          {campaigns.map((campaign) => {
            const done = campaign.completed_count + campaign.failed_count;
            const pct = campaign.total_target ? Math.round((done / campaign.total_target) * 100) : 0;
            return (
              <tr key={campaign.id} className="border-t border-line">
                <td className="px-5 py-3.5">
                  <div className="flex flex-col gap-0.5">
                    <Link to={`/campaigns/${campaign.id}`} className="font-semibold text-ink no-underline hover:text-accent">{campaign.name}</Link>
                    <span className="text-[13px] text-muted">{campaign.form_title}</span>
                  </div>
                </td>
                <td className="px-3 py-3.5"><StatusBadge status={campaign.status} /></td>
                <td className="px-3 py-3.5">
                  <div className="flex flex-col gap-1.5">
                    <ProgressBar value={done} max={campaign.total_target} label={`Tiến độ ${campaign.name}`} tone={barTone(campaign)} size="sm" />
                    <span className="tabular text-xs text-muted">{done} / {campaign.total_target} · {pct}%</span>
                  </div>
                </td>
                <td className="px-3 py-3.5 text-muted">{modeText(campaign)}</td>
                <td className="px-5 py-3.5 text-muted">{formatDateTime(campaign.created_at)}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
