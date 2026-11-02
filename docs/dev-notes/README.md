# Dev Notes — Sổ ghi chép phát triển

Mục đích: ghi lại mọi vấn đề gặp phải để **không lặp lại lỗi cũ**. Đọc file liên quan trước khi sửa module; ghi ngay khi phát hiện vấn đề mới.

| File | Ghi gì |
|---|---|
| [bugs.md](bugs.md) | Lỗi trong code: nguyên nhân gốc, cách sửa, bài học |
| [conflicts.md](conflicts.md) | Xung đột: thư viện/phiên bản, spec vs thực tế, yêu cầu mâu thuẫn |
| [issues.md](issues.md) | Vấn đề môi trường/công cụ/vận hành chưa phải bug code |
| [risks.md](risks.md) | Rủi ro chưa xảy ra nhưng cần theo dõi, kèm cách giảm thiểu |
| [spec.md](spec.md) | Quyết định thiết kế, điểm lệch/bổ sung so với SPECIFICATION.md |
| [perf.md](perf.md) | Hiệu năng: số đo, nút thắt, tối ưu đã làm |
| [checks.md](checks.md) | Checklist kiểm tra trước khi commit / release |

## Mẫu ghi một mục
```
### [MÃ-SỐ] Tiêu đề ngắn — YYYY-MM-DD — Trạng thái: OPEN | FIXED | WONTFIX | MONITORING
- **Bối cảnh:** đang làm gì, file nào
- **Hiện tượng:** thấy gì
- **Nguyên nhân gốc:** vì sao
- **Cách xử lý:** đã làm gì (link file:dòng)
- **Bài học / Quy tắc:** lần sau phải làm gì để tránh
```
Mã: BUG-, CONF-, ISS-, RISK-, SPEC-, PERF-.
