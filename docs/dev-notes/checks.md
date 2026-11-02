# Checklists

## Trước mỗi commit
- [ ] `pytest -q` pass (trong `backend/`, dùng `.venv\Scripts\python.exe -m pytest -q`)
- [ ] `python -m ruff check app tests` sạch (cấu hình trong `backend/pyproject.toml`)
- [ ] `wc -l app/*/*.py app/*/*/*.py`: không file nào > 400 dòng (SPEC-014)
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
