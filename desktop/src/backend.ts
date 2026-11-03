import { type ChildProcess, spawn } from 'node:child_process';
import { randomBytes } from 'node:crypto';
import net from 'node:net';

import { app } from 'electron';
import log from 'electron-log/main';

import { backendCommand } from './paths';

export const APP_ORIGIN = 'app://autoform';
const START_TIMEOUT_MS = 60_000;
const STOP_TIMEOUT_MS = 15_000;

export interface BackendInfo {
  port: number;
  token: string;
  apiBase: string;
  wsBase: string;
}

function freePort(): Promise<number> {
  return new Promise((resolve, reject) => {
    const server = net.createServer();
    server.once('error', reject);
    server.listen(0, '127.0.0.1', () => {
      const address = server.address();
      server.close(() => (typeof address === 'object' && address ? resolve(address.port) : reject(new Error('Không lấy được cổng trống'))));
    });
  });
}

const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

/** Tiến trình backend FastAPI chạy kèm app: cổng ngẫu nhiên + mã ngẫu nhiên mỗi lần mở (dev-notes SPEC-011). */
export class BackendProcess {
  private child: ChildProcess | null = null;
  private exited = false;
  info: BackendInfo | null = null;

  async start(): Promise<BackendInfo> {
    const port = await freePort();
    const token = randomBytes(32).toString('base64url');
    const { command, args, cwd } = backendCommand();
    log.info(`Khởi động backend: ${command} (cổng ${port})`);
    this.child = spawn(command, args, {
      cwd,
      windowsHide: true,
      env: {
        ...process.env,
        PORT: String(port),
        APP_TOKEN: token,
        ENVIRONMENT: 'production',
        APP_VERSION: app.getVersion(),
        CORS_ORIGINS: APP_ORIGIN,
        PYTHONIOENCODING: 'utf-8',
      },
    });
    this.child.stdout?.on('data', (chunk: Buffer) => log.info(`[backend] ${chunk.toString().trimEnd()}`));
    this.child.stderr?.on('data', (chunk: Buffer) => log.info(`[backend] ${chunk.toString().trimEnd()}`));
    this.child.once('exit', (code) => {
      this.exited = true;
      log.warn(`Backend đã thoát (mã ${code})`);
    });

    const apiBase = `http://127.0.0.1:${port}/api/v1`;
    await this.waitHealthy(apiBase);
    this.info = { port, token, apiBase, wsBase: `ws://127.0.0.1:${port}` };
    return this.info;
  }

  private async waitHealthy(apiBase: string): Promise<void> {
    const deadline = Date.now() + START_TIMEOUT_MS;
    while (Date.now() < deadline) {
      if (this.exited) throw new Error('Backend thoát ngay khi khởi động.');
      try {
        const response = await fetch(`${apiBase}/health`);
        if (response.ok) return;
      } catch {
        // chưa sẵn sàng
      }
      await sleep(300);
    }
    throw new Error('Backend không phản hồi sau 60 giây.');
  }

  /** Tắt êm (chiến dịch đang chạy được tạm dừng an toàn), quá hạn thì buộc dừng. */
  async stop(): Promise<void> {
    const child = this.child;
    if (!child || this.exited) return;
    if (this.info) {
      try {
        await fetch(`${this.info.apiBase}/system/shutdown`, { method: 'POST', headers: { 'X-App-Token': this.info.token } });
      } catch (error) {
        log.warn('Không gửi được lệnh tắt êm', error);
      }
    }
    const deadline = Date.now() + STOP_TIMEOUT_MS;
    while (!this.exited && Date.now() < deadline) await sleep(200);
    if (!this.exited) {
      log.warn('Backend không tự thoát, buộc dừng.');
      child.kill();
    }
  }
}
