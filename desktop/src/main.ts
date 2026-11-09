import { writeFileSync } from 'node:fs';
import path from 'node:path';

import { app, BrowserWindow, dialog, ipcMain, shell } from 'electron';
import log from 'electron-log/main';

import { BackendProcess } from './backend';
import { registerAppScheme, serveRenderer } from './protocol';
import { setupUpdater } from './updater';
import { createMainWindow } from './window';

log.initialize();
registerAppScheme();

const backend = new BackendProcess();
let mainWindow: BrowserWindow | null = null;
let quitting = false;

// Windows chỉ hiện thông báo hệ thống (màn 13) khi app có AppUserModelID — trùng appId của electron-builder
app.setAppUserModelId('com.autoform.desktop');

if (!app.requestSingleInstanceLock()) {
  app.quit(); // đã mở một cửa sổ khác → đưa cửa sổ đó lên thay vì chạy 2 backend
} else {
  app.on('second-instance', () => {
    if (mainWindow) {
      if (mainWindow.isMinimized()) mainWindow.restore();
      mainWindow.focus();
    }
  });
  app.whenReady().then(start).catch(fail);
}

async function start(): Promise<void> {
  serveRenderer();
  const info = await backend.start();
  ipcMain.on('config:get', (event) => {
    event.returnValue = { apiBase: info.apiBase, wsBase: info.wsBase, token: info.token, version: app.getVersion() };
  });
  ipcMain.handle('shell:open-path', (_event, target: string) => shell.openPath(target));
  // Bấm vào thông báo "Đã gửi xong" → đưa cửa sổ app lên trước (kể cả đang thu nhỏ)
  ipcMain.handle('window:focus', () => {
    if (!mainWindow) return;
    if (mainWindow.isMinimized()) mainWindow.restore();
    mainWindow.show();
    mainWindow.focus();
  });
  setupUpdater(() => mainWindow, backend);
  mainWindow = createMainWindow();
  mainWindow.on('closed', () => (mainWindow = null));
  captureForSmokeTest(mainWindow);
}

function fail(error: unknown): void {
  log.error('Không khởi động được app', error);
  dialog.showErrorBox(
    'Auto-Form không khởi động được',
    `${error instanceof Error ? error.message : String(error)}\n\nNhật ký chi tiết: ${log.transports.file.getFile().path}`,
  );
  void backend.stop().finally(() => app.exit(1));
}

/** Kiểm thử tự động: AUTOFORM_SMOKE_SCREENSHOT=<file.png> → chụp màn hình rồi thoát. */
function captureForSmokeTest(window: BrowserWindow): void {
  const target = process.env.AUTOFORM_SMOKE_SCREENSHOT;
  if (!target) return;
  window.webContents.once('did-finish-load', () => {
    setTimeout(async () => {
      const image = await window.webContents.capturePage();
      writeFileSync(path.resolve(target), image.toPNG());
      log.info(`Đã chụp màn hình kiểm thử: ${target}`);
      app.quit();
    }, 5000);
  });
}

// Đóng app: tắt êm backend trước (chiến dịch đang chạy chuyển sang Tạm dừng)
app.on('before-quit', (event) => {
  if (quitting) return;
  event.preventDefault();
  quitting = true;
  void backend.stop().finally(() => app.quit());
});

app.on('window-all-closed', () => app.quit());
