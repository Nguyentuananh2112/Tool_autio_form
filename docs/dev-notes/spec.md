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

### [SPEC-012] Phase 2: KHÔNG lách cơ chế chặn của Google — 2026-11-02 — CHỐT (người dùng đồng ý)
- Bỏ khỏi spec Mục 5.4.C: xoay User-Agent ngẫu nhiên, xoay proxy khi gặp 429/403, chuyển sang Playwright để vượt 429/403.
- Thay bằng `workers/rate_guard.py`: bị 429/403 → nhân đôi khoảng nghỉ (tối đa ×16), chờ theo `Retry-After`; bị 3 lần liên tiếp → **tự tạm dừng** chiến dịch với lý do rõ ràng; người dùng bấm Tiếp tục thì chạy lại với nhịp chậm.
- User-Agent cố định, trung thực (`HTTP_USER_AGENT`). Proxy: tối đa **một** proxy cố định cho mạng của người dùng (`proxy_list[0]`), không xoay vòng.
- Playwright chỉ dùng khi lỗi **dữ liệu** (400 / Google trả lại form), qua link điền sẵn `viewform?usp=pp_url&entry.X=...` rồi bấm Tiếp/Gửi.
- Đã sửa bản thiết kế (Workspace: ô proxy đơn + nhãn trình duyệt; Campaign: nhật ký mẫu) cho khớp.

### [SPEC-013] Gửi payload bằng `content=urlencode(list_of_tuples)` — 2026-11-02
- Spec ghi truyền `list[tuple]` vào httpx; httpx 0.28 chỉ nhận `data` là dict. Dùng `urlencode` để giữ đúng thứ tự và khóa lặp của Checkbox, header `application/x-www-form-urlencoded`.

### [SPEC-014] Tách module lớn (chống God Module) — 2026-11-02
- `spss_generator.py` (946 dòng) → package `services/spss/` 11 file; `spss_generator.py` chỉ còn re-export API (giữ tên file như spec).
- `form_parser.py` (460 dòng) → `form_errors.py`, `form_url.py`, `fb_data_parser.py` + `form_parser.py` (tải & ghép).
- Excel: `excel_reader.py` (đọc file), `answer_coercion.py` (ô → câu trả lời), `excel_mapper.py` (ghép cột, chuyển dòng).
- Worker: `scheduler`, `rate_guard`, `submission_types`, `campaign_control` (thay Redis), `campaign_loader`, `campaign_runner`, `http_submitter`, `playwright_fallback`.
- **Quy tắc:** chạy `wc -l app/*/*.py app/*/*/*.py` trước mỗi commit; file > 400 dòng phải tách.

### [SPEC-015] Excel: dữ liệu đã mã hóa SPSS & ô Checkbox — 2026-11-02
- Số nguyên trong ô của câu thang đo/trắc nghiệm được hiểu là thứ tự đáp án (hoặc giá trị thật nếu thang là số liên tiếp, VD 1–10).
- Ô Checkbox được tách bằng cách dò lựa chọn dài nhất trước (lựa chọn có thể chứa dấu phẩy); phần dư → "Mục khác" nếu câu có, ngược lại là lỗi dòng.
- Giá trị không khớp lựa chọn → "Mục khác" (cảnh báo) hoặc lỗi dòng. Dòng lỗi bị bỏ qua và liệt kê cho người dùng.
- Màn hình tab Excel (artboard 8) **đã duyệt** 2026-11-02.

### [SPEC-016] Phase 3: API local cho app desktop — 2026-11-02
- **Không có `/auth/*`** (SPEC-011). Thay bằng `APP_TOKEN`: vỏ desktop sinh mã ngẫu nhiên mỗi lần khởi động, truyền qua biến môi trường; client gửi header `X-App-Token` (WebSocket: `?token=`). Bản phát hành thiếu token → từ chối tất cả (fail closed). `/api/v1/health` không cần token.
- Thêm so với spec: `GET/DELETE /forms`, `/forms/{id}/excel-convert` (file + ghép cột → bản ghi lưu vào chiến dịch), `/campaigns/{id}/stop`, `/campaigns/{id}/logs`, `/campaigns/trial-submit` (nút "Gửi thử 1 phản hồi"), `/settings` + `/settings/gemini-key`.
- `/export-csv` của spec → `/campaigns/{id}/export?format=xlsx|csv`; Excel có 2 trang "Dữ liệu" và "SPSS (mã số)".
- Lỗi trả về thống nhất `{"detail": {"message", "errors"}}` bằng tiếng Việt (`api/errors.py`).
- WebSocket gửi `SNAPSHOT` ngay khi kết nối, rồi `SUBMISSION_UPDATE` / `STATUS_CHANGE` / `RATE_LIMITED`, `PING` mỗi 25 giây.
- Khởi động: chiến dịch còn RUNNING (app tắt đột ngột) → PAUSED. Tắt app: dừng an toàn mọi chiến dịch.
- Chạy backend: `python -m app` (cổng mặc định 8765, chỉ 127.0.0.1).

### [SPEC-017] Chế độ tập dùng (form mẫu, không gửi ra ngoài) — 2026-11-02 — CHỐT
- Người dùng chọn: người mới tập mọi tính năng mà KHÔNG gửi gì lên Google, không cần link thật.
- `POST /api/v1/forms/demo` tạo/dùng lại form mẫu (`forms.is_demo = true`, địa chỉ `*.invalid`, có rẽ nhánh, hộp kiểm + Mục khác, lưới Likert, thang 1–10, tự luận).
- Chiến dịch trên form mẫu: runner LUÔN dùng `SimulatedSubmitter` (engine `SIMULATED`), bỏ qua `http_factory` và trình duyệt dự phòng. `trial-submit` có `dry_run` để xem trước dữ liệu mà không gửi; form mẫu luôn mô phỏng.
- Test `test_practice_mode.py` dùng bộ gửi "nổ" nếu bị gọi để chứng minh không có gì đi ra ngoài.
- UI (Phase 4): nút "Thử với form mẫu" ở Tổng quan và cuối tour; nhãn "Chế độ tập dùng" luôn hiện khi đang ở form mẫu.
- Việc kiểm chứng gửi thật (RISK-009/010) vẫn cần một form thử riêng của người dùng — để sau.

### [SPEC-007] Yêu cầu bổ sung của người dùng — 2026-11-02
- UI/UX thiết kế trước; phát hành qua GitHub + Actions; thông báo & nút cập nhật; cấm God Component; duy trì dev-notes. Chi tiết trong `CLAUDE.md`.
