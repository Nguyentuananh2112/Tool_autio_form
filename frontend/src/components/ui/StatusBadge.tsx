import type { CampaignStatus } from '@/types/campaign';

import { Badge, type BadgeTone } from './Badge';

const STATUS: Record<CampaignStatus, { label: string; tone: BadgeTone }> = {
  IDLE: { label: 'Chờ chạy', tone: 'neutral' },
  RUNNING: { label: 'Đang chạy', tone: 'accent' },
  PAUSED: { label: 'Tạm dừng', tone: 'warn' },
  COMPLETED: { label: 'Hoàn thành', tone: 'ok' },
  FAILED: { label: 'Lỗi', tone: 'bad' },
};

/** Xong mà có phản hồi lỗi thì không được trông như thành công trọn vẹn (BUG-019). */
function view(status: CampaignStatus, completed: number, failed: number): { label: string; tone: BadgeTone } {
  if (status === 'COMPLETED' && failed > 0) {
    return completed === 0 ? { label: 'Không gửi được', tone: 'bad' } : { label: 'Hoàn thành · có lỗi', tone: 'warn' };
  }
  return STATUS[status];
}

export function StatusBadge({ status, completed = 0, failed = 0 }: { status: CampaignStatus; completed?: number; failed?: number }) {
  const { label, tone } = view(status, completed, failed);
  return <Badge tone={tone} dot>{label}</Badge>;
}

export const statusTone = (status: CampaignStatus, completed = 0, failed = 0): BadgeTone => view(status, completed, failed).tone;
