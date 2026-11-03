"""Sinh app/core/_build_secrets.py từ biến môi trường (GitHub Secrets) trước khi đóng gói.

Dùng trong .github/workflows/release.yml:
    GEMINI_SHARED_KEY=${{ secrets.GEMINI_SHARED_KEY }} GEMINI_BACKUP_KEY=${{ secrets.GEMINI_BACKUP_KEY }}
    python packaging/write_build_secrets.py
Không in key ra log. Thiếu biến nào thì key đó để trống (app sẽ hỏi người dùng dán key riêng).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.core.build_secrets import encode  # noqa: E402

TARGET = BACKEND_DIR / "app" / "core" / "_build_secrets.py"


def main() -> None:
    shared = os.environ.get("GEMINI_SHARED_KEY", "").strip()
    backup = os.environ.get("GEMINI_BACKUP_KEY", "").strip()
    TARGET.write_text(
        "# File sinh tự động lúc build — KHÔNG commit (đã gitignore).\n"
        f"SHARED = {encode(shared) if shared else ''!r}\n"
        f"BACKUP = {encode(backup) if backup else ''!r}\n",
        encoding="utf-8",
    )
    print(f"Đã ghi {TARGET.name}: key chung={'có' if shared else 'không'}, key dự phòng={'có' if backup else 'không'}")


if __name__ == "__main__":
    main()
