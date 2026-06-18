"""
Async SQLAlchemy session factory.
Used by FastAPI route dependencies.
"""

from app.core.config import settings
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.ENVIRONMENT == "development",  # logs SQL in dev only
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,  # reconnect on stale connections
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncSession:
    """FastAPI dependency — yields a DB session per request."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
