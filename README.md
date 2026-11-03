# Auto-Form

Ứng dụng desktop Windows giúp cấu hình và gửi phản hồi cho Google Form công khai: đặt tỷ lệ đáp án,
nhóm tương quan SPSS, câu tự luận (Gemini), nhập từ Excel/CSV, theo dõi tiến độ trực tiếp.

## Cài đặt (người dùng)

1. Vào trang **Releases** của repo này, tải `Auto-Form-Setup-X.Y.Z.exe` ở bản mới nhất.
2. Mở file. Windows có thể hiện **“Windows protected your PC”** vì bộ cài chưa được ký số →
   bấm **More info → Run anyway**.
3. App tự kiểm tra bản mới mỗi lần mở; khi có bản mới sẽ hiện thông báo và nút **Cập nhật**.

Dữ liệu (form, chiến dịch, nhật ký) nằm ở `%APPDATA%\Auto-Form`. Gỡ/cài lại không xóa dữ liệu.

## Cấu trúc

| Thư mục | Nội dung |
|---|---|
| `backend/` | FastAPI + SQLite: phân tích form, sinh dữ liệu, gửi phản hồi, WebSocket |
| `frontend/` | React + TypeScript + Tailwind: toàn bộ giao diện |
| `desktop/` | Vỏ Electron: chạy backend kèm app, cửa sổ, tự cập nhật từ GitHub Releases |
| `docs/` | Đặc tả (`SPECIFICATION.md`), thiết kế UI/UX, sổ ghi chép phát triển (`dev-notes/`) |

## Phát triển

Yêu cầu: Python 3.12, Node.js 22+.

```bash
# Backend
cd backend
python -m venv .venv && .venv\Scripts\activate
pip install -r requirements-dev.txt
python -m app                # http://127.0.0.1:8765
python -m pytest -q

# Giao diện (cửa sổ khác)
cd frontend
npm ci
npx vite                     # http://localhost:5173 (proxy /api sang backend)

# App desktop với backend & giao diện đang có
cd desktop
npm ci
npm start
```

> Chạy Electron từ terminal của VS Code: đặt `ELECTRON_RUN_AS_NODE=` (rỗng) trước, nếu không Electron chạy như Node thường.

## Phát hành bản mới

1. Sửa `version` trong `desktop/package.json` (VD `0.2.0`).
2. Thêm mục `## [0.2.0]` vào `CHANGELOG.md` — ghi chú này hiện cho người dùng trong hộp thoại cập nhật.
3. Commit, rồi tạo & đẩy tag:
   ```bash
   git tag v0.2.0
   git push origin main --tags
   ```
4. GitHub Actions (`Release`) tự kiểm thử, build bộ cài và đăng Release. App của mọi người sẽ thấy bản mới.

CI (`.github/workflows/ci.yml`) chạy kiểm thử backend, frontend và vỏ desktop cho mọi lần đẩy code / Pull Request.
