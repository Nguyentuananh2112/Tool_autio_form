# Risks

### [RISK-001] Cấu trúc `FB_PUBLIC_LOAD_DATA_` không có tài liệu chính thức — MONITORING
- Google có thể đổi chỉ số mảng bất kỳ lúc nào → parser hỏng đồng loạt cho 40–50 user.
- **Giảm thiểu:** truy cập an toàn `_safe_get`, log cảnh báo khi bỏ qua phần tử; test với HTML form thật đã lưu (fixtures); CI chạy test parser; phát hành bản sửa nhanh qua cơ chế cập nhật.

### [RISK-002] Chỉ số `item[5]` (điều hướng section) và `row[11]` (checkbox grid) — PARTLY RESOLVED 2026-11-02
- `item[5]` của Page Break = điều hướng của trang trước nó: **đã xác nhận** trên form thật (CONF-001).
- `row[11]`: grid trắc nghiệm thường có `row[11] = [0]` (đã thấy trên form thật). Chưa có form thật nào chứa **checkbox grid** để xác nhận giá trị `[1]` — vẫn OPEN.

### [RISK-003] Form yêu cầu thu thập email (`emailAddress`) chưa được xử lý — OPEN
- Form bật "Thu thập email → Người trả lời nhập" sẽ từ chối POST thiếu trường `emailAddress`. Cần phát hiện ở parser (Phase 2) và cấu hình sinh email.

### [RISK-004] Chưa chốt mô hình triển khai cho 40–50 user — RESOLVED 2026-11-02
- Người dùng chọn **ứng dụng desktop**. Xem SPEC-008.

### [RISK-005] Windows SmartScreen chặn file .exe chưa ký số — OPEN
- Bộ cài không có chứng chỉ code-signing sẽ hiện cảnh báo "Windows protected your PC" cho cả 40–50 user, và có thể bị antivirus nghi ngờ (đặc biệt app tự tải bản cập nhật).
- **Giảm thiểu:** hướng dẫn "More info → Run anyway" trong tài liệu; cân nhắc mua chứng chỉ code-signing hoặc dùng Azure Trusted Signing.

### [RISK-006] Dung lượng bộ cài khi kèm Python + Playwright Chromium — OPEN
- PyInstaller backend (~80–150MB) + Chromium (~150MB+) làm bộ cài và mỗi lần cập nhật rất nặng.
- **Giảm thiểu:** không đóng gói Chromium vào bộ cài; tải Chromium lần đầu khi user bật Playwright Fallback; cập nhật khác biệt (differential) nếu framework hỗ trợ.

### [RISK-007] Models đang dùng kiểu riêng của PostgreSQL (`JSONB`, `UUID`) — OPEN
- App desktop dùng SQLite → phải đổi sang kiểu trung lập (`JSON`, `Uuid` của SQLAlchemy 2.0) và bỏ `::jsonb` trong `server_default`. Làm trước Phase 2.
