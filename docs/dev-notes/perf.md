# Performance

### [PERF-001] Sinh dữ liệu vector hóa theo cột — 2026-11-02
- `spss_generator` sinh cả cột N mẫu cho mỗi câu bằng numpy (`rng.choice`, `multivariate_normal`) rồi mới ghép theo dòng.
- Smoke test: 2.000 phản hồi × 9 câu + preview + hiệu chỉnh chạy trong vài giây trên máy dev.
- Module thuần CPU → trong FastAPI phải gọi `asyncio.to_thread`, không chạy trực tiếp trong event loop.
