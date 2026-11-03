# Bugs

### [BUG-001] Điều kiện kiểm tra `min_checked` sai — 2026-11-02 — FIXED
- **Bối cảnh:** `backend/app/services/spss_generator.py`, `_validate_question` cho Checkbox.
- **Hiện tượng:** Chỉ báo lỗi `min_checked > số lựa chọn` khi `max_checked` có giá trị; nếu `max_checked=None` thì cấu hình sai lọt qua.
- **Nguyên nhân gốc:** Ghép nhầm điều kiện `rule.max_checked is not None` vào kiểm tra `min_checked`.
- **Cách xử lý:** Bỏ điều kiện thừa, chỉ còn `rule and rule.min_checked > len(options)`.
- **Bài học:** Mỗi điều kiện validate chỉ kiểm tra đúng một ràng buộc; viết test cho cả nhánh `None`.

### [BUG-002] Test chập chờn: mất số đếm khi chiến dịch chạy song song với request — 2026-11-02 — FIXED
- **Bối cảnh:** `tests/test_api.py` (start/pause/resume), khoảng 1/4 số lần chạy bị lỗi: `completed_count` 4 thay vì 5, 19 thay vì 20, trạng thái kẹt RUNNING.
- **Nguyên nhân gốc:** test dùng SQLite `:memory:` + `StaticPool` → MỌI phiên dùng chung MỘT kết nối. Phiên của request kết thúc bằng rollback đã xóa luôn phần ghi chưa commit của runner chạy nền.
- **Cách xử lý:** `tests/conftest.py` dùng file SQLite tạm (mỗi phiên một kết nối, giống bản thật, WAL + busy_timeout). Đã chạy lại 15 lần liên tiếp, đều đạt.
- **Bài học:** Không dùng `:memory:` cho test có ghi đồng thời. Khi sửa code chạy nền/đồng thời, chạy cả bộ test ≥ 10 lần trước khi commit.

### [BUG-003] "Event loop is closed": task chiến dịch của test trước còn sống — 2026-11-02 — FIXED
- **Nguyên nhân gốc:** `start_campaign` tạo task nền lưu trong `registry` toàn cục; test kết thúc nhưng task vẫn chạy sang vòng lặp sự kiện đã đóng.
- **Cách xử lý:** `CampaignRegistry.stop_all()` (dùng chung cho lúc tắt app) + `tests/db_helpers.reset_database()` gọi nó trước khi xóa bảng và `engine.dispose()`.

### [BUG-004] `MissingGreenlet` khi trả về chiến dịch vừa tạo — 2026-11-02 — FIXED
- **Nguyên nhân gốc:** `session.get(Campaign, id, options=[selectinload(form)])` trả lại object CÓ SẴN trong session (vừa `add`), bỏ qua `selectinload` → truy cập `campaign.form` kích hoạt lazy-load ngoài ngữ cảnh async.
- **Cách xử lý:** thêm `populate_existing=True` trong `campaign_service.get_campaign`.
- **Bài học:** Với SQLAlchemy async, mọi quan hệ dùng sau khi trả về phải được nạp rõ ràng; object vừa tạo trong cùng session cần `populate_existing`.

### [BUG-005] Giờ trong nhật ký lệch 7 tiếng — 2026-11-02 — FIXED (phát hiện qua ảnh chụp màn hình thật)
- **Hiện tượng:** Nhật ký hiện 16:32 (lấy từ DB) xen với 23:32 (từ WebSocket); biểu đồ nhịp gửi chia sai khung giờ.
- **Nguyên nhân gốc:** SQLite lưu `now()` dạng UTC KHÔNG kèm múi giờ → API trả "2026-11-02T16:32:23" → trình duyệt hiểu là giờ địa phương.
- **Cách xử lý:** kiểu `UtcDateTime` (`schemas/common.py`) gắn UTC cho mọi thời điểm trong DTO; file xuất Excel đổi sang giờ máy (backend chạy ngay trên máy người dùng). Test `test_datetimes_are_utc_aware`.
- **Bài học:** Mọi datetime trả ra API phải có múi giờ. Chỉ test logic là không đủ — phải chạy app thật và nhìn.

### [BUG-006] "Kiểm tra thử Alpha" bị chặn bởi câu không liên quan — 2026-11-02 — FIXED
- **Hiện tượng:** Chạy thử nhóm SPSS báo lỗi vì một câu tự luận khác chưa có câu mẫu.
- **Nguyên nhân gốc:** endpoint preview gọi `validate()` toàn form.
- **Cách xử lý:** `preview_spss_groups` chỉ lập kế hoạch & kiểm tra các nhóm (`_plan_groups`). Test `test_preview_spss_ignores_unrelated_missing_questions`.
- **Bài học:** Kiểm tra theo đúng phạm vi thao tác người dùng đang làm.

### [BUG-007] Gửi thành công có thể bị hiểu nhầm là bị từ chối → gửi trùng — 2026-11-03 — FIXED
- **Phát hiện khi kiểm chứng trên Google thật:** trang xác nhận cũng chứa `FB_PUBLIC_LOAD_DATA_`; app chỉ nhận ra thành công nhờ câu "Câu trả lời của bạn đã được ghi lại".
- **Hậu quả nếu chủ form đổi câu xác nhận:** app coi là VALIDATION → gửi lại bằng trình duyệt dự phòng → form nhận 2 phản hồi giống nhau, chiến dịch đếm sai.
- **Cách xử lý:** `classify_response` dựa vào cấu trúc (có/không ô ẩn `pageHistory`, `fbzx`), không dựa vào câu chữ. Test có trường hợp câu xác nhận tự đặt.
- **Bài học:** Suy đoán về hệ thống bên ngoài phải được kiểm chứng bằng dữ liệu thật trước khi phát hành; ưu tiên dấu hiệu cấu trúc hơn câu chữ (câu chữ đổi theo ngôn ngữ và theo người dùng).

### [BUG-008] Tiêu đề form chứa "];</script>" làm hỏng việc đọc form — 2026-11-03 — FIXED
- **Phát hiện bởi:** unit test chi tiết (tests/unit/test_fb_data_extract.py).
- **Nguyên nhân gốc:** regex không tham lam cắt ngang JSON; nhánh dự phòng `raw_decode` chỉ chạy khi regex KHÔNG khớp.
- **Cách xử lý:** `json.loads` trên kết quả regex lỗi → thử `_raw_decode_after_marker()` trước khi báo lỗi.

### [BUG-009] Ô hộp kiểm ghi cả tên lẫn mã số ("Giao hàng, 3") bị báo lỗi / điền nhầm Mục khác — 2026-11-03 — FIXED
- **Cách xử lý:** mã số đã khớp một lựa chọn luôn được bỏ khỏi phần dư (`answer_coercion._coerce_multi`).

### [BUG-010] Chữ trong "Mục khác" lấy từ Excel bị hạ thường trước khi gửi — 2026-11-03 — FIXED
- **Nguyên nhân gốc:** phần dư tính trên chuỗi đã `casefold()`.
- **Cách xử lý:** gỡ lựa chọn bằng regex không phân biệt hoa thường ngay trên chuỗi gốc (chỉ chuẩn hoá NFC & khoảng trắng).
- **Bài học:** Chuẩn hoá chỉ để SO KHỚP, không dùng chuỗi đã chuẩn hoá làm dữ liệu gửi đi.

### [BUG-011] Tắt app: chiến dịch không dừng kịp vẫn chạy ngầm — 2026-11-03 — FIXED
- **Nguyên nhân gốc:** `CampaignRegistry.stop_all` hết thời hạn chỉ xoá khỏi danh sách, không `cancel()` task.
- **Cách xử lý:** huỷ các task còn lại sau thời hạn và chờ chúng kết thúc.

### [BUG-012] CSV một cột bị tách sai theo một chữ cái — 2026-11-03 — FIXED
- **Nguyên nhân gốc:** `csv.Sniffer` tự do đoán dấu phân cách (VD "Tên" → tách theo "n").
- **Cách xử lý:** `_detect_delimiter()` chỉ đoán trong `,;\t|`, mặc định `,`.

### [BUG-013] File .xlsx hỏng làm lộ lỗi kỹ thuật `BadZipFile` — 2026-11-03 — FIXED
- **Cách xử lý:** bắt `zipfile.BadZipFile` → `ExcelReadError` ("Không đọc được file Excel").

### [BUG-014] Hộp kiểm "tối đa N" không đặt tỷ lệ → mọi phản hồi tích đúng N ô — 2026-11-03 — FIXED
- **Phát hiện bởi:** chạy thật 100 phản hồi vào bản sao form Tiki (câu E4: 11 lựa chọn, tối đa 3 → 100/100 phản hồi đều 3 ô).
- **Nguyên nhân gốc:** mặc định 50% mỗi ô × 11 ô ≈ 5,5 ô được tích, rồi bị cắt về `max_checked` → dữ liệu thiếu tự nhiên.
- **Cách xử lý:** `default_checkbox_probability()` (spss/validation.py): có `max_checked` mà không có weights thì xác suất = (min + max) / 2 / số ô, kẹp trong [5%, 50%]. Cùng công thức ở `distribution_service._targets` (biểu đồ mục tiêu) và frontend `defaultCheckboxPercent` (useQuestionRule.ts).
- **Kèm theo:** biểu đồ mục tiêu trước đây hiện 50% cho ô thiếu khoá khi đã có weights, trong khi bộ sinh dùng 0% → đã thống nhất về 0%.
- **Bài học:** Kiểm tra phân phối của dữ liệu sinh ra trên form thật, không chỉ kiểm tra "hợp lệ".
