import type { CampaignStatus } from '@/types/campaign';

import { Badge, type BadgeTone } from './Badge';

const STATUS: Record<CampaignStatus, { label: string; tone: BadgeTone }> = {
  IDLE: { label: 'Chờ chạy', tone: 'neutral' },
  RUNNING: { label: 'Đang chạy', tone: 'accent' },
  PAUSED: { label: 'Tạm dừng', tone: 'warn' },
  COMPLETED: { label: 'Hoàn thành', tone: 'ok' },
  FAILED: { label: 'Lỗi', tone: 'bad' },
};

export function StatusBadge({ status }: { status: CampaignStatus }) {
  const { label, tone } = STATUS[status];
  return <Badge tone={tone} dot>{label}</Badge>;
}

export const statusTone = (status: CampaignStatus): BadgeTone => STATUS[status].tone;
