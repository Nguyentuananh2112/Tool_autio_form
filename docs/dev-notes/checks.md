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
