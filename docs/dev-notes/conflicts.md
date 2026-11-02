# Conflicts

### [CONF-001] Mã điều hướng rẽ nhánh: spec vs Google Forms thực tế — 2026-11-02 — OPEN
- **Bối cảnh:** `backend/app/schemas/form_schema.py` (hằng `JUMP_NEXT_PAGE`, `JUMP_SUBMIT`, `JUMP_SUBMIT_ALT`).
- **Mâu thuẫn:** Spec (Mục 5.1.C) ghi `-1` = sang trang tiếp, `-2` = nộp form. Có khả năng Google thực tế dùng `-2` = phần tiếp theo, `-3` = nộp.
- **Hệ quả nếu sai:** Đáp án đặt "Tiếp tục đến phần tiếp theo" bị hiểu là "Nộp" → mẫu bị cắt mất các trang sau.
- **Hiện trạng:** Đang theo spec; `-3` cũng coi là nộp. Smoke test chỉ dùng dữ liệu giả theo spec nên CHƯA xác nhận.
- **Cần làm:** Parse một form thật có rẽ nhánh (đủ 3 loại: sang phần X, tiếp tục, nộp) rồi đối chiếu `FB_PUBLIC_LOAD_DATA_` thô.
