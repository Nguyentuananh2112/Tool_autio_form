/**
 * Thông báo kết thúc chiến dịch (màn 13): chọn kiểu thông báo, tiêu đề và nút theo kết quả.
 * Hàm thuần để test được; giao diện ở components/campaign/Completion*.
 */
import type { CampaignRead, CampaignSummary } from '@/types/campaign';

export type CompletionKind = 'success' | 'partial' | 'failed';
export type CompletionAction = 'view' | 'export' | 'log' | 'retry' | 'resume' | 'config';

export interface CompletionView {
  kind: CompletionKind;
  title: string;
  subtitle: string;
  actions: CompletionAction[]; // nút phụ trước, nút chính cuối
}

export function completionView(summary: CampaignSummary): CompletionView {
  const { completed_count: ok, failed_count: bad, total_target: total, auto_paused: paused } = summary;
  const top = summary.reasons[0]?.category;
  const kind: CompletionKind = ok >= total && bad === 0 && !paused ? 'success' : ok === 0 ? 'failed' : 'partial';

  let title: string;
  if (kind === 'success') title = `Đã gửi xong ${ok}/${total} phản hồi`;
  else if (kind === 'failed') title = 'Không gửi được phản hồi nào';
  else if (paused) title = `Đã tự tạm dừng sau ${ok}/${total} phản hồi`;
  else title = `Đã gửi ${ok}/${total} — ${bad} phản hồi không gửi được`;

  const note = summary.status_reason
    ?? (kind === 'success' ? 'Google đã xác nhận nhận đủ.' : `${ok} phản hồi đã vào form.`);

  let primary: CompletionAction;
  if (kind === 'success') primary = 'view';
  else if (top === 'REJECTED' || top === 'FORM_CLOSED') primary = 'config';
  else if (paused && top === 'RATE_LIMITED') primary = 'resume';
  else if (bad > 0) primary = 'retry';
  else primary = paused ? 'resume' : 'view';

  return {
    kind,
    title,
    subtitle: `${summary.name} · ${note}`,
    actions: [kind === 'success' ? 'export' : 'log', primary],
  };
}

export const ACTION_LABELS: Record<CompletionAction, (summary: CampaignSummary) => string> = {
  view: () => 'Xem chiến dịch',
  export: () => 'Xuất dữ liệu (Excel)',
  log: () => 'Xem nhật ký',
  retry: (s) => `Gửi lại ${s.failed_count} phản hồi lỗi`,
  resume: () => 'Tiếp tục',
  config: () => 'Mở Cấu hình',
};

/** Chiến dịch đã dừng hẳn lần này: chạy xong / lỗi / app tự tạm dừng (người dùng tự dừng thì không báo). */
export function hasEnded(campaign: CampaignRead): boolean {
  if (campaign.is_active && !campaign.auto_paused) return false;
  return campaign.status === 'COMPLETED' || campaign.status === 'FAILED' || (campaign.status === 'PAUSED' && campaign.auto_paused);
}

export interface Snapshot {
  key: string;
  ended: boolean;
}

export const snapshotOf = (campaign: CampaignRead): Snapshot => ({
  key: `${campaign.status}:${campaign.completed_count}:${campaign.failed_count}`,
  ended: hasEnded(campaign),
});

/**
 * Chiến dịch nào VỪA kết thúc giữa hai lần kiểm tra. Lần kiểm tra đầu chỉ ghi nhận (không báo chiến dịch cũ),
 * trừ chiến dịch tạo sau khi app mở mà chạy xong rất nhanh giữa hai lần kiểm tra.
 */
export function justEnded(
  previous: Map<string, Snapshot> | null,
  campaigns: CampaignRead[],
  watchingSince: number,
): CampaignRead[] {
  if (previous === null) return [];
  return campaigns.filter((campaign) => {
    const now = snapshotOf(campaign);
    if (!now.ended) return false;
    const before = previous.get(campaign.id);
    if (!before) return Date.parse(campaign.created_at) >= watchingSince;
    return !before.ended || before.key !== now.key;
  });
}
