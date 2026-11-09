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

### [BUG-015] Model gemini-2.5-flash bị Google ngừng cho key mới → mọi tính năng AI hỏng — 2026-11-03 — FIXED
- **Phát hiện bởi:** gọi Gemini thật với key mới của người dùng (404 "no longer available to new users").
- **Ảnh hưởng:** tạo câu tự luận bằng AI (có từ Phase 2) và Soát logic đều lỗi với mọi key tạo mới.
- **Cách xử lý:** mặc định dùng bí danh `gemini-flash-latest` (luôn trỏ model Flash mới nhất); `services/gemini_call.generate_json` gặp 404 / quá tải kéo dài (503) thì tự chuyển model dự phòng (`gemini-flash-latest` → `gemini-flash-lite-latest`), lỗi 5xx thử lại tăng dần.
- **Bài học:** Không đặt cứng tên model có số phiên bản; mọi lời gọi AI đi qua một chỗ có thử lại + model dự phòng.

### [BUG-016] Suýt đưa một phần API key thật vào file test — 2026-11-03 — FIXED (chưa từng được commit)
- **Phát hiện bởi:** bộ kiểm tra an toàn chặn lệnh `git add -A`.
- **Cách xử lý:** thay bằng key giả `AQ.FakeKeyOnlyForTests-000`, xoá `.pytest_cache`/`__pycache__` còn giữ chuỗi; quét lại toàn repo chỉ còn `backend/.env` (đã gitignore).
- **Bài học:** Dữ liệu test cho key LUÔN là chuỗi giả. Trước commit: `grep` tiền tố key thật trên toàn repo; add file theo đường dẫn, không `git add -A` khi vừa làm việc với bí mật.

### [BUG-017] Form có câu "Đánh giá" (sao, type 18) → cả 50 phản hồi bị Google từ chối — 2026-11-09 — FIXED
- **Phát hiện bởi:** người dùng chạy form "Interview Questions" (50/50 lỗi 400 rồi "Không tìm thấy nút Tiếp/Gửi").
- **Nguyên nhân gốc (3 lớp):** (1) parser không biết type 18 (Rating) và **bỏ qua âm thầm** câu bắt buộc → Google từ chối mọi phản hồi; (2) trình duyệt dự phòng so chữ nút với "Gửi" dựng sẵn (U+1EED) trong khi Google viết dạng TÁCH DẤU (ư U+01B0 + dấu hỏi U+0309) → không bao giờ khớp; (3) bộ chạy không dừng khi form từ chối liên tiếp.
- **Cách xử lý:** `QuestionType.RATING` (gửi "1".."N" như thang đo; trình duyệt bấm `[role=radio][data-value]` vì link điền sẵn không nhận giá trị Đánh giá); kiểu chưa hỗ trợ ghi vào `unsupported_items`, câu bắt buộc chặn chạy + cảnh báo đỏ ở Cấu hình; `workers/form_page.py` tìm nút theo `jsname` cố định (Gửi `M2UYVd`, Tiếp `OCpkoe`) rồi chữ đã chuẩn hoá NFC; 5 lần thất bại liên tiếp → tự tạm dừng; "Phân tích lại" cùng link cập nhật form cũ (giữ cấu hình) thay vì tạo form mới.
- **Bài học:** Không bao giờ bỏ qua âm thầm dữ liệu không hiểu — phải báo người dùng. So chuỗi tiếng Việt từ trang web luôn chuẩn hoá NFC. Tính năng dự phòng phải có test chạy trình duyệt thật (tests/test_playwright_fallback_browser.py).

### [BUG-018] Trình duyệt dự phòng báo "thành công" sau khi chỉ bấm Tiếp ở trang 1 (form nhiều trang) — 2026-11-09 — FIXED
- **Phát hiện bởi:** điều tra BUG-017 (thử bấm Tiếp trên bản sao form Tiki, KHÔNG bấm Gửi).
- **Nguyên nhân gốc:** URL đổi sang `/formResponse` ngay khi bấm Tiếp; code cũ coi URL đó là đã gửi xong.
- **Cách xử lý:** chỉ coi là đã gửi khi trang không còn ô ẩn `fbzx` (giống BUG-007); sang trang được xác nhận bằng `pageHistory` thay đổi.

### [BUG-019] Chiến dịch 50/50 lỗi vẫn hiện "Hoàn thành" với thanh tiến độ xanh 100% — 2026-11-09 — FIXED
- **Phát hiện bởi:** người dùng (ảnh màn Tổng quan sau BUG-017).
- **Nguyên nhân gốc:** runner đặt COMPLETED khi gửi hết hàng đợi, không xét số thành công; bảng chiến dịch tính tiến độ = thành công + lỗi và tô một màu theo trạng thái.
- **Cách xử lý:** gửi hết mà 0 thành công → trạng thái FAILED kèm lý do; huy hiệu "Không gửi được" (đỏ) / "Hoàn thành · có lỗi" (cam) dựa trên số thành công/lỗi (đúng cả với chiến dịch cũ đã lưu); thanh tiến độ tách xanh/đỏ, ghi "X thành công · Y lỗi / tổng".
- **Bài học:** "Xong" khác "thành công" — mọi chỉ báo tiến độ phải tách số thành công khỏi số lỗi.

### [BUG-020] Khung "Thiết lập chạy" dính khi lăn nhưng cao hơn màn hình → phần dưới bị che, lăn trên khung lại cuộn cả trang — 2026-11-09 — FIXED
- **Phát hiện bởi:** người dùng (màn Cấu hình, màn hình 1424×888).
- **Nguyên nhân gốc:** `lg:sticky` không giới hạn chiều cao; khung cao ~840px + vị trí → đáy khung chỉ thấy khi lăn tới cuối trang; khung không tự cuộn nên lăn chuột trên khung cuộn cả trang.
- **Cách xử lý:** khung dính (Thiết lập chạy, danh sách trang) giới hạn `max-h: 100vh - 3rem`, tự cuộn riêng (`overflow-y-auto`, `overscroll-contain`). Đo bằng trình duyệt thật: lăn ở cột câu hỏi → khung nằm gọn; lăn trên khung → chỉ khung cuộn, trang đứng yên.
- **Bài học:** Phần tử `sticky` luôn phải có giới hạn chiều cao + cuộn riêng.

### [BUG-021] Phát hành v0.1.0 lỗi ở bước build bộ cài: ENOENT `.releaseInfo.releaseNotesFile=release-notes.md` — 2026-11-09 — FIXED
- **Phát hiện bởi:** CI Release (lần đẩy tag v0.1.0 đầu tiên); chưa có Release nào được tạo.
- **Nguyên nhân gốc:** release.yml dùng `-c.releaseInfo.releaseNotesFile=...`; trên runner, electron-builder 26 hiểu `-c` là đường dẫn file cấu hình nên đi mở file tên `.releaseInfo...`.
- **Cách xử lý:** đổi sang dạng đầy đủ `--config.releaseInfo.releaseNotesFile=release-notes.md`; chạy thử lệnh build ở máy (publish never) đạt.
- **Lỗi kèm theo:** lần chạy lại thành công nhưng electron-builder tải file song song khi chưa có Release → tạo 2 Release v0.1.0: bản "Latest" chỉ có .blockmap (người dùng/updater không thấy bộ cài). Đã chép .blockmap sang bản đủ file và xoá bản trùng (người dùng đồng ý). Workflow nay tạo sẵn Release nháp bằng `gh release create --draft`, electron-builder tải vào đó, rồi `gh release edit --draft=false --latest`.
- **Bài học:** Ghi đè cấu hình electron-builder qua CLI luôn dùng `--config.<khoá>`, không dùng `-c.<khoá>`. Luôn tạo Release trước khi electron-builder publish.
