"""Database connection and session management."""

import os
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/game_scheduler"
)

engine = create_async_engine(DATABASE_URL, echo=False, pool_pre_ping=True)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Provide database session for FastAPI dependency injection.

    Use this with FastAPI's Depends() for automatic session lifecycle management.
    FastAPI will handle the async generator properly.

    Example:
        @app.get("/items")
        async def get_items(db: AsyncSession = Depends(get_db)):
            result = await db.execute(select(Item))
            return result.scalars().all()
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


def get_db_session() -> AsyncSession:
    """
    Get database session for use as async context manager.

    Use this pattern in Discord bot commands and other non-FastAPI code
    where you need to manage the session lifecycle explicitly.

    DO NOT use this with FastAPI Depends() - use get_db() instead.

    Example:
        async with get_db_session() as db:
            result = await db.execute(select(Item))
            await db.commit()

    Returns:
        AsyncSession that must be used with 'async with' statement
    """
    return AsyncSessionLocal()
