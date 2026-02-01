# Copyright 2025 Bret McKee (bret.mckee@gmail.com)
#
# This file is part of Game_Scheduler. (https://github.com/game-scheduler)
#
# Game_Scheduler is free software: you can redistribute it and/or
# modify it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or (at your
# option) any later version.
#
# Game_Scheduler is distributed in the hope that it will be
# useful, but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Affero General
# Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License along
# with Game_Scheduler If not, see <https://www.gnu.org/licenses/>.


"""Database connection and session management."""

import asyncio
import logging
import os
from collections.abc import AsyncGenerator, Generator
from contextlib import contextmanager
from typing import Any

from fastapi import Depends
from sqlalchemy import create_engine as create_sync_engine
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session, sessionmaker

from shared.data_access.guild_isolation import (
    clear_current_guild_ids,
)
from shared.schemas.auth import CurrentUser

logger = logging.getLogger(__name__)

# Base PostgreSQL URL without driver specification
_raw_database_url = os.getenv(
    "DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/game_scheduler"
)

# Strip any driver specification to get base URL
BASE_DATABASE_URL = _raw_database_url.replace("postgresql+asyncpg://", "postgresql://").replace(
    "postgresql+psycopg2://", "postgresql://"
)

# Build driver-specific URLs by adding driver to base URL
ASYNC_DATABASE_URL = BASE_DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
SYNC_DATABASE_URL = BASE_DATABASE_URL.replace("postgresql://", "postgresql+psycopg2://")

# For backward compatibility - services importing DATABASE_URL get async version
DATABASE_URL = ASYNC_DATABASE_URL

# Async engine for API and Bot services
engine = create_async_engine(ASYNC_DATABASE_URL, echo=False, pool_pre_ping=True)

# Sync engine for Scheduler service
sync_engine = create_sync_engine(SYNC_DATABASE_URL, echo=False, pool_pre_ping=True)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

SyncSessionLocal = sessionmaker(
    sync_engine,
    class_=Session,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession]:
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


def get_db_with_user_guilds() -> Any:  # noqa: ANN401
    """
    Factory function that returns a database dependency with user guild context.

    This should be called as: db: AsyncSession = Depends(get_db_with_user_guilds())

    The returned dependency function will automatically receive current_user from
    the route's dependency chain.
    """
    from services.api.dependencies import (  # noqa: PLC0415 - avoid circular dependency
        auth,
    )

    async def _get_db_with_guilds(
        current_user: CurrentUser = Depends(auth.get_current_user),  # noqa: B008
    ) -> AsyncGenerator[AsyncSession]:
        """Inner dependency that receives current_user and provides DB session."""
        from services.api.auth import (  # noqa: PLC0415 - avoid circular dependency
            oauth2,
        )
        from services.api.database import queries  # noqa: PLC0415

        # Fetch user's guilds (cached with 5-min TTL) - returns Discord IDs
        user_guilds = await oauth2.get_user_guilds(
            current_user.access_token, current_user.user.discord_id
        )
        discord_guild_ids = [g["id"] for g in user_guilds]

        # Set up RLS context and convert Discord IDs to database UUIDs
        async with AsyncSessionLocal() as temp_session:
            await queries.setup_rls_and_convert_guild_ids(temp_session, discord_guild_ids)

        # Yield session - event listener will set RLS on next query
        async with AsyncSessionLocal() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()
                clear_current_guild_ids()

    return _get_db_with_guilds


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


@contextmanager
def get_sync_db_session() -> Generator[Session]:
    """
    Get synchronous database session for use as context manager.

    Use this pattern in Celery tasks and other synchronous code
    where async operations provide no benefit.

    Example:
        with get_sync_db_session() as db:
            result = db.execute(select(Item))
            db.commit()

    Yields:
        Session: Synchronous SQLAlchemy session
    """
    session = SyncSessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


# Event listeners for deferred event publishing


@event.listens_for(AsyncSession.sync_session_class, "after_commit")
def publish_deferred_events_after_commit(session: Session) -> None:
    """
    Publish deferred events after successful transaction commit.

    This ensures events are only sent to consumers after database
    changes are visible, preventing race conditions.

    Args:
        session: SQLAlchemy session that was committed
    """
    from shared.messaging import (  # noqa: PLC0415
        deferred_publisher,
        publisher,
    )

    deferred_events = deferred_publisher.DeferredEventPublisher.get_deferred_events(session)

    if not deferred_events:
        return

    logger.info("Publishing %d deferred events after commit", len(deferred_events))

    event_pub = publisher.EventPublisher()

    async def _publish_all() -> None:
        """Publish all deferred events asynchronously."""
        try:
            await event_pub.connect()

            for deferred_event in deferred_events:
                event = deferred_event["event"]
                routing_key = deferred_event["routing_key"]

                await event_pub.publish(event=event, routing_key=routing_key)

                logger.debug("Published deferred event: %s", event.event_type)

        except Exception:
            logger.exception("Failed to publish deferred events")
        finally:
            await event_pub.close()
            deferred_publisher.DeferredEventPublisher.clear_deferred_events(session)

    task = asyncio.create_task(_publish_all())
    task.add_done_callback(lambda t: t.exception() if not t.cancelled() else None)


@event.listens_for(AsyncSession.sync_session_class, "after_rollback")
def clear_deferred_events_after_rollback(session: Session) -> None:
    """
    Clear deferred events after transaction rollback.

    Events are discarded since the associated database changes
    were rolled back and should not be published.

    Args:
        session: SQLAlchemy session that was rolled back
    """
    from shared.messaging import deferred_publisher  # noqa: PLC0415

    deferred_events = deferred_publisher.DeferredEventPublisher.get_deferred_events(session)

    if deferred_events:
        logger.info("Discarding %d deferred events after rollback", len(deferred_events))
        deferred_publisher.DeferredEventPublisher.clear_deferred_events(session)
