import type { CampaignRead, CampaignSummary, FailureReason } from '@/types/campaign';

import { ACTION_LABELS, completionView, hasEnded, justEnded, snapshotOf } from './completion';

const reason = (category: FailureReason['category'], count: number): FailureReason => ({
  category, title: category, fix: 'Cách xử lý', count, detail: 'Chi tiết',
});

const summary = (patch: Partial<CampaignSummary>): CampaignSummary => ({
  campaign_id: 'c1', name: 'Interview — 19:58', form_id: 'f1', form_title: 'Interview', status: 'COMPLETED',
  status_reason: null, auto_paused: false, total_target: 50, completed_count: 50, failed_count: 0, remaining: 0,
  started_at: null, finished_at: null, duration_seconds: 60, reasons: [], ...patch,
});

const campaign = (patch: Partial<CampaignRead>): CampaignRead => ({
  id: 'c1', form_id: 'f1', form_title: 'F', name: 'C', data_source: 'PROBABILITY', status: 'RUNNING', total_target: 10,
  completed_count: 0, failed_count: 0, schedule: { mode: 'BURST', duration_minutes: null, concurrency: 1 }, proxy: null,
  use_playwright_fallback: true, created_at: '2026-11-09T12:00:00Z', is_active: true, pause_reason: null,
  status_reason: null, auto_paused: false, ...patch,
});

describe('completionView (màn 13)', () => {
  it('thành công trọn vẹn: Xuất dữ liệu + Xem chiến dịch', () => {
    const view = completionView(summary({}));
    expect(view.kind).toBe('success');
    expect(view.title).toBe('Đã gửi xong 50/50 phản hồi');
    expect(view.subtitle).toContain('Google đã xác nhận');
    expect(view.actions).toEqual(['export', 'view']);
  });

  it('một phần lỗi mạng: gợi ý Gửi lại đúng số phản hồi lỗi', () => {
    const s = summary({ completed_count: 45, failed_count: 5, reasons: [reason('NETWORK', 5)] });
    const view = completionView(s);
    expect(view.kind).toBe('partial');
    expect(view.title).toBe('Đã gửi 45/50 — 5 phản hồi không gửi được');
    expect(view.actions).toEqual(['log', 'retry']);
    expect(ACTION_LABELS.retry(s)).toBe('Gửi lại 5 phản hồi lỗi');
  });

  it('không gửi được vì Google từ chối dữ liệu: dẫn về Cấu hình kèm lý do', () => {
    const view = completionView(summary({
      status: 'FAILED', completed_count: 0, failed_count: 50, reasons: [reason('REJECTED', 50)],
      status_reason: 'Không gửi được phản hồi nào: Google từ chối cả 50 lần.',
    }));
    expect(view.kind).toBe('failed');
    expect(view.title).toBe('Không gửi được phản hồi nào');
    expect(view.subtitle).toContain('Google từ chối cả 50 lần');
    expect(view.actions).toEqual(['log', 'config']);
  });

  it('tự tạm dừng vì Google giới hạn: nút Tiếp tục', () => {
    const view = completionView(summary({
      status: 'PAUSED', auto_paused: true, completed_count: 20, failed_count: 0, remaining: 30,
      reasons: [reason('RATE_LIMITED', 3)],
    }));
    expect(view.kind).toBe('partial');
    expect(view.title).toBe('Đã tự tạm dừng sau 20/50 phản hồi');
    expect(view.actions).toEqual(['log', 'resume']);
  });

  it('form đã đóng: dẫn về Cấu hình', () => {
    expect(completionView(summary({ completed_count: 3, failed_count: 47, reasons: [reason('FORM_CLOSED', 47)] })).actions).toEqual(['log', 'config']);
  });
});

describe('justEnded: chiến dịch vừa kết thúc', () => {
  const since = Date.parse('2026-11-09T12:00:00Z');

  it('lần kiểm tra đầu không báo chiến dịch cũ', () => {
    expect(justEnded(null, [campaign({ status: 'COMPLETED', is_active: false })], since)).toEqual([]);
  });

  it('đang chạy → xong thì báo một lần', () => {
    const running = campaign({});
    const done = campaign({ status: 'COMPLETED', is_active: false, completed_count: 10 });
    const before = new Map([[running.id, snapshotOf(running)]]);
    expect(justEnded(before, [done], since).map((c) => c.id)).toEqual(['c1']);
    const after = new Map([[done.id, snapshotOf(done)]]);
    expect(justEnded(after, [done], since)).toEqual([]);
  });

  it('chiến dịch mới chạy xong rất nhanh giữa hai lần kiểm tra vẫn được báo', () => {
    const quick = campaign({ status: 'FAILED', is_active: false, failed_count: 2, created_at: '2026-11-09T12:00:05Z' });
    expect(justEnded(new Map(), [quick], since)).toHaveLength(1);
    const old = campaign({ status: 'COMPLETED', is_active: false, created_at: '2026-11-08T12:00:00Z' });
    expect(justEnded(new Map(), [old], since)).toEqual([]);
  });

  it('gửi lại xong (số liệu đổi) thì báo lần nữa', () => {
    const first = campaign({ status: 'COMPLETED', is_active: false, completed_count: 8, failed_count: 2 });
    const again = campaign({ status: 'COMPLETED', is_active: false, completed_count: 10, failed_count: 0 });
    expect(justEnded(new Map([[first.id, snapshotOf(first)]]), [again], since)).toHaveLength(1);
  });

  it('người dùng tự tạm dừng thì không báo; app tự tạm dừng thì báo', () => {
    const running = new Map([['c1', snapshotOf(campaign({}))]]);
    expect(justEnded(running, [campaign({ status: 'PAUSED', is_active: true })], since)).toEqual([]);
    expect(justEnded(running, [campaign({ status: 'PAUSED', is_active: true, auto_paused: true })], since)).toHaveLength(1);
  });

  it('hasEnded', () => {
    expect(hasEnded(campaign({}))).toBe(false);
    expect(hasEnded(campaign({ status: 'COMPLETED', is_active: false }))).toBe(true);
    expect(hasEnded(campaign({ status: 'PAUSED', is_active: false }))).toBe(false);
  });
});
