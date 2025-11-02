from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import settings

# Shared Base for ORM models
Base = declarative_base()

# Async engine
engine = create_async_engine(
    settings.DB_URL,
    echo=settings.SQL_ECHO,
    future=True
)

# Async session factory
AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)