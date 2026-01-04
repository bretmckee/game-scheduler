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


"""Shared fixtures for integration tests."""

import os
import uuid
from datetime import UTC, datetime, timedelta

import pika
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from services.api.auth.tokens import encrypt_token
from shared.cache.client import RedisClient
from shared.cache.keys import CacheKeys
from shared.data_access.guild_isolation import clear_current_guild_ids
from shared.database import engine
from shared.models.channel import ChannelConfiguration
from shared.models.game import GameSession, GameStatus
from shared.models.guild import GuildConfiguration
from shared.models.template import GameTemplate
from shared.models.user import User


@pytest.fixture(scope="module")
def rabbitmq_url():
    """Get RabbitMQ URL from environment."""
    return os.getenv("RABBITMQ_URL", "amqp://guest:guest@rabbitmq:5672/")


@pytest.fixture
def rabbitmq_connection(rabbitmq_url):
    """Create RabbitMQ connection for test setup/assertions."""
    connection = pika.BlockingConnection(pika.URLParameters(rabbitmq_url))
    yield connection
    connection.close()


@pytest.fixture
def rabbitmq_channel(rabbitmq_connection):
    """Create RabbitMQ channel for test operations."""
    channel = rabbitmq_connection.channel()
    yield channel
    channel.close()


@pytest.fixture(autouse=True, scope="function")
async def cleanup_guild_context():
    """Ensure guild context is cleared before and after each test."""
    clear_current_guild_ids()
    yield
    clear_current_guild_ids()


@pytest.fixture(autouse=True, scope="function")
async def cleanup_db_engine():
    """
    Dispose database engine after each test to prevent event loop issues.

    Ensures connection pool is cleared between tests so connections
    don't get reused across different event loops in pytest-asyncio.
    """
    yield
    await engine.dispose()


@pytest.fixture(scope="session")
def db_url():
    """Get database URL from environment for async operations."""
    raw_url = os.getenv(
        "DATABASE_URL",
        "postgresql://gamebot:dev_password_change_in_prod@postgres:5432/game_scheduler",
    )
    return raw_url.replace("postgresql://", "postgresql+asyncpg://")


@pytest.fixture(scope="session")
def admin_db_url():
    """Get admin database URL from environment for fixture creation (bypasses all restrictions)."""
    raw_url = os.getenv(
        "ADMIN_DATABASE_URL",
        "postgresql://gamebot_admin:integration_admin_password@postgres:5432/game_scheduler_integration",
    )
    return raw_url.replace("postgresql://", "postgresql+asyncpg://")


@pytest.fixture
async def async_engine(db_url):
    """Create async engine for integration tests."""
    engine_instance = create_async_engine(db_url, echo=False)
    yield engine_instance
    await engine_instance.dispose()


@pytest.fixture
async def admin_async_engine(admin_db_url):
    """Create async engine using admin user (superuser, bypasses all restrictions)
    for fixture creation.
    """
    engine_instance = create_async_engine(admin_db_url, echo=False)
    yield engine_instance
    await engine_instance.dispose()


@pytest.fixture
def async_session_factory(async_engine):
    """Create session factory for integration tests."""
    return async_sessionmaker(
        async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )


@pytest.fixture
def admin_async_session_factory(admin_async_engine):
    """Create session factory using admin user (superuser) for fixtures."""
    return async_sessionmaker(
        admin_async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )


@pytest.fixture
async def db(async_session_factory):
    """Provide async database session with automatic rollback after test."""
    async with async_session_factory() as session:
        yield session
        await session.rollback()


@pytest.fixture
async def admin_db(admin_async_session_factory):
    """Provide async database session using admin user (superuser) for fixture creation."""
    async with admin_async_session_factory() as session:
        yield session
        await session.rollback()


@pytest.fixture
async def redis_client():
    """Provide Redis client for cache operations."""
    client = RedisClient()
    await client.connect()
    yield client
    await client.disconnect()


async def seed_user_guilds_cache(
    redis_client: RedisClient, user_discord_id: str, guild_ids: list[str]
):
    """
    Seed Redis cache with user guilds to bypass Discord API calls.

    Required for Phase 2 guild isolation where _get_game_service fetches user guilds.
    This allows integration tests to work without valid Discord OAuth tokens.

    Args:
        redis_client: Redis client instance
        user_discord_id: Discord user ID
        guild_ids: List of guild Discord IDs the user should have access to
    """

    user_guilds_key = CacheKeys.user_guilds(user_discord_id)
    guilds_data = [
        {
            "id": guild_id,
            "name": f"Test Guild {guild_id[:8]}",
            "permissions": "2147483647",
        }
        for guild_id in guild_ids
    ]
    await redis_client.set_json(user_guilds_key, guilds_data, ttl=300)


async def seed_user_session(
    redis_client: RedisClient,
    session_token: str,
    user_id: str,
    access_token: str,
):
    """
    Seed Redis cache with user session for token validation.

    Allows integration tests to bypass actual OAuth login flow.

    Args:
        redis_client: Redis client instance
        session_token: Session token to create
        user_id: User UUID
        access_token: Access token to store (will be encrypted)
    """

    session_key = f"session:{session_token}"
    session_data = {
        "user_id": user_id,
        "access_token": encrypt_token(access_token),
        "refresh_token": encrypt_token("mock_refresh_token"),
        "expires_at": (datetime.now(UTC) + timedelta(hours=1)).isoformat(),
    }
    await redis_client.set_json(session_key, session_data, ttl=3600)


@pytest.fixture
def guild_a_id():
    """Guild A UUID for multi-guild testing - unique per test."""
    return str(uuid.uuid4())


@pytest.fixture
def guild_b_id():
    """Guild B UUID for multi-guild testing - unique per test."""
    return str(uuid.uuid4())


@pytest.fixture
async def guild_a_config(admin_db, guild_a_id):
    """Create GuildConfiguration for guild A using admin user (superuser)."""
    guild_config = GuildConfiguration(
        id=guild_a_id,
        guild_id=str(uuid.uuid4())[:18],
    )
    admin_db.add(guild_config)
    await admin_db.commit()
    return guild_config


@pytest.fixture
async def guild_b_config(admin_db, guild_b_id):
    """Create GuildConfiguration for guild B using admin user (superuser)."""
    guild_config = GuildConfiguration(
        id=guild_b_id,
        guild_id=str(uuid.uuid4())[:18],
    )
    admin_db.add(guild_config)
    await admin_db.commit()
    return guild_config


@pytest.fixture
async def channel_a(admin_db, guild_a_id, guild_a_config):
    """Test channel for guild A."""
    channel = ChannelConfiguration(
        id=str(uuid.uuid4()),
        guild_id=guild_a_id,
        channel_id=str(uuid.uuid4())[:18],
        is_active=True,
    )
    admin_db.add(channel)
    await admin_db.commit()
    return channel


@pytest.fixture
async def channel_b(admin_db, guild_b_id, guild_b_config):
    """Test channel for guild B."""
    channel = ChannelConfiguration(
        id=str(uuid.uuid4()),
        guild_id=guild_b_id,
        channel_id=str(uuid.uuid4())[:18],
        is_active=True,
    )
    admin_db.add(channel)
    await admin_db.commit()
    return channel


@pytest.fixture
async def template_a(admin_db, guild_a_id, channel_a):
    """Test template for guild A."""
    template = GameTemplate(
        id=str(uuid.uuid4()),
        guild_id=guild_a_id,
        channel_id=channel_a.id,
        name="Template A",
        description="Test template for guild A",
        order=0,
        is_default=True,
        max_players=4,
    )
    admin_db.add(template)
    await admin_db.commit()
    return template


@pytest.fixture
async def template_b(admin_db, guild_b_id, channel_b):
    """Test template for guild B."""
    template = GameTemplate(
        id=str(uuid.uuid4()),
        guild_id=guild_b_id,
        channel_id=channel_b.id,
        name="Template B",
        description="Test template for guild B",
        order=0,
        is_default=True,
        max_players=4,
    )
    admin_db.add(template)
    await admin_db.commit()
    return template


@pytest.fixture
async def user_a(admin_db):
    """Test user for guild A scenarios."""
    user = User(
        id=str(uuid.uuid4()),
        discord_id=str(uuid.uuid4())[:18],
    )
    admin_db.add(user)
    await admin_db.commit()
    return user


@pytest.fixture
async def user_b(admin_db):
    """Test user for guild B scenarios."""
    user = User(
        id=str(uuid.uuid4()),
        discord_id=str(uuid.uuid4())[:18],
    )
    admin_db.add(user)
    await admin_db.commit()
    return user


@pytest.fixture
async def game_a(admin_db, guild_a_id, channel_a, template_a, user_a):
    """Test game in guild A."""
    game = GameSession(
        id=str(uuid.uuid4()),
        guild_id=guild_a_id,
        channel_id=channel_a.id,
        template_id=template_a.id,
        host_id=user_a.id,
        title="Game A",
        description="Test game in guild A",
        scheduled_at=datetime.now(UTC).replace(tzinfo=None) + timedelta(days=1),
        max_players=4,
        status=GameStatus.SCHEDULED,
    )
    admin_db.add(game)
    await admin_db.commit()
    return game


@pytest.fixture
async def game_b(admin_db, guild_b_id, channel_b, template_b, user_b):
    """Test game in guild B."""
    game = GameSession(
        id=str(uuid.uuid4()),
        guild_id=guild_b_id,
        channel_id=channel_b.id,
        template_id=template_b.id,
        host_id=user_b.id,
        title="Game B",
        description="Test game in guild B",
        scheduled_at=datetime.now(UTC).replace(tzinfo=None) + timedelta(days=1),
        max_players=4,
        status=GameStatus.SCHEDULED,
    )
    admin_db.add(game)
    await admin_db.commit()
    return game
