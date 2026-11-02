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
