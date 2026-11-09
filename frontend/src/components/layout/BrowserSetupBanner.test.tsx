import { render, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { settingsApi } from '@/api/endpoints';
import { shouldAutoInstall } from '@/hooks/useBrowserInstall';
import type { BrowserStatus } from '@/types/settings';

import { BrowserSetupBanner } from './BrowserSetupBanner';

const missing: BrowserStatus = { installed: false, installing: false, percent: null, detail: null, error: null };

describe('shouldAutoInstall', () => {
  it('tự tải khi chưa có, chưa tải, chưa lỗi và chưa thử trong phiên', () => {
    expect(shouldAutoInstall(missing, false)).toBe(true);
  });
  it('không tải lại khi đã có, đang tải, đã lỗi hoặc đã thử', () => {
    expect(shouldAutoInstall(null, false)).toBe(false);
    expect(shouldAutoInstall({ ...missing, installed: true }, false)).toBe(false);
    expect(shouldAutoInstall({ ...missing, installing: true }, false)).toBe(false);
    expect(shouldAutoInstall({ ...missing, error: 'mất mạng' }, false)).toBe(false);
    expect(shouldAutoInstall(missing, true)).toBe(false);
  });
});

describe('BrowserSetupBanner', () => {
  afterEach(() => vi.restoreAllMocks());

  it('lần đầu mở app: tự gọi tải và hiện tiến độ', async () => {
    vi.spyOn(settingsApi, 'browserStatus').mockResolvedValue(missing);
    const install = vi.spyOn(settingsApi, 'installBrowser').mockResolvedValue({ ...missing, installing: true, percent: 12, detail: 'Đã tải 12% / 98 MiB' });
    render(<BrowserSetupBanner />);
    expect(await screen.findByText('Đang chuẩn bị cho lần dùng đầu tiên')).toBeInTheDocument();
    expect(install).toHaveBeenCalledTimes(1);
  });

  it('lần sau mở app (đã có trình duyệt): không hiện gì, không tải', async () => {
    const statusCall = vi.spyOn(settingsApi, 'browserStatus').mockResolvedValue({ ...missing, installed: true });
    const install = vi.spyOn(settingsApi, 'installBrowser');
    const { container } = render(<BrowserSetupBanner />);
    await waitFor(() => expect(statusCall).toHaveBeenCalled());
    expect(container).toBeEmptyDOMElement();
    expect(install).not.toHaveBeenCalled();
  });

  it('tải lỗi: báo lỗi kèm nút Thử lại, không tự tải lặp', async () => {
    vi.spyOn(settingsApi, 'browserStatus').mockResolvedValue({ ...missing, error: 'Tải trình duyệt thất bại.' });
    const install = vi.spyOn(settingsApi, 'installBrowser');
    render(<BrowserSetupBanner />);
    expect(await screen.findByRole('button', { name: 'Thử lại' })).toBeInTheDocument();
    expect(install).not.toHaveBeenCalled();
  });
});
