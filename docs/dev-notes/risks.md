# Risks

### [RISK-001] Cấu trúc `FB_PUBLIC_LOAD_DATA_` không có tài liệu chính thức — MONITORING
- Google có thể đổi chỉ số mảng bất kỳ lúc nào → parser hỏng đồng loạt cho 40–50 user.
- **Giảm thiểu:** truy cập an toàn `_safe_get`, log cảnh báo khi bỏ qua phần tử; test với HTML form thật đã lưu (fixtures); CI chạy test parser; phát hành bản sửa nhanh qua cơ chế cập nhật.

### [RISK-002] Chỉ số `item[5]` (điều hướng section) và `row[11]` (checkbox grid) chưa xác nhận — OPEN
- Xem CONF-001. Cần đối chiếu với form thật.

### [RISK-003] Form yêu cầu thu thập email (`emailAddress`) chưa được xử lý — OPEN
- Form bật "Thu thập email → Người trả lời nhập" sẽ từ chối POST thiếu trường `emailAddress`. Cần phát hiện ở parser (Phase 2) và cấu hình sinh email.

### [RISK-004] Chưa chốt mô hình triển khai cho 40–50 user — OPEN
- Web tập trung (1 server, CD tự deploy) vs ứng dụng desktop (mỗi máy tự cập nhật từ GitHub Release) ảnh hưởng toàn bộ: cơ chế auto-update, DB (PostgreSQL/Redis chạy ở đâu), bảo mật API key, thiết kế UI/UX. Phải chốt trước khi thiết kế UI/UX.
