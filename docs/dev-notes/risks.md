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

### [RISK-007] Models đang dùng kiểu riêng của PostgreSQL (`JSONB`, `UUID`) — FIXED 2026-11-02
- Đã đổi sang `JSON`, `Uuid` của SQLAlchemy 2.0; `server_default` dùng `'[]'` và `true()`; bỏ bảng `users` (SPEC-011). Test `tests/test_database.py` kiểm tra giá trị mặc định, JSON và xóa dây chuyền.
- **Bẫy SQLite cần nhớ:**
  - Khóa ngoại mặc định TẮT → phải `PRAGMA foreign_keys=ON` ở mỗi kết nối (`_apply_sqlite_pragmas` trong `core/database.py`), nếu không `ON DELETE CASCADE` âm thầm không chạy.
  - Chỉ cột `INTEGER PRIMARY KEY` mới tự tăng → `BigInteger().with_variant(Integer, "sqlite")` cho `submission_logs.id`.
  - DB `:memory:` cần `StaticPool`, nếu không mỗi kết nối là một DB rỗng riêng.
  - Biến môi trường `DATA_DIR=` rỗng bị Pydantic hiểu thành thư mục hiện tại → không để rỗng trong `.env`.

### [RISK-009] Nhận biết gửi thành công chỉ dựa trên suy đoán — OPEN (ưu tiên cao)
- `http_submitter.classify_response`: 200 + có chuỗi xác nhận ("Câu trả lời của bạn đã được ghi lại"…) **hoặc** trang trả về không chứa `FB_PUBLIC_LOAD_DATA_` → coi là thành công.
- Chưa kiểm chứng với Google thật vì gửi thử sẽ tạo phản hồi thật trong form của người dùng.
- **Cần làm:** người dùng tạo một form thử của riêng mình → gửi 1 phản hồi bằng app → đối chiếu trong tab Câu trả lời; lưu HTML trang xác nhận (ẩn danh) làm fixture test.

### [RISK-010] Trình duyệt dự phòng chưa chạy thật lần nào — OPEN
- Chromium chưa được tải trên máy dev; `playwright_fallback.py` mới có test cho link điền sẵn.
- Chưa xác nhận: link điền sẵn giữ giá trị qua nhiều trang; tên nút "Tiếp"/"Gửi" (giao diện tiếng Việt) và "Next"/"Submit".
- **Cần làm:** cùng form thử của RISK-009, chạy `playwright install chromium` rồi gửi 1 phản hồi qua trình duyệt.

### [RISK-011] `fbzx` dùng chung cho mọi lần gửi — MONITORING
- Token lấy một lần lúc phân tích form. Nếu Google bắt đầu kiểm tra token theo phiên, mọi lần gửi sẽ lỗi → khi đó tải lại form trước mỗi phản hồi.

### [RISK-008] Thay đổi schema giữa các phiên bản phát hành — OPEN
- 40–50 máy đã có file DB cũ; bản cập nhật đổi cột/bảng mà chỉ dùng `create_all` sẽ không thêm cột mới → lỗi khi chạy.
- **Giảm thiểu:** thêm Alembic (hỗ trợ batch mode cho SQLite) trước bản phát hành đầu tiên; app tự chạy migration khi khởi động; sao lưu file DB trước khi migrate.
