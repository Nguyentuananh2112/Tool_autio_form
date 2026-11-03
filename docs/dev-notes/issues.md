# Issues (môi trường / công cụ / vận hành)

### [ISS-001] winget lỗi mã 5, không có thông báo — 2026-11-02 — WORKAROUND
- **Hiện tượng:** `winget search/install` thoát với exit code 5, không in lỗi.
- **Cách xử lý:** Tải bộ cài chính thức từ python.org (kiểm tra chữ ký Authenticode của Python Software Foundation) và cài `/quiet InstallAllUsers=0 PrependPath=1`.
- **Bài học:** Trên máy này không dựa vào winget; cài phần mềm bằng installer chính thức + xác minh chữ ký.

### [ISS-002] Môi trường Python của dự án — 2026-11-02 — INFO
- Python 3.12.10 tại `%LOCALAPPDATA%\Programs\Python\Python312`.
- Terminal/VS Code đã mở trước khi cài chưa nhận PATH mới → phải mở lại.
- Môi trường ảo dự án: `backend/.venv`. Luôn gọi `backend\.venv\Scripts\python.exe`.
- In tiếng Việt từ Python trong Git Bash cần `PYTHONIOENCODING=utf-8`. Lưu ý: cờ `python -I` (isolated) **bỏ qua** biến môi trường này → dùng `-X utf8` thay thế khi cần `-I`.

### [ISS-003] Link `/edit` của Google Form trả về 401 — 2026-11-02 — OPEN
- **Hiện tượng:** Người dùng gửi link `docs.google.com/forms/d/<id>/edit`. Thử đổi sang `/d/<id>/viewform` → HTTP 401 (cần đăng nhập).
- **Nguyên nhân:** Link edit dùng ID nội bộ của chủ form, khác ID công khai `/d/e/<public_id>/viewform`; hoặc form chưa nhận phản hồi công khai.
- **Cách xử lý:** Parser từ chối link `/edit`. UI (Phase 4) phải hướng dẫn rõ: nút "Gửi" → biểu tượng liên kết → sao chép link.

### [ISS-005] Node.js 25 che mất `localStorage` của jsdom trong test — 2026-11-02 — WORKAROUND
- **Hiện tượng:** Vitest báo `localStorage.setItem is not a function`.
- **Nguyên nhân:** Node ≥ 25 có `localStorage` toàn cục (thiếu phương thức khi không bật `--localstorage-file`), đè lên bản của jsdom.
- **Cách xử lý:** `src/test/setup.ts` thay bằng `MemoryStorage` khi thiếu `setItem`. Không ảnh hưởng app thật (trình duyệt/webview có localStorage chuẩn).

### [ISS-006] Vite dev chỉ nghe `localhost` (IPv6) — 2026-11-02 — INFO
- `curl http://127.0.0.1:5173` thất bại; dùng `http://localhost:5173`. Proxy `/api`, `/ws` → `127.0.0.1:8765`.
- Kiểm tra giao diện thật: chạy backend (`DATA_DIR` tạm) + `npx vite`, rồi dùng Playwright (Chromium đã cài trong `backend/.venv`) để chụp màn hình.

### [ISS-007] Electron chạy như Node khi mở từ VS Code — 2026-11-03 — WORKAROUND
- **Hiện tượng:** `npx electron .` báo `Cannot read properties of undefined (reading 'registerSchemesAsPrivileged')`.
- **Nguyên nhân:** terminal của VS Code đặt `ELECTRON_RUN_AS_NODE=1` cho tiến trình con.
- **Cách xử lý:** `env -u ELECTRON_RUN_AS_NODE npx electron .` (hoặc đặt biến rỗng). Người dùng mở app bình thường không bị.

### [ISS-004] Heredoc dài chứa ký tự đặc biệt làm Bash tool lỗi parse — 2026-11-02 — WORKAROUND
- **Hiện tượng:** Một lệnh Bash tạo nhiều file bằng heredoc báo `unexpected EOF while looking for matching '`, không file nào được tạo.
- **Bài học:** Tạo/ghi file nội dung dài bằng công cụ Write, không dồn nhiều heredoc vào một lệnh shell.
