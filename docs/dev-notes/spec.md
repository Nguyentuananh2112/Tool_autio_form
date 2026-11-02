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
- Theo mô tả Apps Script `PageBreakItem.setGoToPage`. **Đã xác nhận trên form thật 2026-11-02** (CONF-001).

### [SPEC-009] Quan sát từ form thật cần đưa vào UI/UX — 2026-11-02
- Form có thể bắt đầu bằng Page Break → trang 0 không có câu hỏi; `pageHistory` vẫn bắt đầu từ `0`.
- Giới hạn "Chọn tối đa 3" thường chỉ nằm trong **tiêu đề câu hỏi**, không phải validation của Google (meta trống). UI nên tự gợi ý `max_checked` bằng cách dò chuỗi "tối đa N" trong tiêu đề, và cho người dùng sửa.
- Form thật có 7 câu tự luận bắt buộc → nếu chưa có câu trả lời mẫu, generator báo lỗi. UI phải nhắc rõ câu nào còn thiếu và đưa nút "Sinh bằng Gemini" ngay cạnh.
- Câu hỏi có thể chứa tên người thật (VD: "Bạn nhận được form từ ai?") → không đưa HTML/JSON form thật của người dùng vào repo công khai; fixture phải ẩn danh hóa.

### [SPEC-005] Thêm CASCADE cho `campaigns.user_id` và `submission_logs.campaign_id` — 2026-11-02
- Spec chỉ ghi FK; thêm `ondelete=CASCADE` để xóa user/campaign không bị chặn.

### [SPEC-006] Chặn SSRF ở parser — 2026-11-02
- Chỉ nhận host `docs.google.com/forms` và `forms.gle`; từ chối link `/edit`.

### [SPEC-008] Mô hình triển khai: ỨNG DỤNG DESKTOP — 2026-11-02 — CHỐT
- Người dùng chọn: mỗi user cài app trên máy mình; app kiểm tra GitHub Release, báo "Có bản mới" và nút "Cập nhật".
- **Lệch spec có chủ đích:** PostgreSQL + Redis → SQLite nhúng (async qua `aiosqlite`) + trạng thái chiến dịch trong bộ nhớ của tiến trình backend. Backend FastAPI chạy local `127.0.0.1` như một tiến trình con (sidecar) đóng gói bằng PyInstaller; frontend React giữ nguyên.
- Còn phải chốt: khung desktop (Electron + electron-updater hay Tauri + updater plugin). Đăng nhập: đã bỏ (SPEC-011). Gemini key: kho bảo mật Windows (SPEC-011).
- Ưu điểm đã cân nhắc: mỗi máy gửi form từ IP riêng, không tốn VPS.

### [SPEC-010] Bản thiết kế UI/UX v1 — 2026-11-02 — ĐÃ DUYỆT
- 8 artboard (6 màn hình + hộp thoại SPSS + sidebar + hệ thống thiết kế). Chi tiết & cây component: `docs/ui-ux/README.md`.
- Người dùng duyệt ngày 2026-11-02. Màn hình riêng cho tab Excel/CSV chưa có — thiết kế bổ sung khi làm `excel_mapper` (Phase 2) và xin duyệt riêng.

### [SPEC-011] Bỏ đăng nhập & tài khoản — 2026-11-02 — CHỐT
- Người dùng xác nhận: app một người dùng/máy, **không có màn hình đăng nhập**.
- Lệch spec: bỏ bảng `users`, cột `user_id` ở `forms`/`campaigns`, `auth_router`, `security.py` (JWT/bcrypt), `AuthPage.tsx`, các endpoint `/api/v1/auth/*`.
- Gemini API key chuyển từ cột `users.gemini_api_key` sang kho bảo mật của Windows (thư viện `keyring`), cấu hình ở màn hình Cài đặt.
- Backend chỉ nghe trên `127.0.0.1` nên không cần xác thực tài khoản; sẽ dùng token ngẫu nhiên mỗi lần khởi động giữa app desktop và backend để chặn trang web lạ gọi vào cổng local (thiết kế ở Phase 3).

### [SPEC-007] Yêu cầu bổ sung của người dùng — 2026-11-02
- UI/UX thiết kế trước; phát hành qua GitHub + Actions; thông báo & nút cập nhật; cấm God Component; duy trì dev-notes. Chi tiết trong `CLAUDE.md`.
