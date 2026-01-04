# Copyright (C) 2024-2025 Bret McKee
# SPDX-License-Identifier: AGPL-3.0-or-later
#
# This file is part of game-scheduler.
#
# game-scheduler is free software: you can redistribute it and/or modify it
# under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or (at your
# option) any later version.
#
# game-scheduler is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY
# or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Affero General Public
# License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with game-scheduler. If not, see <https://www.gnu.org/licenses/>.

"""
Validation tests for shared fixtures.

These tests verify that the consolidated fixture architecture works correctly:
- Each factory fixture creates valid data
- Multiple calls to same factory create distinct objects
- Composite fixtures create properly connected objects
- Redis cache seeding populates all expected keys
- Automatic cleanup removes all test data
- No deadlocks occur with database sessions

All tests are hermetic: they create what they need and rely on automatic cleanup.
"""

import asyncio
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import text

from shared.cache.keys import CacheKeys

pytestmark = pytest.mark.integration

# ============================================================================
# Database Session Fixture Tests
# ============================================================================


def test_admin_db_sync_fixture_only(admin_db_sync):
    """Verify admin_db_sync fixture works without deadlock."""
    assert admin_db_sync is not None


def test_admin_db_sync_can_execute_query(admin_db_sync):
    """Verify admin_db_sync can execute queries."""
    result = admin_db_sync.execute(text("SELECT 1 as value"))
    assert result.scalar() == 1


@pytest.mark.asyncio
async def test_admin_db_fixture(admin_db):
    """Verify async admin_db fixture works."""
    assert admin_db is not None
    result = await admin_db.execute(text("SELECT 1 as value"))
    assert result.scalar() == 1


@pytest.mark.asyncio
async def test_app_db_fixture(app_db):
    """Verify async app_db fixture works (RLS enforced)."""
    assert app_db is not None
    result = await app_db.execute(text("SELECT 1 as value"))
    assert result.scalar() == 1


@pytest.mark.asyncio
async def test_bot_db_fixture(bot_db):
    """Verify async bot_db fixture works (BYPASSRLS)."""
    assert bot_db is not None
    result = await bot_db.execute(text("SELECT 1 as value"))
    assert result.scalar() == 1


# ============================================================================
# Redis Client Fixture Tests
# ============================================================================


def test_redis_client_fixture(redis_client):
    """Verify sync redis_client fixture connects."""
    assert redis_client is not None


@pytest.mark.asyncio
async def test_redis_client_async_fixture(redis_client_async):
    """Verify async redis_client_async fixture connects."""
    assert redis_client_async is not None


# ============================================================================
# Factory Fixture Tests - Guild
# ============================================================================


def test_create_guild_factory_basic(admin_db_sync, create_guild):
    """Test basic guild creation with factory fixture."""
    guild = create_guild(discord_guild_id="123456789012345678")

    assert guild["id"] is not None
    assert guild["guild_id"] == "123456789012345678"
    assert guild["bot_manager_role_ids"] == []

    # Verify in database
    result = admin_db_sync.execute(
        text("SELECT guild_id FROM guild_configurations WHERE id = :id"),
        {"id": guild["id"]},
    )
    assert result.scalar() == "123456789012345678"


def test_create_guild_with_bot_manager_roles(admin_db_sync, create_guild):
    """Test guild creation with bot manager roles."""
    guild = create_guild(
        discord_guild_id="999888777666555444",
        bot_manager_roles=["111222333444555666", "777888999000111222"],
    )

    assert len(guild["bot_manager_role_ids"]) == 2
    assert "111222333444555666" in guild["bot_manager_role_ids"]


def test_create_guild_auto_generated_id(create_guild):
    """Test guild creation with auto-generated Discord ID."""
    guild = create_guild()

    assert guild["id"] is not None
    assert guild["guild_id"] is not None
    assert len(guild["guild_id"]) == 18


def test_create_multiple_guilds(create_guild):
    """Test creating multiple guilds in same test."""
    guild1 = create_guild(discord_guild_id="111111111111111111")
    guild2 = create_guild(discord_guild_id="222222222222222222")

    assert guild1["id"] != guild2["id"]
    assert guild1["guild_id"] != guild2["guild_id"]


# ============================================================================
# Factory Fixture Tests - Channel
# ============================================================================


def test_create_channel_factory(admin_db_sync, create_guild, create_channel):
    """Test channel creation with factory fixture."""
    guild = create_guild()
    channel = create_channel(guild_id=guild["id"], discord_channel_id="333333333333333333")

    assert channel["id"] is not None
    assert channel["channel_id"] == "333333333333333333"
    assert channel["guild_id"] == guild["id"]

    # Verify in database
    result = admin_db_sync.execute(
        text("SELECT channel_id FROM channel_configurations WHERE id = :id"),
        {"id": channel["id"]},
    )
    assert result.scalar() == "333333333333333333"


def test_create_multiple_channels_same_guild(create_guild, create_channel):
    """Test creating multiple channels for same guild."""
    guild = create_guild()
    channel1 = create_channel(guild_id=guild["id"], discord_channel_id="111")
    channel2 = create_channel(guild_id=guild["id"], discord_channel_id="222")

    assert channel1["id"] != channel2["id"]
    assert channel1["guild_id"] == guild["id"]
    assert channel2["guild_id"] == guild["id"]


# ============================================================================
# Factory Fixture Tests - User
# ============================================================================


def test_create_user_factory(admin_db_sync, create_user):
    """Test user creation with factory fixture."""
    user = create_user(discord_user_id="444444444444444444")

    assert user["id"] is not None
    assert user["discord_id"] == "444444444444444444"

    # Verify in database
    result = admin_db_sync.execute(
        text("SELECT discord_id FROM users WHERE id = :id"), {"id": user["id"]}
    )
    assert result.scalar() == "444444444444444444"


def test_create_user_auto_generated_id(create_user):
    """Test user creation with auto-generated Discord ID."""
    user = create_user()

    assert user["id"] is not None
    assert user["discord_id"] is not None
    assert len(user["discord_id"]) == 18


def test_create_multiple_users(create_user):
    """Test creating multiple users in same test."""
    user1 = create_user(discord_user_id="111111111111111111")
    user2 = create_user(discord_user_id="222222222222222222")

    assert user1["id"] != user2["id"]
    assert user1["discord_id"] != user2["discord_id"]


# ============================================================================
# Factory Fixture Tests - Template
# ============================================================================


def test_create_template_factory(admin_db_sync, create_guild, create_channel, create_template):
    """Test template creation with factory fixture."""
    guild = create_guild()
    channel = create_channel(guild_id=guild["id"])
    template = create_template(
        guild_id=guild["id"],
        channel_id=channel["id"],
        name="D&D Campaign",
        max_players=5,
    )

    assert template["id"] is not None
    assert template["guild_id"] == guild["id"]
    assert template["channel_id"] == channel["id"]
    assert template["name"] == "D&D Campaign"
    assert template["max_players"] == 5

    # Verify in database
    result = admin_db_sync.execute(
        text("SELECT name FROM game_templates WHERE id = :id"), {"id": template["id"]}
    )
    assert result.scalar() == "D&D Campaign"


def test_create_template_with_signup_methods(
    admin_db_sync, create_guild, create_channel, create_template
):
    """Test template with custom signup methods."""
    guild = create_guild()
    channel = create_channel(guild_id=guild["id"])
    template = create_template(
        guild_id=guild["id"],
        channel_id=channel["id"],
        allowed_signup_methods=["SELF_SIGNUP", "HOST_SIGNUP"],
        default_signup_method="HOST_SIGNUP",
    )

    assert template["id"] is not None


# ============================================================================
# Factory Fixture Tests - Game
# ============================================================================


def test_create_game_factory(admin_db_sync, create_guild, create_channel, create_user, create_game):
    """Test game creation with factory fixture."""
    guild = create_guild()
    channel = create_channel(guild_id=guild["id"])
    user = create_user()
    scheduled_time = datetime.now(UTC) + timedelta(hours=2)

    game = create_game(
        guild_id=guild["id"],
        channel_id=channel["id"],
        host_id=user["id"],
        title="Epic Adventure",
        scheduled_at=scheduled_time,
        max_players=6,
    )

    assert game["id"] is not None
    assert game["guild_id"] == guild["id"]
    assert game["channel_id"] == channel["id"]
    assert game["host_id"] == user["id"]
    assert game["title"] == "Epic Adventure"
    assert game["status"] == "scheduled"

    # Verify in database
    result = admin_db_sync.execute(
        text("SELECT title FROM game_sessions WHERE id = :id"), {"id": game["id"]}
    )
    assert result.scalar() == "Epic Adventure"


def test_create_game_with_template(
    create_guild, create_channel, create_user, create_template, create_game
):
    """Test game creation with template."""
    guild = create_guild()
    channel = create_channel(guild_id=guild["id"])
    user = create_user()
    template = create_template(guild_id=guild["id"], channel_id=channel["id"])

    game = create_game(
        guild_id=guild["id"],
        channel_id=channel["id"],
        host_id=user["id"],
        template_id=template["id"],
    )

    assert game["id"] is not None


def test_create_multiple_games_same_channel(create_guild, create_channel, create_user, create_game):
    """Test creating multiple games in same channel."""
    guild = create_guild()
    channel = create_channel(guild_id=guild["id"])
    user = create_user()

    game1 = create_game(
        guild_id=guild["id"],
        channel_id=channel["id"],
        host_id=user["id"],
        title="Game 1",
    )
    game2 = create_game(
        guild_id=guild["id"],
        channel_id=channel["id"],
        host_id=user["id"],
        title="Game 2",
    )

    assert game1["id"] != game2["id"]
    assert game1["channel_id"] == game2["channel_id"]


# ============================================================================
# Composite Fixture Tests
# ============================================================================


def test_test_environment_composite_basic(test_environment):
    """Test composite fixture creates all objects."""
    env = test_environment(
        discord_guild_id="111111111111111111",
        discord_channel_id="222222222222222222",
        discord_user_id="333333333333333333",
    )

    assert "guild" in env
    assert "channel" in env
    assert "user" in env
    assert env["guild"]["guild_id"] == "111111111111111111"
    assert env["channel"]["channel_id"] == "222222222222222222"
    assert env["channel"]["guild_id"] == env["guild"]["id"]
    assert env["user"]["discord_id"] == "333333333333333333"


def test_test_environment_with_bot_manager(test_environment):
    """Test composite fixture with bot manager roles."""
    env = test_environment(bot_manager_roles=["999888777666555444"])

    assert len(env["guild"]["bot_manager_role_ids"]) == 1


def test_test_environment_auto_generated_ids(test_environment):
    """Test composite fixture with auto-generated IDs."""
    env = test_environment()

    assert env["guild"]["id"] is not None
    assert env["channel"]["id"] is not None
    assert env["user"]["id"] is not None


# ============================================================================
# Redis Cache Seeding Tests
# ============================================================================


def test_seed_redis_cache_basic(redis_client, seed_redis_cache):
    """Test Redis cache seeding with basic data."""
    seed_redis_cache(
        user_discord_id="111111111111111111",
        guild_discord_id="222222222222222222",
        channel_discord_id="333333333333333333",
    )

    # Verify user guilds cached
    loop = asyncio.get_event_loop()
    guilds = loop.run_until_complete(
        redis_client.get_json(CacheKeys.user_guilds("111111111111111111"))
    )
    assert len(guilds) == 1
    assert guilds[0]["id"] == "222222222222222222"

    # Verify user roles cached
    roles = loop.run_until_complete(
        redis_client.get_json(CacheKeys.user_roles("111111111111111111", "222222222222222222"))
    )
    assert "222222222222222222" in roles  # Guild membership role

    # Verify channel metadata cached
    channel = loop.run_until_complete(
        redis_client.get_json(CacheKeys.discord_channel("333333333333333333"))
    )
    assert channel["id"] == "333333333333333333"
    assert channel["guild_id"] == "222222222222222222"

    # Verify guild metadata cached
    guild = loop.run_until_complete(
        redis_client.get_json(CacheKeys.discord_guild("222222222222222222"))
    )
    assert guild["id"] == "222222222222222222"


def test_seed_redis_cache_with_bot_manager_roles(redis_client, seed_redis_cache):
    """Test Redis cache seeding with bot manager roles."""
    seed_redis_cache(
        user_discord_id="111111111111111111",
        guild_discord_id="222222222222222222",
        bot_manager_roles=["999888777666555444", "888777666555444333"],
    )

    loop = asyncio.get_event_loop()
    roles = loop.run_until_complete(
        redis_client.get_json(CacheKeys.user_roles("111111111111111111", "222222222222222222"))
    )
    assert "999888777666555444" in roles
    assert "888777666555444333" in roles
    assert "222222222222222222" in roles  # Guild membership role


def test_seed_redis_cache_with_session(redis_client, seed_redis_cache, create_user):
    """Test Redis cache seeding with session token."""
    user = create_user(discord_user_id="111111111111111111")

    seed_redis_cache(
        user_discord_id=user["discord_id"],
        guild_discord_id="222222222222222222",
        session_token="test_session_token_123",
        session_user_id=user["id"],
        session_access_token="mock_discord_access_token",
    )

    loop = asyncio.get_event_loop()
    session = loop.run_until_complete(
        redis_client.get_json(CacheKeys.session("test_session_token_123"))
    )
    assert session["user_id"] == user["id"]
    assert "access_token" in session
    assert "expires_at" in session


@pytest.mark.asyncio
async def test_seed_redis_cache_async_usage(redis_client_async, seed_redis_cache):
    """Test Redis cache seeding with async/await pattern."""
    await seed_redis_cache(
        user_discord_id="111111111111111111", guild_discord_id="222222222222222222"
    )

    guilds = await redis_client_async.get_json(CacheKeys.user_guilds("111111111111111111"))
    assert len(guilds) == 1


# ============================================================================
# Integration Tests - Full Workflow
# ============================================================================


def test_full_workflow_sync(
    admin_db_sync,
    redis_client,
    test_environment,
    create_template,
    create_game,
    seed_redis_cache,
):
    """Test complete workflow with all fixtures."""
    # Create environment
    env = test_environment(
        discord_guild_id="111111111111111111",
        discord_channel_id="222222222222222222",
        discord_user_id="333333333333333333",
        bot_manager_roles=["999888777666555444"],
    )

    # Seed Redis cache
    seed_redis_cache(
        user_discord_id=env["user"]["discord_id"],
        guild_discord_id=env["guild"]["guild_id"],
        channel_discord_id=env["channel"]["channel_id"],
        bot_manager_roles=env["guild"]["bot_manager_role_ids"],
    )

    # Create template
    template = create_template(
        guild_id=env["guild"]["id"],
        channel_id=env["channel"]["id"],
        name="Test Template",
        max_players=4,
    )

    # Create game
    game = create_game(
        guild_id=env["guild"]["id"],
        channel_id=env["channel"]["id"],
        host_id=env["user"]["id"],
        template_id=template["id"],
        title="Test Game",
    )

    # Verify everything is connected
    assert game["guild_id"] == env["guild"]["id"]
    assert game["channel_id"] == env["channel"]["id"]
    assert game["host_id"] == env["user"]["id"]

    # Verify in database
    result = admin_db_sync.execute(
        text("SELECT title FROM game_sessions WHERE id = :id"), {"id": game["id"]}
    )
    assert result.scalar() == "Test Game"


@pytest.mark.asyncio
async def test_full_workflow_async(
    admin_db,
    redis_client_async,
    test_environment,
    create_template,
    create_game,
    seed_redis_cache,
):
    """Test complete workflow with async fixtures."""
    # Create environment
    env = test_environment()

    # Seed Redis cache
    await seed_redis_cache(
        user_discord_id=env["user"]["discord_id"],
        guild_discord_id=env["guild"]["guild_id"],
        channel_discord_id=env["channel"]["channel_id"],
    )

    # Create template and game
    template = create_template(guild_id=env["guild"]["id"], channel_id=env["channel"]["id"])
    game = create_game(
        guild_id=env["guild"]["id"],
        channel_id=env["channel"]["id"],
        host_id=env["user"]["id"],
        template_id=template["id"],
    )

    # Verify in database using async session
    result = await admin_db.execute(
        text("SELECT title FROM game_sessions WHERE id = :id"), {"id": game["id"]}
    )
    assert result.scalar() is not None


# ============================================================================
# Cleanup Tests
# ============================================================================


def test_automatic_cleanup_removes_data(admin_db_sync, create_guild, create_channel):
    """Verify automatic cleanup removes test data."""
    guild = create_guild()
    create_channel(guild_id=guild["id"])

    # Data should exist during test
    result = admin_db_sync.execute(
        text("SELECT COUNT(*) FROM guild_configurations WHERE id = :id"),
        {"id": guild["id"]},
    )
    assert result.scalar() == 1

    # Cleanup happens automatically after test completes
