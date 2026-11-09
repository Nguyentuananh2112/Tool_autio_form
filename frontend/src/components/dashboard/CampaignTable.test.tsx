import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';

import type { CampaignRead } from '@/types/campaign';

import { CampaignTable } from './CampaignTable';

const campaign = (patch: Partial<CampaignRead>): CampaignRead => ({
  id: 'c', form_id: 'f', form_title: 'Interview Questions', name: 'Interview Questions — 19:41', data_source: 'PROBABILITY',
  status: 'COMPLETED', total_target: 50, completed_count: 0, failed_count: 0,
  schedule: { mode: 'BURST', duration_minutes: null, concurrency: 5 }, proxy: null, use_playwright_fallback: true,
  created_at: '2026-11-09T12:41:58Z', is_active: false, pause_reason: null, ...patch,
});

function renderTable(rows: CampaignRead[]) {
  return render(<MemoryRouter><CampaignTable campaigns={rows} /></MemoryRouter>);
}

describe('bảng chiến dịch (BUG-019)', () => {
  it('50/50 lỗi không được hiện "Hoàn thành" xanh', () => {
    renderTable([campaign({ failed_count: 50 })]);
    expect(screen.getByText('Không gửi được')).toBeInTheDocument();
    expect(screen.queryByText('Hoàn thành')).not.toBeInTheDocument();
    expect(screen.getByRole('progressbar')).toHaveAccessibleName(/0 thành công, 50 lỗi/);
  });

  it('xong nhưng có một phần lỗi thì báo "có lỗi"', () => {
    renderTable([campaign({ completed_count: 45, failed_count: 5 })]);
    expect(screen.getByText('Hoàn thành · có lỗi')).toBeInTheDocument();
    expect(screen.getByText('45')).toBeInTheDocument();
  });

  it('thành công trọn vẹn vẫn là "Hoàn thành"', () => {
    renderTable([campaign({ completed_count: 50 })]);
    expect(screen.getByText('Hoàn thành')).toBeInTheDocument();
  });
});
