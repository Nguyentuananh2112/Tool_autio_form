from app.core.database import Base, engine
from app.workers.campaign_control import registry


async def reset_database() -> None:
    """Dừng mọi chiến dịch chạy nền của test, xóa bảng, đóng kết nối (tránh rò sang test sau)."""
    await registry.stop_all(timeout=5)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()
