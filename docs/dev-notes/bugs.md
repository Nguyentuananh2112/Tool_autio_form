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
