import os
import tempfile
from pathlib import Path

# Test dùng file SQLite tạm (giống bản thật: mỗi phiên một kết nối riêng), không đụng tới
# dữ liệu thật trong %APPDATA%\Auto-Form. KHÔNG dùng ":memory:" cho test có chạy nền đồng thời:
# StaticPool dùng chung một kết nối → phiên này rollback làm mất ghi dở của phiên khác (BUG-002).
_TEST_DIR = Path(tempfile.mkdtemp(prefix="autoform-test-"))
os.environ["DATA_DIR"] = str(_TEST_DIR)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_TEST_DIR / 'test.db').as_posix()}"
os.environ.pop("APP_TOKEN", None)
# Không bao giờ dùng key Gemini thật của máy dev (backend/.env) trong test
os.environ["GEMINI_API_KEY"] = ""
