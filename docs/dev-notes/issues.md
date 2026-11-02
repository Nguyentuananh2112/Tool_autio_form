# Issues (môi trường / công cụ / vận hành)

### [ISS-001] winget lỗi mã 5, không có thông báo — 2026-11-02 — WORKAROUND
- **Hiện tượng:** `winget search/install` thoát với exit code 5, không in lỗi.
- **Cách xử lý:** Tải bộ cài chính thức từ python.org (kiểm tra chữ ký Authenticode của Python Software Foundation) và cài `/quiet InstallAllUsers=0 PrependPath=1`.
- **Bài học:** Trên máy này không dựa vào winget; cài phần mềm bằng installer chính thức + xác minh chữ ký.

### [ISS-002] Môi trường Python của dự án — 2026-11-02 — INFO
- Python 3.12.10 tại `%LOCALAPPDATA%\Programs\Python\Python312`.
- Terminal/VS Code đã mở trước khi cài chưa nhận PATH mới → phải mở lại.
- Môi trường ảo dự án: `backend/.venv`. Luôn gọi `backend\.venv\Scripts\python.exe`.
- In tiếng Việt từ Python trong Git Bash cần `PYTHONIOENCODING=utf-8`.

### [ISS-003] Link `/edit` của Google Form trả về 401 — 2026-11-02 — OPEN
- **Hiện tượng:** Người dùng gửi link `docs.google.com/forms/d/<id>/edit`. Thử đổi sang `/d/<id>/viewform` → HTTP 401 (cần đăng nhập).
- **Nguyên nhân:** Link edit dùng ID nội bộ của chủ form, khác ID công khai `/d/e/<public_id>/viewform`; hoặc form chưa nhận phản hồi công khai.
- **Cách xử lý:** Parser từ chối link `/edit`. UI (Phase 4) phải hướng dẫn rõ: nút "Gửi" → biểu tượng liên kết → sao chép link.

### [ISS-004] Heredoc dài chứa ký tự đặc biệt làm Bash tool lỗi parse — 2026-11-02 — WORKAROUND
- **Hiện tượng:** Một lệnh Bash tạo nhiều file bằng heredoc báo `unexpected EOF while looking for matching '`, không file nào được tạo.
- **Bài học:** Tạo/ghi file nội dung dài bằng công cụ Write, không dồn nhiều heredoc vào một lệnh shell.
