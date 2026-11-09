import { contextBridge, ipcRenderer, type IpcRendererEvent } from 'electron';

/**
 * Cầu nối an toàn giữa giao diện và vỏ desktop (contextIsolation + sandbox).
 * Khớp `window.__AUTOFORM_CONFIG__` và `window.autoformDesktop` ở frontend (src/types/settings.ts).
 */
const config = ipcRenderer.sendSync('config:get') as { apiBase: string; wsBase: string; token: string; version: string };

contextBridge.exposeInMainWorld('__AUTOFORM_CONFIG__', {
  apiBase: config.apiBase,
  wsBase: config.wsBase,
  token: config.token,
});

contextBridge.exposeInMainWorld('autoformDesktop', {
  version: config.version,
  openPath: (target: string) => ipcRenderer.invoke('shell:open-path', target),
  focusWindow: () => ipcRenderer.invoke('window:focus'),
  updater: {
    check: () => ipcRenderer.invoke('updater:check'),
    download: async (onProgress: (percent: number) => void) => {
      const listener = (_event: IpcRendererEvent, percent: number) => onProgress(percent);
      ipcRenderer.on('updater:progress', listener);
      try {
        await ipcRenderer.invoke('updater:download');
        onProgress(100);
      } finally {
        ipcRenderer.removeListener('updater:progress', listener);
      }
    },
    installAndRestart: () => ipcRenderer.invoke('updater:install-now'),
    installOnQuit: () => ipcRenderer.invoke('updater:install-on-quit'),
  },
});
