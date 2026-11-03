import path from 'node:path';

import { BrowserWindow, shell } from 'electron';

import { APP_ORIGIN } from './backend';

const isExternal = (url: string) => /^https?:\/\//i.test(url);

export function createMainWindow(): BrowserWindow {
  const window = new BrowserWindow({
    width: 1440,
    height: 900,
    minWidth: 1024,
    minHeight: 680,
    show: false,
    title: 'Auto-Form',
    autoHideMenuBar: true,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
    },
  });

  // Link ra ngoài (VD Google AI Studio) mở bằng trình duyệt; không cho trang tự điều hướng đi nơi khác
  window.webContents.setWindowOpenHandler(({ url }) => {
    if (isExternal(url)) void shell.openExternal(url);
    return { action: 'deny' };
  });
  window.webContents.on('will-navigate', (event, url) => {
    if (!url.startsWith(APP_ORIGIN)) {
      event.preventDefault();
      if (isExternal(url)) void shell.openExternal(url);
    }
  });

  window.once('ready-to-show', () => window.show());
  void window.loadURL(`${APP_ORIGIN}/index.html`);
  return window;
}
