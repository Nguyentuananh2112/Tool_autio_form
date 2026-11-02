# Spec decisions (quyết định thiết kế & điểm lệch so với SPECIFICATION.md)

### [SPEC-001] Grid tách mỗi hàng thành một câu hỏi riêng — 2026-11-02
- Mỗi hàng có `entry_id` riêng → mỗi hàng là một `ParsedQuestion` (type 7, có `grid_item_id`, `row_label`). Cho phép đưa hàng của ma trận Likert vào nhóm SPSS và lưu `question_rules` theo từng hàng.

### [SPEC-002] Hiệu chỉnh tham số ẩn cho nhóm SPSS — 2026-11-02
- Làm tròn + cắt biên MVN như spec kéo mean về giữa thang và giảm alpha. Đã thêm `calibrate_latent_moments` (giải chính xác bằng CDF chuẩn + brentq) và `calibrate_latent_correlation` (chia đôi với Common Random Numbers). Tắt bằng `calibrate=False`.
- Nhóm nhận `r` hoặc `alpha_target`; có cả hai thì ưu tiên `r`.
- Hỗ trợ `reversed_entries` (biến đảo chiều).

### [SPEC-003] Hỗ trợ thêm Date (9) / Time (10) — 2026-11-02
- Cần để form có câu ngày/giờ bắt buộc vẫn nộp được. Payload: `entry.X_year/_month/_day`, `entry.X_hour/_minute`.

### [SPEC-004] `item[5]` của Page Break = điều hướng của trang ĐỨNG TRƯỚC — 2026-11-02
- Theo mô tả Apps Script `PageBreakItem.setGoToPage`. Chưa xác nhận trên form thật (RISK-002).

### [SPEC-005] Thêm CASCADE cho `campaigns.user_id` và `submission_logs.campaign_id` — 2026-11-02
- Spec chỉ ghi FK; thêm `ondelete=CASCADE` để xóa user/campaign không bị chặn.

### [SPEC-006] Chặn SSRF ở parser — 2026-11-02
- Chỉ nhận host `docs.google.com/forms` và `forms.gle`; từ chối link `/edit`.

### [SPEC-008] Mô hình triển khai: ỨNG DỤNG DESKTOP — 2026-11-02 — CHỐT
- Người dùng chọn: mỗi user cài app trên máy mình; app kiểm tra GitHub Release, báo "Có bản mới" và nút "Cập nhật".
- **Lệch spec có chủ đích:** PostgreSQL + Redis → SQLite nhúng (async qua `aiosqlite`) + trạng thái chiến dịch trong bộ nhớ của tiến trình backend. Backend FastAPI chạy local `127.0.0.1` như một tiến trình con (sidecar) đóng gói bằng PyInstaller; frontend React giữ nguyên.
- Còn phải chốt khi thiết kế: khung desktop (Electron + electron-updater hay Tauri + updater plugin), có giữ đăng nhập tài khoản không (app một người dùng/máy), nơi lưu Gemini API key (bộ nhớ an toàn của hệ điều hành).
- Ưu điểm đã cân nhắc: mỗi máy gửi form từ IP riêng, không tốn VPS.

### [SPEC-007] Yêu cầu bổ sung của người dùng — 2026-11-02
- UI/UX thiết kế trước; phát hành qua GitHub + Actions; thông báo & nút cập nhật; cấm God Component; duy trì dev-notes. Chi tiết trong `CLAUDE.md`.
