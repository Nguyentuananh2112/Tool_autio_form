# Conflicts

### [CONF-001] Mã điều hướng rẽ nhánh: spec SAI so với Google Forms thực tế — 2026-11-02 — FIXED
- **Bối cảnh:** `backend/app/schemas/form_schema.py` (hằng `JUMP_NEXT_PAGE`, `JUMP_SUBMIT`, `JUMP_UNCONFIRMED`).
- **Mâu thuẫn:** Spec (Mục 5.1.C) ghi `-1` = sang trang tiếp, `-2` = nộp form.
- **Xác nhận trên form thật** (khảo sát Tiki, 10 trang, 53 câu):
  - Câu C11 có cả 4 lựa chọn = `-2` — đúng giá trị mặc định Google gán khi bật "Chuyển đến phần dựa trên câu trả lời" ("Tiếp tục đến phần tiếp theo"). Nếu `-2` là nộp thì mọi người đi nhánh "Đã từng mua" sẽ bị nộp ở trang C và bỏ qua phần D → vô lý.
  - Page Break "Kết thúc khảo sát" có `item[5] = -3` → điều hướng "Gửi biểu mẫu" cho trang trước nó.
  - **Kết luận:** `-2` = tiếp tục phần tiếp theo, `-3` = gửi biểu mẫu, số dương = id section đích. `-1` chưa gặp (có thể là "quay lại phần 1"), tạm coi là sang trang tiếp.
- **Cách xử lý:** Đổi hằng số; thêm `tests/test_real_form_patterns.py` (dữ liệu ẩn danh hóa mô phỏng form thật). Với form thật, 1.000 mẫu sinh ra đúng 3 đường đi mà tác giả form thiết kế.
- **Bài học:** Spec có thể sai ở chi tiết reverse-engineering. Mọi giả định về `FB_PUBLIC_LOAD_DATA_` phải được kiểm chứng bằng form thật trước khi dựa vào.
