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
- Khung desktop: Electron + electron-updater (SPEC-019). Đăng nhập: đã bỏ (SPEC-011). Gemini key: kho bảo mật Windows (SPEC-011).
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

### [SPEC-018] Phase 4: Frontend React — 2026-11-02
- Vite 6 + React 18.3 + TypeScript strict + Tailwind 4 + Zustand 5 + Recharts 2 + lucide-react + axios; 117 file, lớn nhất 141 dòng.
- **Lệch spec:** không dùng thư viện Shadcn/UI; tự viết các component cơ bản (`components/ui/*`) theo đúng token của artboard 7 để không phụ thuộc Radix và giữ bundle nhỏ. Có thể chuyển sang shadcn sau nếu cần.
- `HashRouter` (app desktop nạp giao diện từ file). Địa chỉ backend & `X-App-Token` lấy từ `window.__AUTOFORM_CONFIG__` do vỏ desktop gắn (Phase 5); khi dev dùng proxy của Vite.
- Bản nháp cấu hình từng form lưu `localStorage`; KHÔNG lưu dữ liệu Excel (vượt ~5 MB) → mở lại app cần chọn lại file.
- Tour (`components/tour/*`) chạy trên form mẫu + một "Chiến dịch tập dùng (mô phỏng)" thật → người mới thấy tiến độ trực tiếp mà không gửi gì ra ngoài.
- Màu biểu đồ đã kiểm bằng `dataviz/validate_palette.js`: sáng `#2563EB`/`#0E9384`, tối `#4F7FEA`/`#22A08E` (đạt mọi kiểm tra, kể cả mù màu). Biểu đồ có chú thích + chế độ xem bảng.
- Backend bổ sung cho giao diện: `GET /campaigns/{id}/distribution`, `page_history` trong nhật ký.
- Nút cập nhật & "Mở thư mục" chỉ hoạt động khi có cầu nối desktop (`window.autoformDesktop`, Phase 5); khi chạy dev, Cài đặt ghi rõ điều đó.
- Đã chạy app thật bằng Playwright, chụp 30+ màn hình (tour 14 bước, sáng/tối, SPSS, gửi thử, chiến dịch) → tìm và sửa BUG-005, BUG-006 và 4 lỗi giao diện nhỏ (màu link, nhãn bộ lọc SPSS, câu 2 lựa chọn lọt vào danh sách thang đo, biểu đồ chậm cập nhật).

### [SPEC-019] Phase 5: Electron + GitHub Releases — 2026-11-03
- **Chọn Electron thay Tauri:** máy dev không có Rust (Tauri cần Rust + MSVC Build Tools vài GB); `electron-updater` hỗ trợ đúng luồng artboard 5. Đổi lại bộ cài ~195 MB (Electron + Python + Playwright driver), cập nhật sau chỉ tải phần khác nhờ `.blockmap`.
- `desktop/src/`: `backend.ts` (cổng trống + mã ngẫu nhiên, chờ /health, tắt êm qua `POST /system/shutdown`), `protocol.ts` (giao diện nạp qua `app://autoform`, chặn `../`), `window.ts` (link ngoài mở bằng trình duyệt), `updater.ts` (IPC check/download/install), `preload.ts` (contextBridge, sandbox), `main.ts`.
- Backend đóng gói bằng PyInstaller `--onedir` (`backend/packaging/build_backend.py`), log ra `%APPDATA%\Auto-Form\logs\backend.log`; log vỏ desktop ở `%APPDATA%\Auto-Form\logs\main.log`.
- Tắt êm trên Windows: `system/shutdown` → `signal.raise_signal(SIGINT)` → uvicorn chạy lifespan → chiến dịch chuyển PAUSED. Đã kiểm với file .exe thật.
- CI (`ci.yml`): backend (Windows), frontend, desktop. Release (`release.yml`): tag `vX.Y.Z` phải khớp `desktop/package.json`, ghi chú lấy từ `CHANGELOG.md`, `electron-builder --publish always` dùng `GITHUB_TOKEN`.
- Repo **Public** → app tải bản cập nhật không cần token. Nếu chuyển Private phải cấp token cho từng máy (không khuyến nghị).
- Đã kiểm: bản dev và bản đóng gói (`win-unpacked`) đều mở được, gọi backend .exe qua `app://` + token, chụp màn hình, tắt êm.

### [SPEC-007] Yêu cầu bổ sung của người dùng — 2026-11-02
- UI/UX thiết kế trước; phát hành qua GitHub + Actions; thông báo & nút cập nhật; cấm God Component; duy trì dev-notes. Chi tiết trong `CLAUDE.md`.

### [SPEC-020] Soát logic bằng AI + chuỗi API key Gemini — 2026-11-03 — ĐÃ LÀM (màn 11, 12 đã duyệt)
- **Bối cảnh:** ISS-008, quy tắc 6 trong CLAUDE.md.
- **Đã chốt với người dùng:**
  - Lượt 1 (đọc toàn bộ câu hỏi) **chỉ dùng AI** (Gemini), không có chế độ quy tắc từ khoá thay thế.
  - Độ đồng đều trong một người: mặc định **"Vừa phải"** (đa số lệch ≤ 1 điểm, thỉnh thoảng 2), có thanh trượt.
  - Chuỗi key, thử theo thứ tự: key riêng người dùng → key chung của app → 1 key dự phòng → hộp thoại "Hết lượt AI" để dán key riêng. Không tạo nhiều tài khoản miễn phí để lách giới hạn (vi phạm điều khoản Google).
  - Key chung + key dự phòng **nhúng lúc build từ GitHub Secrets**, không bao giờ nằm trong mã nguồn. Người dùng phải giới hạn key chỉ gọi Gemini API, đặt hạn mức chi tiêu, và dùng key riêng cho app.
  - Hết mọi key / mất mạng → **dừng, chờ dán key** (không soát thay thế).
- **Rủi ro:** repo công khai nên ai cũng tải được file cài đặt và có thể trích key ra; thiệt hại bị chặn bởi hạn mức chi tiêu.
- **Lưu ý:** gói Google AI Pro (chat) KHÔNG kèm quota API; key phải tạo ở AI Studio.
- **Cài đặt:** `services/logic/*` (ordering, attitude, checker, repair, plan, ai_reader, text_classifier, review, validation), `services/gemini_keys.py`, `services/gemini_call.py`, `api/logic_router.py`; giao diện `pages/LogicReviewPage.tsx`, `components/logic/*`, `hooks/useLogicReview.ts`.
- **Lệch so với thiết kế:** lượt 3 SỬA TẠI CHỖ câu mâu thuẫn thay vì bỏ cả phản hồi (bỏ cả phản hồi làm lệch tỷ lệ — checks.md). Dữ liệu Excel là dữ liệu thật nên không bắt buộc soát.
- **Key:** `GEMINI_SHARED_KEY` đã lưu vào GitHub Secrets (2026-11-03); `GEMINI_BACKUP_KEY` chưa có (tuỳ chọn).
- **AI:** mặc định `gemini-flash-latest`; quá tải (503) hoặc quá 45 giây → chuyển ngay `gemini-flash-lite-latest` (đo thật: Flash quá tải trả 503 sau 10–100 giây, Lite trả lời ~8 giây với chất lượng đủ dùng).

### [SPEC-021] Thông báo kết thúc chiến dịch + Gửi lại phản hồi lỗi — 2026-11-09 — ĐÃ LÀM (màn 13 đã duyệt)
- **Yêu cầu người dùng:** gửi xong thì báo hoàn tất; gửi không thành công thì báo và nói rõ lý do; có nút gửi lại đúng các phản hồi lỗi, giữ nguyên nội dung.
- **Cài đặt:** `services/campaign_summary.py` (gom lỗi theo loại REJECTED / RATE_LIMITED / NETWORK / BROWSER / FORM_CLOSED / OTHER + cách xử lý), `GET /campaigns/{id}/summary`, `POST /campaigns/{id}/retry-failed`; cột `campaigns.status_reason` lưu lý do trạng thái (tự thêm cho CSDL cũ); `CampaignRead.auto_paused`.
- **Gửi lại giữ nguyên nội dung:** xoá nhật ký lỗi → các số thứ tự đó quay lại hàng đợi; bộ sinh dùng seed cố định theo chiến dịch + bản đồ logic đã chụp nên sinh ra ĐÚNG phản hồi cũ (Excel: đúng dòng cũ). Nếu form đã được Phân tích lại và đổi câu hỏi thì nội dung theo cấu trúc mới.
- **Giao diện:** `CompletionNotifier` gắn ở gốc app, theo dõi danh sách chiến dịch (3 giây khi có chiến dịch chạy, 8 giây khi rảnh) → hộp thoại ở mọi màn hình + thông báo Windows khi app không ở trước mặt (Electron `setAppUserModelId`, IPC `window:focus`). Không báo khi người dùng tự Tạm dừng / Dừng. Trang chiến dịch có khung kết quả để xem lại.

### [SPEC-022] Câu tự luận gõ như người thật, không như AI — 2026-11-09 — ĐÃ LÀM
- **Yêu cầu người dùng:** câu trả lời Gemini sinh không được giống AI (không phải lúc nào cũng hoa đầu dòng, đủ dấu chấm phẩy…), phải giống hành vi người thật.
- **Nghiên cứu (nguồn):** Pew Research (câu hỏi mở: trả lời trên điện thoại ~80 ký tự, máy tính ~113; câu hỏi đòi dài → nhiều người bỏ trống); DISQO & GESIS/ESRA ("không có / không biết" là câu trả lời hợp lệ, hay gặp; trả lời ngắn dần về cuối khảo sát); nghiên cứu nhận diện văn LLM (arXiv 2507.00838, 2410.16107, ACL StyGenAI 2026: AI đồng đều hơn, từ vựng "sang" hơn, chuẩn ngữ pháp, dùng gạch ngang dài; người thật dao động nhiều); ViLexNorm (EACL 2024: tiếng Việt mạng xã hội hay rút gọn từ, viết tắt, bỏ dấu).
- **Cài đặt:**
  - Câu lệnh Gemini (`gemini_service.build_prompt`): viết như N người khác nhau, tỷ lệ độ dài (1/3 rất ngắn), ~1/8 trả lời qua loa, quan điểm khen/chê/trung lập, văn nói; cấm gạch đầu dòng, ngoặc kép, gạch ngang dài, chấm than, "Theo tôi", cụm sáo rỗng; không chép ví dụ.
  - `humanize/ai_cleanup.py`: gỡ dấu vết AI còn sót trước khi lưu pool.
  - `humanize/styles.py` + `humanizer.py`: mỗi người điền một kiểu gõ (cẩn thận 25%, thường 40%, lười 20%, không dấu 10%, teencode nhẹ 5%) áp cho MỌI câu tự luận + ô "Mục khác" của họ: chữ hoa / dấu chấm cuối / dấu phẩy theo xác suất, viết tắt (ko, dc, j, r, vs, mn, sp…), gõ không dấu, lỗi gõ ~1–2% số từ, kiểu lười chỉ gõ vế đầu.
  - Chỉ áp cho dữ liệu tự sinh khi chạy / gửi thử (Excel là dữ liệu thật → giữ nguyên); theo seed chiến dịch nên "Gửi lại phản hồi lỗi" vẫn ra đúng câu cũ.
- **Kết quả thử thật (Gemini, câu C16 form Tiki):** câu ngắn đời thường, có kể chuyện cụ thể, có chê thẳng; trước khi sửa câu lệnh, AI chép nguyên văn ví dụ → đã cấm.

### [SPEC-023] Chuẩn bị lần đầu: tự cài thành phần còn thiếu khi mở app — 2026-11-09 — ĐÃ LÀM
- **Yêu cầu người dùng:** người dùng chỉ biết cài và dùng; lần đầu chạy app tự quét thành phần cần thiết, thiếu thì tự cài; lần sau mở là chạy ngay.
- **Quét bộ cài v0.1.0:** Python + mọi thư viện backend, giao diện, driver Playwright (Node) đều đã đóng gói trong bộ cài (PyInstaller + electron-builder) → máy người dùng không cần cài gì. Thành phần duy nhất tải riêng: Chrome Headless Shell cho trình duyệt dự phòng (~100 MB, RISK-012) — trước đây phải tự bấm tải trong Cài đặt.
- **Cài đặt:** `BrowserSetupBanner` gắn trong `AppShell`; `useBrowserInstall({ autoInstall: true })` hỏi `GET /system/browser` khi mở app, chưa có → tự `POST /system/browser/install` (mỗi phiên tự thử 1 lần, `shouldAutoInstall`). Đang tải: dải tiến độ, app dùng bình thường. Lỗi: nút Thử lại; backend khởi động lại ở lần mở sau nên tự thử lại. Đã có: không hiện gì.
- **Vị trí cài:** `%LOCALAPPDATA%\ms-playwright` (mặc định Playwright) → giữ nguyên qua các lần cập nhật app, không tải lại.
- **Kiểm chứng:** giả lập máy mới (`PLAYWRIGHT_BROWSERS_PATH` rỗng): lần đầu installed=false → tự tải xong ~20 giây → installed=true; mở lại: installed=true, không tải. Test giao diện: tự tải lần đầu / không làm gì khi đã có / lỗi hiện Thử lại và không tải lặp.
- **Vì sao không nhúng Chromium vào bộ cài:** bộ cài đã 186 MB; nhúng thêm ~100 MB làm mỗi bản cập nhật nặng hơn cho 40–50 người dùng, trong khi tải một lần là đủ.
