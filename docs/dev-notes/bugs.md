# Bugs

### [BUG-001] Điều kiện kiểm tra `min_checked` sai — 2026-11-02 — FIXED
- **Bối cảnh:** `backend/app/services/spss_generator.py`, `_validate_question` cho Checkbox.
- **Hiện tượng:** Chỉ báo lỗi `min_checked > số lựa chọn` khi `max_checked` có giá trị; nếu `max_checked=None` thì cấu hình sai lọt qua.
- **Nguyên nhân gốc:** Ghép nhầm điều kiện `rule.max_checked is not None` vào kiểm tra `min_checked`.
- **Cách xử lý:** Bỏ điều kiện thừa, chỉ còn `rule and rule.min_checked > len(options)`.
- **Bài học:** Mỗi điều kiện validate chỉ kiểm tra đúng một ràng buộc; viết test cho cả nhánh `None`.
