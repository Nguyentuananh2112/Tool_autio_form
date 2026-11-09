import { Link } from 'react-router-dom';

import { StatusBadge } from '@/components/ui/StatusBadge';
import { formatDateTime } from '@/lib/format';
import type { CampaignRead } from '@/types/campaign';

const MODE_LABEL = { BURST: 'Tốc độ tối đa', SCHEDULED: 'Rải đều tự nhiên' } as const;

function modeText(campaign: CampaignRead): string {
  const { mode, duration_minutes: minutes } = campaign.schedule;
  return mode === 'SCHEDULED' && minutes ? `${MODE_LABEL[mode]} · ${minutes} phút` : MODE_LABEL[mode];
}

/** Thanh tách xanh (thành công) / đỏ (lỗi): trước đây gộp chung nên 50 lỗi vẫn hiện xanh 100% (BUG-019). */
function SplitProgress({ campaign }: { campaign: CampaignRead }) {
  const { completed_count: ok, failed_count: bad, total_target: total } = campaign;
  const width = (part: number) => `${total ? Math.min(100, (part / total) * 100) : 0}%`;
  return (
    <div className="flex flex-col gap-1.5">
      <div role="progressbar" aria-label={`Tiến độ ${campaign.name}: ${ok} thành công, ${bad} lỗi`} aria-valuemin={0} aria-valuemax={total} aria-valuenow={ok}
        className="flex h-1.5 overflow-hidden rounded-full bg-sunken">
        <span className="bg-ok" style={{ width: width(ok) }} />
        <span className="bg-bad" style={{ width: width(bad) }} />
      </div>
      <span className="tabular text-xs text-muted">
        <b className="font-semibold text-ok">{ok}</b> thành công{bad > 0 && <> · <b className="font-semibold text-bad">{bad}</b> lỗi</>} / {total}
      </span>
    </div>
  );
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
            return (
              <tr key={campaign.id} className="border-t border-line">
                <td className="px-5 py-3.5">
                  <div className="flex flex-col gap-0.5">
                    <Link to={`/campaigns/${campaign.id}`} className="font-semibold text-ink no-underline hover:text-accent">{campaign.name}</Link>
                    <span className="text-[13px] text-muted">{campaign.form_title}</span>
                  </div>
                </td>
                <td className="px-3 py-3.5"><StatusBadge status={campaign.status} completed={campaign.completed_count} failed={campaign.failed_count} /></td>
                <td className="px-3 py-3.5">
                  <SplitProgress campaign={campaign} />
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
