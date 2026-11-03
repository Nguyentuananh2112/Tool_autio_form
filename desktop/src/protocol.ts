import path from 'node:path';
import { pathToFileURL } from 'node:url';

import { net, protocol } from 'electron';

import { rendererDir } from './paths';

/**
 * Giao diện được nạp qua `app://autoform/...` thay vì file:// — trang có origin cố định để backend
 * chỉ cho phép đúng origin này (CORS), không phải origin "null" mà mọi iframe sandbox cũng dùng.
 */
export function registerAppScheme(): void {
  protocol.registerSchemesAsPrivileged([
    { scheme: 'app', privileges: { standard: true, secure: true, supportFetchAPI: true } },
  ]);
}

export function serveRenderer(): void {
  const root = rendererDir();
  protocol.handle('app', (request) => {
    const { pathname } = new URL(request.url);
    const relative = decodeURIComponent(pathname === '/' ? '/index.html' : pathname);
    const target = path.normalize(path.join(root, relative));
    if (!target.startsWith(root + path.sep)) {
      return new Response('Không được phép', { status: 403 }); // chặn ../ ra ngoài thư mục giao diện
    }
    return net.fetch(pathToFileURL(target).toString());
  });
}
