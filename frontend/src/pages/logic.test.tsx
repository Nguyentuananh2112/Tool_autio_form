import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';

import { ApiError } from '@/api/client';
import { campaignsApi, logicApi, settingsApi } from '@/api/endpoints';
import type { LogicMap, LogicReviewResult } from '@/types/logic';

import { LogicReviewPage } from './LogicReviewPage';

const LOGIC: LogicMap = {
  version: 1,
  attitude_groups: [{ group_id: 'g1', name: 'Thái độ với quán', items: [{ entry_id: '1', positive_high: true }, { entry_id: '4', positive_high: false }] }],
  rules: [{ rule_id: 'r1', if_entry: '1', if_values: ['Nam'], then_entry: '4', then_op: 'IS', then_values: ['Trà'], strength: 'ALWAYS', reason: null }],
  exclusive_options: [{ entry_id: '3', value: 'Nhà' }],
  text_attitudes: [],
  consistency: 'MODERATE',
  source: 'AI',
  model: 'gemini-test',
  analyzed_at: '2026-11-03T10:00:00Z',
  confirmed: false,
};

const result = (logic: LogicMap): LogicReviewResult => ({
  sample_size: 200, inconsistent_before: 57, inconsistent_after: 0, repaired: 60, regenerated: 2,
  violations: [{ kind: 'RULE', key: 'r1', before: 40, after: 0 }],
  correlations: [{ group_id: 'g1', name: 'Thái độ với quán', before: -0.04, after: 0.61 }],
  drifts: [], sample: { attitude: 'khá tích cực', answers: { 1: ['Nam'], 4: ['Trà'] } }, logic, ready: true,
});

vi.mock('@/api/endpoints', async () => {
  const { sampleStructure: build } = await import('@/test/fixtures');
  const structure = build();
  const form = { id: 'f1', title: structure.title, view_url: structure.view_url, submit_url: structure.submit_url, total_pages: 4, question_count: 5, is_demo: false, created_at: '2026-11-02T10:00:00Z', structure };
  return {
    formsApi: { get: vi.fn(async () => form) },
    logicApi: { get: vi.fn(), analyze: vi.fn(), save: vi.fn(), review: vi.fn() },
    campaignsApi: { create: vi.fn(async () => ({ id: 'c1' })), start: vi.fn(async () => ({ id: 'c1' })) },
    settingsApi: { saveGeminiKey: vi.fn(async () => undefined) },
  };
});

function renderPage() {
  return render(
    <MemoryRouter initialEntries={['/forms/f1/logic']}>
      <Routes>
        <Route path="/forms/:formId/logic" element={<LogicReviewPage />} />
        <Route path="/campaigns/:campaignId" element={<p>Trang chiến dịch</p>} />
      </Routes>
    </MemoryRouter>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(logicApi.get).mockResolvedValue(LOGIC);
  vi.mocked(logicApi.review).mockImplementation(async (_id, payload) => result(payload.logic ?? LOGIC));
  vi.mocked(logicApi.save).mockImplementation(async (_id, logic) => logic);
});

describe('màn Soát logic (artboard 11)', () => {
  it('đọc bản đồ đã lưu, soát mẫu thử rồi xác nhận và chạy', async () => {
    renderPage();
    expect(await screen.findByText('Sẵn sàng chạy')).toBeInTheDocument();
    expect(screen.getByText('Thái độ với quán')).toBeInTheDocument();
    expect(screen.getByText(/1 nhóm thái độ \(2 câu\), 1 ràng buộc, 1 ô loại trừ/)).toBeInTheDocument();
    expect(screen.getByText('Luôn')).toBeInTheDocument();
    expect(logicApi.analyze).not.toHaveBeenCalled();

    fireEvent.click(screen.getByRole('button', { name: /Xác nhận & chạy/ }));
    expect(await screen.findByText('Trang chiến dịch')).toBeInTheDocument();
    expect(vi.mocked(logicApi.save).mock.calls[0]?.[1].confirmed).toBe(true);
    expect(campaignsApi.create).toHaveBeenCalledTimes(1);
    expect(campaignsApi.start).toHaveBeenCalledWith('c1');
  });

  it('sửa bản đồ thì phải soát lại mới được chạy', async () => {
    renderPage();
    await screen.findByText('Sẵn sàng chạy');
    fireEvent.click(screen.getAllByRole('button', { name: /Đổi chiều/ })[0]!);
    expect(screen.getByText('Bạn vừa sửa bản đồ logic')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Xác nhận & chạy/ })).toBeDisabled();

    fireEvent.click(screen.getByRole('button', { name: 'Soát lại' }));
    await waitFor(() => expect(logicApi.review).toHaveBeenCalledTimes(2));
    expect(vi.mocked(logicApi.review).mock.calls[1]?.[1].logic?.attitude_groups[0]?.items[0]?.positive_high).toBe(false);
    await waitFor(() => expect(screen.getByRole('button', { name: /Xác nhận & chạy/ })).toBeEnabled());
  });

  it('form chưa soát: AI đọc câu hỏi; hết lượt thì hỏi key rồi chạy tiếp', async () => {
    vi.mocked(logicApi.get).mockResolvedValue(null);
    vi.mocked(logicApi.analyze)
      .mockRejectedValueOnce(new ApiError('Hết lượt AI — dán API key Gemini của bạn để tiếp tục.', 429, [], 'AI_KEYS_UNAVAILABLE', {
        keys: [{ slot: 'USER', state: 'MISSING' }, { slot: 'SHARED', state: 'EXHAUSTED' }, { slot: 'BACKUP', state: 'INVALID' }],
      }))
      .mockResolvedValueOnce(LOGIC);
    renderPage();

    expect(await screen.findByRole('dialog')).toBeInTheDocument();
    expect(screen.getByText('Hết lượt')).toBeInTheDocument();
    expect(screen.getByText('Không hợp lệ')).toBeInTheDocument();
    const save = screen.getByRole('button', { name: /Lưu key/ });
    expect(save).toBeDisabled();

    fireEvent.change(screen.getByLabelText('API key Gemini của bạn'), { target: { value: ' AQ.fake-key ' } });
    fireEvent.click(save);
    expect(await screen.findByText('Sẵn sàng chạy')).toBeInTheDocument();
    expect(settingsApi.saveGeminiKey).toHaveBeenCalledWith('AQ.fake-key');
    expect(logicApi.analyze).toHaveBeenCalledTimes(2);
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('lỗi khác hiện thông báo kèm nút thử lại', async () => {
    vi.mocked(logicApi.review).mockRejectedValueOnce(new ApiError('Cấu hình câu trả lời chưa hợp lệ.', 422, ['D1 thiếu câu mẫu']));
    renderPage();
    expect(await screen.findByText('D1 thiếu câu mẫu')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Thử lại' }));
    expect(await screen.findByText('Sẵn sàng chạy')).toBeInTheDocument();
  });
});
