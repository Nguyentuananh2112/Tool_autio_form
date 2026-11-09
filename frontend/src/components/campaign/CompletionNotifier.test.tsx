import { act, fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';

import { campaignsApi } from '@/api/endpoints';
import type { CampaignRead, CampaignSummary } from '@/types/campaign';

import { CompletionNotifier } from './CompletionNotifier';

vi.mock('@/api/endpoints', () => ({
  campaignsApi: { list: vi.fn(), summary: vi.fn(), retryFailed: vi.fn(async () => ({ retried: 5 })), resume: vi.fn(), exportFile: vi.fn() },
}));

const base: CampaignRead = {
  id: 'c1', form_id: 'f1', form_title: 'Interview', name: 'Interview — 20:15', data_source: 'PROBABILITY', status: 'RUNNING',
  total_target: 50, completed_count: 10, failed_count: 0, schedule: { mode: 'BURST', duration_minutes: null, concurrency: 1 },
  proxy: null, use_playwright_fallback: true, created_at: '2026-11-09T12:00:00Z', is_active: true, pause_reason: null,
  status_reason: null, auto_paused: false,
};

const partial: CampaignSummary = {
  campaign_id: 'c1', name: 'Interview — 20:15', form_id: 'f1', form_title: 'Interview', status: 'COMPLETED',
  status_reason: null, auto_paused: false, total_target: 50, completed_count: 45, failed_count: 5, remaining: 0,
  started_at: null, finished_at: null, duration_seconds: 2520,
  reasons: [{ category: 'NETWORK', title: 'Mất kết nối mạng', fix: 'Kiểm tra Internet / proxy rồi gửi lại.', count: 5, detail: 'Không kết nối được tới Google Form.' }],
};

function renderNotifier() {
  return render(
    <MemoryRouter initialEntries={['/']}>
      <CompletionNotifier />
      <Routes>
        <Route path="/" element={<p>Tổng quan</p>} />
        <Route path="/campaigns/:id" element={<p>Trang chiến dịch</p>} />
      </Routes>
    </MemoryRouter>,
  );
}

beforeEach(() => {
  vi.useFakeTimers({ shouldAdvanceTime: true });
  vi.mocked(campaignsApi.list)
    .mockResolvedValueOnce([base])
    .mockResolvedValue([{ ...base, status: 'COMPLETED', is_active: false, completed_count: 45, failed_count: 5 }]);
  vi.mocked(campaignsApi.summary).mockResolvedValue(partial);
});

afterEach(() => {
  vi.useRealTimers();
  vi.clearAllMocks();
});

describe('thông báo kết thúc ở mọi màn hình (màn 13)', () => {
  it('chiến dịch chạy xong có lỗi: hiện lý do, cách xử lý và gửi lại đúng phản hồi lỗi', async () => {
    renderNotifier();
    await act(async () => { await vi.advanceTimersByTimeAsync(3_100); });
    expect(await screen.findByRole('dialog')).toBeInTheDocument();
    expect(screen.getByText('Đã gửi 45/50 — 5 phản hồi không gửi được')).toBeInTheDocument();
    expect(screen.getByText('Mất kết nối mạng')).toBeInTheDocument();
    expect(screen.getByText(/Không kết nối được tới Google Form/)).toBeInTheDocument();
    expect(screen.getByText('5 lần')).toBeInTheDocument();
    expect(screen.getByText('42 phút')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'Gửi lại 5 phản hồi lỗi' }));
    expect(await screen.findByText('Trang chiến dịch')).toBeInTheDocument();
    expect(campaignsApi.retryFailed).toHaveBeenCalledWith('c1');
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('chiến dịch đã xong từ trước khi mở app thì không làm phiền', async () => {
    vi.mocked(campaignsApi.list).mockReset().mockResolvedValue([{ ...base, status: 'COMPLETED', is_active: false, created_at: '2026-01-01T00:00:00Z' }]);
    renderNotifier();
    await act(async () => { await vi.advanceTimersByTimeAsync(20_000); });
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    expect(campaignsApi.summary).not.toHaveBeenCalled();
  });
});
