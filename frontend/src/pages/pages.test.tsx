import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';

import { TourProvider } from '@/components/tour/TourProvider';
import { UpdaterProvider } from '@/components/update/UpdaterProvider';

import { DashboardPage } from './DashboardPage';
import { FormWorkspacePage } from './FormWorkspacePage';
import { HelpPage } from './HelpPage';

vi.mock('@/api/endpoints', async () => {
  const { sampleStructure: build } = await import('@/test/fixtures');
  const structure = build();
  const form = { id: 'f1', title: structure.title, view_url: structure.view_url, submit_url: structure.submit_url, total_pages: 4, question_count: 5, is_demo: true, created_at: '2026-11-02T10:00:00Z' };
  return {
    formsApi: { list: vi.fn(async () => [form]), get: vi.fn(async () => ({ ...form, structure })), openDemo: vi.fn(async () => ({ ...form, structure })), parse: vi.fn() },
    campaignsApi: { list: vi.fn(async () => []) },
    settingsApi: { get: vi.fn(async () => ({ app_version: '0.1.0', data_dir: 'C:/x', gemini_model: 'gemini-flash-latest', gemini_key_configured: false })) },
    aiApi: {},
    excelApi: {},
  };
});

function renderAt(path: string, element: React.ReactElement, route: string) {
  localStorage.setItem('autoform.tour-seen', '1');
  return render(
    <MemoryRouter initialEntries={[path]}>
      <UpdaterProvider>
        <TourProvider>
          <Routes><Route path={route} element={element} /></Routes>
        </TourProvider>
      </UpdaterProvider>
    </MemoryRouter>,
  );
}

describe('các màn hình chính vẽ được với dữ liệu thật', () => {
  it('Tổng quan: có ô dán link, form mẫu và trạng thái trống', async () => {
    renderAt('/', <DashboardPage />, '/');
    expect(await screen.findByText('Chưa có chiến dịch nào')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Thử với form mẫu' })).toBeInTheDocument();
    await waitFor(() => expect(screen.getAllByText('Form thử').length).toBeGreaterThan(0));
  });

  it('Cấu hình: chế độ tập dùng, thẻ rẽ nhánh và nút Bắt đầu bị khóa khi thiếu câu mẫu', async () => {
    renderAt('/forms/f1', <FormWorkspacePage />, '/forms/:formId');
    expect(await screen.findByText(/Chế độ tập dùng/)).toBeInTheDocument();
    expect(screen.getByText('Rẽ nhánh')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Bắt đầu chạy/ })).toBeDisabled();
    expect(screen.getByText(/1 câu chưa cấu hình xong/)).toBeInTheDocument();
  });

  it('Hướng dẫn: có nút bắt đầu tour và tìm kiếm', async () => {
    renderAt('/help', <HelpPage />, '/help');
    expect(screen.getByRole('button', { name: 'Bắt đầu tour hướng dẫn' })).toBeInTheDocument();
    expect(screen.getByText('Cronbach’s Alpha (α)')).toBeInTheDocument();
  });
});
