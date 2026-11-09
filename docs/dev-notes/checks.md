# Checklists

## Trước mỗi commit
- [ ] `pytest -q` pass (trong `backend/`, dùng `.venv\Scripts\python.exe -m pytest -q`)
- [ ] `python -m ruff check app tests` sạch (cấu hình trong `backend/pyproject.toml`)
- [ ] `wc -l app/*/*.py app/*/*/*.py`: không file nào > 400 dòng (SPEC-014)
- [ ] Frontend (`frontend/`): `npx tsc --noEmit -p .`, `npx vitest run`, `npx vite build` đều sạch; không component nào > ~200 dòng
- [ ] Đổi giao diện → chạy app thật và chụp màn hình (ISS-006), xem cả chế độ sáng và tối
- [ ] Không có file > ~400 dòng (Python) / > ~200 dòng (React component) mà không có lý do
- [ ] Không commit `.env`, `.venv`, `node_modules`, dữ liệu thật của user
- [ ] Đã ghi vấn đề mới vào `docs/dev-notes/`

## Trước khi bắt đầu Phase mới
- [ ] Đọc `CLAUDE.md`, `docs/SPECIFICATION.md` (phần liên quan), toàn bộ `docs/dev-notes/`
- [ ] Các mục OPEN liên quan đến Phase đã được xử lý hoặc có kế hoạch

## Trước khi release (GitHub)
- [ ] CI (GitHub Actions) xanh
- [ ] Tăng version + changelog
- [ ] Thử luồng "có bản cập nhật → bấm Cập nhật" trên máy sạch

## Kiểm tra parser với form thật
- [x] Rẽ nhánh: sang phần X / tiếp tục / nộp (CONF-001) — xác nhận 2026-11-02
- [x] Grid trắc nghiệm — [ ] checkbox grid (`row[11]`)
- [x] Mục khác (Other), Linear scale 1–5 và 1–10 — [ ] Dropdown, Date, Time
- [ ] Form thu thập email (RISK-003) — form thật đầu tiên không bật

## 2026-11-03 — Chạy thật 100 phản hồi (bản sao form Tiki, chỉ để thử)
- 100/100 gửi thành công, 0 lỗi, ~15,6 phút (lịch 15 phút, 1 luồng); log backend sạch.
- Rẽ nhánh: 3 đường đi 68 / 21 / 11; câu bắt buộc thiếu = 0; không có đáp án thừa ở trang không đi qua.
- SPSS: thang C10 α = 0,858, TB 3,88 (mục tiêu 0,85 / 3,8); C15 α = 0,79 với n = 68 (dao động mẫu).
- "Mục khác" ~5%. Phát hiện BUG-014 (hộp kiểm luôn đủ N ô) → đã sửa.
- Test: backend 724 passed (ruff sạch), frontend 19 passed (tsc sạch).

## 2026-11-03 — Soát logic: đo trên form Tiki (cấu hình lần chạy 100 phản hồi, 400 mẫu, mức Vừa phải)
- Bản đồ do Gemini đọc thật (rơi về flash-lite vì flash quá tải 503): 22 câu một nhóm "Đánh giá thương hiệu Tiki", chiều tích cực đúng cả 22; ràng buộc tuổi→nghề; 2 ô loại trừ; 2 câu tự luận theo thái độ.
- Trước → sau: lệch ≥3 điểm trong C10 16 → 0; C10↔C15 −0,05 → 0,52; C12↔C13 −0,04 → 0,70; "Dưới 18 mà đi làm" 78 → 0; "không nhận diện Tiki nhưng luôn thấy quảng cáo" 35 → 0; ô loại trừ kèm ô khác 136 → 0.
- Giữ tỷ lệ: C10 TB 3,80 → 3,78; C12 TB 5,81 → 5,88; tỷ lệ B1 giữ nguyên. Alpha C10 0,859 → 0,888 (do kéo câu lệch vào gần).
- Bài học thiết kế: loại cả phản hồi rồi sinh lại làm lệch tỷ lệ (bớt người "Dưới 18", bớt người đi nhánh nhiều câu) → SỬA TẠI CHỖ câu mâu thuẫn; chỉ so độ lệch theo ngưỡng giữa câu chấm điểm, câu chữ chỉ chặn hai đầu ngược nhau.
- Trước commit có làm việc với key: `grep -rn "<tiền tố key>" .` chỉ được ra `backend/.env`.

## 2026-11-09 — Kiểm tra bản đóng gói có key chung nhúng sẵn
- `write_build_secrets.py` (key lấy từ .env, không in ra) → `build_backend.py` → chạy `autoform-backend.exe` với ENVIRONMENT=production, APP_TOKEN, GEMINI_API_KEY rỗng.
- `GET /settings` trả `gemini_shared_key: true`, không có token → 401. File key trong mã nguồn đã mã hoá (grep key thô = 0).
- Lượt 1 gọi từ exe: Flash quá 45 giây → Lite 503 (Google quá tải lúc đó) → thêm vòng thử lại thứ hai (RISK-013).
- Dọn dẹp: đã xoá `app/core/_build_secrets.py`, `dist/`, `build/` (chứa key) sau khi thử.
