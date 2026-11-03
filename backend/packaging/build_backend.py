"""Đóng gói backend thành thư mục `dist/autoform-backend/` (chứa autoform-backend.exe) bằng PyInstaller.

Chạy từ thư mục backend:  python packaging/build_backend.py
Vỏ desktop (electron-builder) chép nguyên thư mục này vào bộ cài (extraResources).
"""

from __future__ import annotations

import sys
from pathlib import Path

import PyInstaller.__main__

BACKEND_DIR = Path(__file__).resolve().parents[1]

ARGS = [
    str(BACKEND_DIR / "run_backend.py"),
    "--name", "autoform-backend",
    "--onedir",  # khởi động nhanh hơn --onefile (không phải giải nén mỗi lần mở)
    "--noconfirm",
    "--clean",
    "--console",  # vỏ desktop ẩn cửa sổ bằng windowsHide; giữ console để đọc lỗi khi chạy tay
    "--distpath", str(BACKEND_DIR / "dist"),
    "--workpath", str(BACKEND_DIR / "build"),
    "--specpath", str(BACKEND_DIR / "build"),
    "--paths", str(BACKEND_DIR),
    "--collect-submodules", "app",
    "--collect-submodules", "uvicorn",
    "--collect-submodules", "keyring.backends",
    "--collect-data", "playwright",  # driver Node của Playwright (Chromium tải riêng khi cần — RISK-006)
    "--hidden-import", "aiosqlite",
    "--copy-metadata", "google-genai",
    "--copy-metadata", "keyring",
    "--exclude-module", "pytest",
    "--exclude-module", "tkinter",
    "--exclude-module", "matplotlib",
    "--exclude-module", "IPython",
]

if __name__ == "__main__":
    PyInstaller.__main__.run(ARGS + sys.argv[1:])
