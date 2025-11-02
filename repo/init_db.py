import asyncio
from app.db.models import Base
from app.core.database import engine

async def init_models():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    print("✔ Database initialized successfully!")

if __name__ == "__main__":
    try:
        asyncio.run(init_models())
    except RuntimeError:
        # Ignore event loop closed error on Windows
        pass
