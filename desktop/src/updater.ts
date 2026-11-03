import { app, type BrowserWindow, ipcMain } from 'electron';
import log from 'electron-log/main';
import { autoUpdater, type UpdateInfo as ElectronUpdateInfo } from 'electron-updater';

import type { BackendProcess } from './backend';

/** Khớp kiểu UpdateInfo ở frontend (src/types/settings.ts). */
interface UpdateInfo {
  version: string;
  releaseDate: string;
  notes: string[];
  sizeBytes: number;
}

function releaseNotes(info: ElectronUpdateInfo): string[] {
  const raw = Array.isArray(info.releaseNotes)
    ? info.releaseNotes.map((n) => n.note ?? '').join('\n')
    : info.releaseNotes ?? '';
  const lines = raw
    .replace(/<\/(p|li|h\d)>/gi, '\n')
    .replace(/<[^>]+>/g, '')
    .split('\n')
    .map((line) => line.replace(/^[\s*#-]+/, '').trim())
    .filter(Boolean);
  return lines.length > 0 ? lines.slice(0, 12) : ['Có cải tiến và sửa lỗi mới.'];
}

const toInfo = (info: ElectronUpdateInfo): UpdateInfo => ({
  version: info.version,
  releaseDate: info.releaseDate,
  notes: releaseNotes(info),
  sizeBytes: info.files?.[0]?.size ?? 0,
});

/** Cập nhật qua GitHub Releases (latest.yml). Giao diện quyết định lúc tải & lúc cài (artboard 5). */
export function setupUpdater(getWindow: () => BrowserWindow | null, backend: BackendProcess): void {
  autoUpdater.logger = log;
  autoUpdater.autoDownload = false;
  autoUpdater.autoInstallOnAppQuit = false;

  autoUpdater.on('download-progress', (progress) => {
    getWindow()?.webContents.send('updater:progress', Math.round(progress.percent));
  });

  ipcMain.handle('updater:check', async (): Promise<UpdateInfo | null> => {
    if (!app.isPackaged) return null; // bản phát triển không tự cập nhật
    const result = await autoUpdater.checkForUpdates();
    return result?.isUpdateAvailable ? toInfo(result.updateInfo) : null;
  });

  ipcMain.handle('updater:download', async () => {
    await autoUpdater.downloadUpdate();
  });

  ipcMain.handle('updater:install-now', async () => {
    await backend.stop(); // tạm dừng an toàn chiến dịch trước khi cài
    autoUpdater.quitAndInstall(true, true);
  });

  ipcMain.handle('updater:install-on-quit', () => {
    autoUpdater.autoInstallOnAppQuit = true;
  });
}
