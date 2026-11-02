import os

# Test dùng SQLite trong bộ nhớ, không đụng tới dữ liệu thật trong %APPDATA%\Auto-Form
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
