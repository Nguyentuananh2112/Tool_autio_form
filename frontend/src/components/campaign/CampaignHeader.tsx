import { Download, Pause, Play } from 'lucide-react';
import { Link } from 'react-router-dom';

import { Button } from '@/components/ui/Button';
import { StatusBadge } from '@/components/ui/StatusBadge';
import type { useCampaignControls } from '@/hooks/useCampaignControls';
import type { CampaignRead } from '@/types/campaign';

type Controls = ReturnType<typeof useCampaignControls>;

function scheduleText(campaign: CampaignRead): string {
  const { mode, duration_minutes: minutes } = campaign.schedule;
  return mode === 'SCHEDULED' ? `Rải đều tự nhiên · ${campaign.total_target} phản hồi trong ${minutes} phút` : `Tốc độ tối đa · ${campaign.total_target} phản hồi`;
}

export function CampaignHeader({ campaign, controls }: { campaign: CampaignRead; controls: Controls }) {
  const canResume = campaign.status === 'PAUSED' || campaign.status === 'FAILED' || campaign.status === 'IDLE';
  return (
    <header className="flex flex-wrap items-end justify-between gap-4">
      <div className="flex flex-col gap-1.5">
        <Link to="/campaigns" className="text-[13px] text-accent no-underline">← Tất cả chiến dịch</Link>
        <div className="flex flex-wrap items-center gap-3">
          <h1 className="m-0 text-[26px] font-bold tracking-tight">{campaign.name}</h1>
          <StatusBadge status={campaign.status} />
        </div>
        <span className="text-sm text-muted">{scheduleText(campaign)} · {campaign.form_title}</span>
      </div>
      <div data-tour="controls" className="flex flex-wrap gap-2">
        {campaign.status === 'RUNNING' && (
          <Button onClick={() => void controls.pause()} loading={controls.busy === 'pause'}><Pause aria-hidden className="size-4" />Tạm dừng</Button>
        )}
        {canResume && (
          <Button variant="primary" onClick={() => void controls.resume()} loading={controls.busy === 'resume'}>
            <Play aria-hidden className="size-4" />{campaign.status === 'IDLE' ? 'Bắt đầu' : 'Tiếp tục'}
          </Button>
        )}
        <Button onClick={() => void controls.exportData('xlsx')} loading={controls.busy === 'export'}><Download aria-hidden className="size-4" />Xuất dữ liệu cho SPSS</Button>
        {campaign.is_active && (
          <Button variant="danger" onClick={() => void controls.stop()} loading={controls.busy === 'stop'}>Dừng hẳn</Button>
        )}
      </div>
    </header>
  );
}
