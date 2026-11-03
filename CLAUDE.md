# CLAUDE.md — Quy tắc bắt buộc của dự án Auto-Form System

Trao đổi với người dùng bằng **tiếng Việt**. Tên code, thuật ngữ kỹ thuật giữ tiếng Anh.

## Tài liệu nguồn
- `docs/SPECIFICATION.md`: bản đặc tả kỹ thuật gốc (kiến trúc bắt buộc, 4 Phase).
- `docs/ui-ux/README.md`: bản thiết kế UI/UX (link canvas, danh sách màn hình, cây component). Frontend phải bám theo.
- `docs/dev-notes/`: sổ ghi chép bug / conflict / issue / risk / spec / perf / check. **Đọc trước khi bắt đầu một Phase hoặc sửa module liên quan; ghi thêm ngay khi gặp vấn đề mới.**

## Yêu cầu bổ sung của người dùng (ngoài spec)
1. **UI/UX thiết kế trước, code sau.** Phải có bản thiết kế UI/UX được duyệt trước khi viết frontend (Phase 4); khi code bám sát bản thiết kế đó.
2. **Ứng dụng desktop (đã chốt 2026-11-02, xem dev-notes SPEC-008)**: mỗi user cài trên máy mình; DB là SQLite nhúng thay cho PostgreSQL/Redis của spec. **Phát hành cho 40–50 người dùng qua GitHub.** Repo trên GitHub, dùng GitHub Actions cho CI/CD (kiểm thử tự động khi push/PR). Khi có bản cập nhật mới (tính năng / sửa lỗi) được publish, người dùng phải **nhận thông báo có bản mới và bấm "Cập nhật" để cập nhật**.
3. **Cấm "God Component" / "God Module".** Chia nhỏ code thành module/component, tách folder khi cần. Mỗi file một trách nhiệm rõ ràng. Đây là nguyên tắc sống còn, phải tuân thủ cả backend lẫn frontend.
4. **Người mới mở app phải biết làm gì ngay (yêu cầu 2026-11-02).** Có tour lần đầu chỉ dẫn TỪNG tính năng ngay trên giao diện (làm sáng tính năng + bong bóng giải thích cạnh nó, bấm Tiếp sang tính năng kế), trang Hướng dẫn tính năng, thanh bước ① Phân tích → ② Cấu hình → ③ Chạy, mỗi màn hình chỉ MỘT nút chính, tùy chọn nâng cao gấp gọn, màn hình trống luôn chỉ ra việc tiếp theo, giải thích thuật ngữ (Alpha, SPSS…) bằng lời thường qua nút "?". Xem `docs/ui-ux/README.md` mục Hướng dẫn người mới.
5. **Ghi chép dev-notes.** Mọi bug, conflict, issue, risk, quyết định lệch spec, vấn đề hiệu năng, checklist kiểm tra đều ghi vào `docs/dev-notes/*.md` để không lặp lại lỗi cũ.
6. **Câu trả lời phải logic với nhau trong MỌI form (yêu cầu 2026-11-03, xem dev-notes ISS-008).** Một người điền phải nhất quán từ câu trước tới câu sau (VD uy tín 4 điểm thì chất lượng không thể 1 điểm; mức độ các câu đánh giá "sàn sàn" nhau; nhân khẩu học không mâu thuẫn; ô loại trừ như "Không có…" không đi kèm ô khác). Trước khi điền bất kỳ form nào phải có **1–3 lượt soát (đọc) toàn bộ câu hỏi và câu trả lời**, xong mới bắt đầu gửi.

## Quy ước kỹ thuật
- Backend: Python 3.12, môi trường ảo `backend/.venv` (`backend\.venv\Scripts\python.exe`).
- DB: SQLite (`aiosqlite`) tại `%APPDATA%\Auto-Form\auto_form.db`; test dùng file SQLite tạm (KHÔNG dùng `:memory:` — dev-notes BUG-002). Không có tài khoản/đăng nhập (SPEC-011).
- Frontend: `frontend/` (Vite + React + TS + Tailwind 4). Dev: `python -m app` trong backend + `npx vite` trong frontend, mở `http://localhost:5173`. Kiểm tra: `npx tsc --noEmit -p .`, `npx vitest run`.
- Async-first cho mọi I/O; Pydantic v2; SQLAlchemy 2.0 async; không viết code giả (placeholder).
- Module thuần CPU (`spss_generator`) gọi qua `asyncio.to_thread` trong code async.
- Không commit `.env`, `.venv`, `node_modules`.

## Gợi ý kích thước (chống God Component)
- File Python > ~400 dòng hoặc React component > ~200 dòng → cân nhắc tách.
- Component React: tách logic (hooks) khỏi trình bày; mỗi component một việc.
