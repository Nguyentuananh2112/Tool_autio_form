"""Kết nối SQLite bất đồng bộ (SQLAlchemy 2.0 + aiosqlite) cho app desktop."""

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator, AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from sqlalchemy import MetaData, event, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import StaticPool

from app.core.config import Settings, settings

logger = logging.getLogger(__name__)

# Quy ước đặt tên constraint giúp Alembic autogenerate ổn định.
NAMING_CONVENTION: dict[str, str] = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


def _apply_sqlite_pragmas(dbapi_connection: Any, _connection_record: Any) -> None:
    """SQLite mặc định TẮT khóa ngoại → phải bật để ON DELETE CASCADE hoạt động."""
    cursor = dbapi_connection.cursor()
    try:
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")  # cho phép đọc trong lúc worker đang ghi log
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA busy_timeout=5000")
    finally:
        cursor.close()


def create_engine_for(app_settings: Settings) -> AsyncEngine:
    if app_settings.is_in_memory_db:
        # Mọi session phải dùng chung một kết nối, nếu không mỗi kết nối là một DB rỗng riêng
        new_engine = create_async_engine(
            app_settings.DATABASE_URL,
            echo=app_settings.DB_ECHO,
            poolclass=StaticPool,
            connect_args={"check_same_thread": False},
        )
    else:
        app_settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
        new_engine = create_async_engine(
            app_settings.DATABASE_URL,
            echo=app_settings.DB_ECHO,
            connect_args={"timeout": 30},
        )
    event.listen(new_engine.sync_engine, "connect", _apply_sqlite_pragmas)
    return new_engine


engine: AsyncEngine = create_engine_for(settings)

AsyncSessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency cho FastAPI: mỗi request một session, rollback nếu có lỗi."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


@asynccontextmanager
async def session_scope() -> AsyncIterator[AsyncSession]:
    """Session có commit/rollback tự động, dùng cho background worker."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# Cột thêm sau khi đã có người dùng: create_all không sửa bảng cũ nên thêm bằng ALTER TABLE.
# Chỉ thêm cột cho phép NULL (an toàn với dữ liệu sẵn có).
ADDED_COLUMNS: tuple[tuple[str, str, str], ...] = (
    ("forms", "logic_map", "JSON"),
    ("campaigns", "logic_map", "JSON"),
)


def _add_missing_columns(sync_conn: Any) -> None:
    for table, column, ddl_type in ADDED_COLUMNS:
        existing = {row[1] for row in sync_conn.exec_driver_sql(f"PRAGMA table_info({table})")}
        if existing and column not in existing:
            sync_conn.exec_driver_sql(f"ALTER TABLE {table} ADD COLUMN {column} {ddl_type}")
            logger.info("Đã thêm cột %s.%s", table, column)


async def init_db() -> None:
    """Tạo bảng nếu chưa có và bổ sung cột mới cho CSDL của phiên bản cũ."""
    import app.models  # noqa: F401  # đăng ký toàn bộ model vào Base.metadata

    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            await conn.run_sync(_add_missing_columns)
    except SQLAlchemyError:
        logger.exception("Không thể khởi tạo schema cơ sở dữ liệu")
        raise


async def check_db_connection() -> bool:
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except (SQLAlchemyError, OSError):
        logger.exception("Kiểm tra kết nối cơ sở dữ liệu thất bại")
        return False


async def dispose_engine() -> None:
    await engine.dispose()
