import asyncio
import sys
from app.db.models import Base
from app.core.database import engine

if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

async def init_models():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    print("✔ Database initialized successfully!")

if __name__ == "__main__":
    asyncio.run(init_models())
