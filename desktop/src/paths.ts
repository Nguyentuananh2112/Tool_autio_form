import path from 'node:path';

import { app } from 'electron';

/** Vị trí giao diện & backend: bản cài nằm trong resources/, khi phát triển lấy thẳng từ repo. */
const REPO_ROOT = path.resolve(__dirname, '..', '..');

export function rendererDir(): string {
  return app.isPackaged ? path.join(process.resourcesPath, 'renderer') : path.join(REPO_ROOT, 'frontend', 'dist');
}

export interface BackendCommand {
  command: string;
  args: string[];
  cwd: string;
}

export function backendCommand(): BackendCommand {
  if (app.isPackaged) {
    const dir = path.join(process.resourcesPath, 'backend');
    return { command: path.join(dir, 'autoform-backend.exe'), args: [], cwd: dir };
  }
  const backend = path.join(REPO_ROOT, 'backend');
  return { command: path.join(backend, '.venv', 'Scripts', 'python.exe'), args: ['-m', 'app'], cwd: backend };
}
