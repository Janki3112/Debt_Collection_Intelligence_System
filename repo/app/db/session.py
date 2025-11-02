"""
Async database session management
"""
import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool, QueuePool
from typing import AsyncGenerator

from app.db import models
from app.logger import logger

# Get database URL from environment
DB_URL = os.getenv("DB_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/ai_developer_db")

# Determine if using PostgreSQL or SQLite
is_postgres = "postgresql" in DB_URL

# Configure engine based on database type
if is_postgres:
    engine = create_async_engine(
        DB_URL,
        echo=os.getenv("SQL_ECHO", "false").lower() == "true",
        poolclass=QueuePool,
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,  # Verify connections before using
    )
else:
    engine = create_async_engine(
        DB_URL,
        echo=os.getenv("SQL_ECHO", "false").lower() == "true",
        poolclass=NullPool,
        connect_args={"check_same_thread": False},
    )

# Create session factory
async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for getting database session"""
    async with async_session_factory() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    """Initialize database tables"""
    try:
        async with engine.begin() as conn:
            await conn.run_sync(models.metadata.create_all)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {str(e)}")
        raise


async def close_db():
    """Close database connections"""
    try:
        await engine.dispose()
        logger.info("Database connections closed")
    except Exception as e:
        logger.error(f"Error closing database: {str(e)}")
    
# Alias for backward compatibility
async_session = async_session_factory
