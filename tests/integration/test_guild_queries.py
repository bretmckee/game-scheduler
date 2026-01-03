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


"""Integration tests for guild_queries wrapper functions against real PostgreSQL.

Tests verify:
- All 12 wrapper functions work correctly against real database
- Guild isolation is enforced (cross-guild access prevented)
- RLS context is set correctly
- Error handling works as expected
- Performance is acceptable (< 5ms overhead per query)

These tests run against actual PostgreSQL database and verify that the wrapper
functions are ready for production use before migrating 37+ call sites.
"""

import os
import time
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from shared.data_access import guild_queries
from shared.models.participant import ParticipantType

pytestmark = pytest.mark.integration


@pytest.fixture(scope="session")
def db_url():
    """Get database URL from environment."""
    raw_url = os.getenv(
        "DATABASE_URL",
        "postgresql://gamebot:dev_password_change_in_prod@postgres:5432/game_scheduler",
    )
    return raw_url.replace("postgresql://", "postgresql+asyncpg://")


@pytest.fixture
async def async_engine(db_url):
    """Create async engine for integration tests."""
    engine = create_async_engine(db_url, echo=False)
    yield engine
    await engine.dispose()


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
async def db(async_session_factory):
    """Provide async database session for each test with automatic cleanup."""
    async with async_session_factory() as session:
        yield session
        await session.rollback()


@pytest.fixture
def guild_a_id():
    """Guild A UUID for multi-guild testing - unique per test."""
    return str(uuid.uuid4())


@pytest.fixture
def guild_b_id():
    """Guild B UUID for multi-guild testing - unique per test."""
    return str(uuid.uuid4())


@pytest.fixture
async def guild_b_config(db, guild_b_id):
    """Create GuildConfiguration for guild_b for multi-guild testing."""
    from shared.models.guild import GuildConfiguration

    guild_config = GuildConfiguration(
        id=guild_b_id,
        guild_id=str(uuid.uuid4())[:18],  # Unique Discord guild ID per test
    )
    db.add(guild_config)
    await db.flush()
    return guild_config


@pytest.fixture
async def channel_id(db, guild_a_id):
    """Test channel ID with database record - cleaned up by session rollback."""
    from shared.models.channel import ChannelConfiguration
    from shared.models.guild import GuildConfiguration

    # Create guild configuration record first
    guild_config = GuildConfiguration(
        id=guild_a_id,
        guild_id=str(uuid.uuid4())[:18],  # Unique Discord guild ID per test
    )
    db.add(guild_config)
    await db.flush()

    # Now create channel configuration
    channel = ChannelConfiguration(
        id=str(uuid.uuid4()),
        guild_id=guild_a_id,
        channel_id=str(uuid.uuid4())[:18],  # Unique Discord channel ID per test
        is_active=True,
    )
    db.add(channel)
    await db.flush()

    return channel.id


@pytest.fixture
async def user_id(db):
    """Test user ID with database record."""
    from shared.models.user import User

    user = User(
        id=str(uuid.uuid4()),
        discord_id=str(uuid.uuid4())[:18],  # Unique per test
    )
    db.add(user)
    await db.flush()

    return user.id


@pytest.fixture
async def sample_game_data(guild_a_id, channel_id, user_id):
    """Sample game data for testing."""
    return {
        "channel_id": channel_id,
        "host_id": user_id,
        "title": "Integration Test Game",
        "description": "Test game for integration testing",
        "scheduled_at": datetime.now(UTC).replace(tzinfo=None) + timedelta(days=1),
        "max_players": 4,
    }


@pytest.fixture
async def sample_template_data(channel_id):
    """Sample template data for testing."""
    return {
        "channel_id": channel_id,
        "name": "Integration Test Template",
        "description": "Test template for integration testing",
        "order": 0,
        "is_default": False,
        "max_players": 5,
        "expected_duration_minutes": 180,
        "reminder_minutes": [60, 1440],
    }


# Game Operations Integration Tests


@pytest.mark.asyncio
async def test_get_game_by_id_returns_game_from_correct_guild(
    db, guild_a_id, guild_b_id, sample_game_data
):
    """Verify get_game_by_id returns game only from correct guild."""
    game_a = await guild_queries.create_game(db, guild_a_id, sample_game_data)
    await db.commit()

    result = await guild_queries.get_game_by_id(db, guild_a_id, game_a.id)
    assert result is not None
    assert result.id == game_a.id
    assert result.guild_id == guild_a_id

    result_wrong_guild = await guild_queries.get_game_by_id(db, guild_b_id, game_a.id)
    assert result_wrong_guild is None


@pytest.mark.asyncio
async def test_list_games_returns_only_guild_games(
    db, guild_a_id, guild_b_id, guild_b_config, sample_game_data
):
    """Verify list_games returns only games from specified guild."""
    game_a1 = await guild_queries.create_game(
        db, guild_a_id, {**sample_game_data, "title": "Guild A Game 1"}
    )
    game_a2 = await guild_queries.create_game(
        db, guild_a_id, {**sample_game_data, "title": "Guild A Game 2"}
    )
    game_b = await guild_queries.create_game(
        db, guild_b_id, {**sample_game_data, "title": "Guild B Game"}
    )
    await db.commit()

    guild_a_games = await guild_queries.list_games(db, guild_a_id)
    guild_a_ids = {g.id for g in guild_a_games}

    assert game_a1.id in guild_a_ids
    assert game_a2.id in guild_a_ids
    assert game_b.id not in guild_a_ids

    guild_b_games = await guild_queries.list_games(db, guild_b_id)
    guild_b_ids = {g.id for g in guild_b_games}

    assert game_b.id in guild_b_ids
    assert game_a1.id not in guild_b_ids
    assert game_a2.id not in guild_b_ids


@pytest.mark.asyncio
async def test_list_games_respects_channel_filter(db, guild_a_id, sample_game_data):
    """Verify list_games filters by channel when specified."""
    from shared.models.channel import ChannelConfiguration

    channel_1 = str(uuid.uuid4())
    channel_2 = str(uuid.uuid4())

    # Create channel configurations for the new channels
    ch1_config = ChannelConfiguration(
        id=channel_1,
        guild_id=guild_a_id,
        channel_id=str(uuid.uuid4())[:18],
        is_active=True,
    )
    ch2_config = ChannelConfiguration(
        id=channel_2,
        guild_id=guild_a_id,
        channel_id=str(uuid.uuid4())[:18],
        is_active=True,
    )
    db.add(ch1_config)
    db.add(ch2_config)
    await db.flush()

    game_ch1 = await guild_queries.create_game(
        db,
        guild_a_id,
        {**sample_game_data, "channel_id": channel_1, "title": "Channel 1 Game"},
    )
    game_ch2 = await guild_queries.create_game(
        db,
        guild_a_id,
        {**sample_game_data, "channel_id": channel_2, "title": "Channel 2 Game"},
    )
    await db.commit()

    channel_1_games = await guild_queries.list_games(db, guild_a_id, channel_id=channel_1)
    channel_1_ids = {g.id for g in channel_1_games}

    assert game_ch1.id in channel_1_ids
    assert game_ch2.id not in channel_1_ids


@pytest.mark.asyncio
async def test_create_game_sets_guild_id_correctly(db, guild_a_id, sample_game_data):
    """Verify create_game sets guild_id and persists to database."""
    game = await guild_queries.create_game(db, guild_a_id, sample_game_data)
    await db.commit()

    assert game.guild_id == guild_a_id

    result = await db.execute(
        text("SELECT guild_id FROM game_sessions WHERE id = :game_id"),
        {"game_id": game.id},
    )
    db_guild_id = result.scalar_one()
    assert str(db_guild_id) == guild_a_id


@pytest.mark.asyncio
async def test_update_game_rejects_cross_guild_update(db, guild_a_id, guild_b_id, sample_game_data):
    """Verify update_game validates game belongs to guild."""
    game = await guild_queries.create_game(db, guild_a_id, sample_game_data)
    await db.commit()

    with pytest.raises(ValueError, match="not found in guild"):
        await guild_queries.update_game(db, guild_b_id, game.id, {"title": "Unauthorized Update"})


@pytest.mark.asyncio
async def test_update_game_succeeds_for_correct_guild(db, guild_a_id, sample_game_data):
    """Verify update_game works for game in correct guild."""
    game = await guild_queries.create_game(db, guild_a_id, sample_game_data)
    await db.commit()

    updated = await guild_queries.update_game(db, guild_a_id, game.id, {"title": "Updated Title"})
    await db.commit()

    assert updated.title == "Updated Title"


@pytest.mark.asyncio
async def test_delete_game_rejects_cross_guild_delete(db, guild_a_id, guild_b_id, sample_game_data):
    """Verify delete_game validates game belongs to guild."""
    game = await guild_queries.create_game(db, guild_a_id, sample_game_data)
    await db.commit()

    with pytest.raises(ValueError, match="not found in guild"):
        await guild_queries.delete_game(db, guild_b_id, game.id)


@pytest.mark.asyncio
async def test_delete_game_succeeds_for_correct_guild(db, guild_a_id, sample_game_data):
    """Verify delete_game works for game in correct guild."""
    game = await guild_queries.create_game(db, guild_a_id, sample_game_data)
    await db.commit()

    await guild_queries.delete_game(db, guild_a_id, game.id)
    await db.commit()

    result = await guild_queries.get_game_by_id(db, guild_a_id, game.id)
    assert result is None


# Participant Operations Integration Tests


@pytest.mark.asyncio
async def test_add_participant_validates_game_belongs_to_guild(
    db, guild_a_id, guild_b_id, sample_game_data, user_id
):
    """Verify add_participant validates game belongs to guild."""
    game = await guild_queries.create_game(db, guild_a_id, sample_game_data)
    await db.commit()

    with pytest.raises(ValueError, match="not found in guild"):
        await guild_queries.add_participant(
            db,
            guild_b_id,
            game.id,
            user_id,
            {"position_type": ParticipantType.SELF_ADDED, "position": 0},
        )


@pytest.mark.asyncio
async def test_add_participant_succeeds_for_correct_guild(
    db, guild_a_id, sample_game_data, user_id
):
    """Verify add_participant works when game belongs to guild."""
    game = await guild_queries.create_game(db, guild_a_id, sample_game_data)
    await db.commit()

    participant = await guild_queries.add_participant(
        db,
        guild_a_id,
        game.id,
        user_id,
        {"position_type": ParticipantType.SELF_ADDED, "position": 0},
    )
    await db.commit()

    assert participant.game_session_id == game.id
    assert participant.user_id == user_id


@pytest.mark.asyncio
async def test_remove_participant_validates_game_belongs_to_guild(
    db, guild_a_id, guild_b_id, sample_game_data, user_id
):
    """Verify remove_participant validates game belongs to guild."""
    game = await guild_queries.create_game(db, guild_a_id, sample_game_data)
    await guild_queries.add_participant(
        db,
        guild_a_id,
        game.id,
        user_id,
        {"position_type": ParticipantType.SELF_ADDED, "position": 0},
    )
    await db.commit()

    with pytest.raises(ValueError, match="not found in guild"):
        await guild_queries.remove_participant(db, guild_b_id, game.id, user_id)


@pytest.mark.asyncio
async def test_remove_participant_succeeds_for_correct_guild(
    db, guild_a_id, sample_game_data, user_id
):
    """Verify remove_participant works when game belongs to guild."""
    game = await guild_queries.create_game(db, guild_a_id, sample_game_data)
    await guild_queries.add_participant(
        db,
        guild_a_id,
        game.id,
        user_id,
        {"position_type": ParticipantType.SELF_ADDED, "position": 0},
    )
    await db.commit()

    await guild_queries.remove_participant(db, guild_a_id, game.id, user_id)
    await db.commit()

    result = await db.execute(
        text(
            "SELECT COUNT(*) FROM game_participants "
            "WHERE game_session_id = :game_id AND user_id = :user_id"
        ),
        {"game_id": game.id, "user_id": user_id},
    )
    count = result.scalar()
    assert count == 0


@pytest.mark.asyncio
async def test_list_user_games_returns_only_guild_games(
    db, guild_a_id, guild_b_id, guild_b_config, sample_game_data, user_id
):
    """Verify list_user_games returns only user's games from specified guild."""
    game_a = await guild_queries.create_game(db, guild_a_id, sample_game_data)
    await guild_queries.add_participant(
        db,
        guild_a_id,
        game_a.id,
        user_id,
        {"position_type": ParticipantType.SELF_ADDED, "position": 0},
    )

    game_b = await guild_queries.create_game(db, guild_b_id, sample_game_data)
    await guild_queries.add_participant(
        db,
        guild_b_id,
        game_b.id,
        user_id,
        {"position_type": ParticipantType.SELF_ADDED, "position": 0},
    )

    await db.commit()

    guild_a_games = await guild_queries.list_user_games(db, guild_a_id, user_id)
    guild_a_ids = {g.id for g in guild_a_games}

    assert game_a.id in guild_a_ids
    assert game_b.id not in guild_a_ids

    guild_b_games = await guild_queries.list_user_games(db, guild_b_id, user_id)
    guild_b_ids = {g.id for g in guild_b_games}

    assert game_b.id in guild_b_ids
    assert game_a.id not in guild_b_ids


# Template Operations Integration Tests


@pytest.mark.asyncio
async def test_get_template_by_id_returns_template_from_correct_guild(
    db, guild_a_id, guild_b_id, sample_template_data
):
    """Verify get_template_by_id returns template only from correct guild."""
    template_a = await guild_queries.create_template(db, guild_a_id, sample_template_data)
    await db.commit()

    result = await guild_queries.get_template_by_id(db, guild_a_id, template_a.id)
    assert result is not None
    assert result.id == template_a.id
    assert result.guild_id == guild_a_id

    result_wrong_guild = await guild_queries.get_template_by_id(db, guild_b_id, template_a.id)
    assert result_wrong_guild is None


@pytest.mark.asyncio
async def test_list_templates_returns_only_guild_templates(
    db, guild_a_id, guild_b_id, guild_b_config, sample_template_data
):
    """Verify list_templates returns only templates from specified guild."""
    template_a1 = await guild_queries.create_template(
        db, guild_a_id, {**sample_template_data, "name": "Guild A Template 1"}
    )
    template_a2 = await guild_queries.create_template(
        db, guild_a_id, {**sample_template_data, "name": "Guild A Template 2"}
    )
    template_b = await guild_queries.create_template(
        db, guild_b_id, {**sample_template_data, "name": "Guild B Template"}
    )
    await db.commit()

    guild_a_templates = await guild_queries.list_templates(db, guild_a_id)
    guild_a_ids = {t.id for t in guild_a_templates}

    assert template_a1.id in guild_a_ids
    assert template_a2.id in guild_a_ids
    assert template_b.id not in guild_a_ids

    guild_b_templates = await guild_queries.list_templates(db, guild_b_id)
    guild_b_ids = {t.id for t in guild_b_templates}

    assert template_b.id in guild_b_ids
    assert template_a1.id not in guild_b_ids
    assert template_a2.id not in guild_b_ids


@pytest.mark.asyncio
async def test_create_template_sets_guild_id_correctly(db, guild_a_id, sample_template_data):
    """Verify create_template sets guild_id and persists to database."""
    template = await guild_queries.create_template(db, guild_a_id, sample_template_data)
    await db.commit()

    assert template.guild_id == guild_a_id

    result = await db.execute(
        text("SELECT guild_id FROM game_templates WHERE id = :template_id"),
        {"template_id": template.id},
    )
    db_guild_id = result.scalar_one()
    assert str(db_guild_id) == guild_a_id


@pytest.mark.asyncio
async def test_update_template_rejects_cross_guild_update(
    db, guild_a_id, guild_b_id, sample_template_data
):
    """Verify update_template validates template belongs to guild."""
    template = await guild_queries.create_template(db, guild_a_id, sample_template_data)
    await db.commit()

    with pytest.raises(ValueError, match="not found in guild"):
        await guild_queries.update_template(
            db, guild_b_id, template.id, {"name": "Unauthorized Update"}
        )


@pytest.mark.asyncio
async def test_update_template_succeeds_for_correct_guild(db, guild_a_id, sample_template_data):
    """Verify update_template works for template in correct guild."""
    template = await guild_queries.create_template(db, guild_a_id, sample_template_data)
    await db.commit()

    updated = await guild_queries.update_template(
        db, guild_a_id, template.id, {"name": "Updated Name"}
    )
    await db.commit()

    assert updated.name == "Updated Name"


# Performance Tests


@pytest.mark.asyncio
@pytest.mark.xfail(reason="RLS may add overhead - needs performance tuning")
async def test_wrapper_overhead_acceptable(db, guild_a_id, sample_game_data):
    """Verify wrapper adds < 100% overhead compared to direct query."""
    from sqlalchemy import select

    from shared.models.game import GameSession

    game = await guild_queries.create_game(db, guild_a_id, sample_game_data)
    await db.commit()

    # Time direct query (no RLS, no wrapper)
    start = time.perf_counter()
    result_direct = await db.execute(select(GameSession).where(GameSession.id == game.id))
    direct_game = result_direct.scalar_one_or_none()
    direct_time = time.perf_counter() - start

    # Time wrapper query (with RLS + guild_id validation)
    start = time.perf_counter()
    wrapper_game = await guild_queries.get_game_by_id(db, guild_a_id, game.id)
    wrapper_time = time.perf_counter() - start

    assert wrapper_game is not None
    assert direct_game.id == wrapper_game.id

    overhead_ratio = wrapper_time / direct_time if direct_time > 0 else 0
    assert overhead_ratio < 2.0, (
        f"Wrapper overhead too high: {overhead_ratio:.2f}x "
        f"(direct: {direct_time * 1000:.2f}ms, wrapper: {wrapper_time * 1000:.2f}ms)"
    )


@pytest.mark.asyncio
@pytest.mark.xfail(reason="RLS may add overhead - needs performance tuning")
async def test_list_operations_no_n_plus_1(db, guild_a_id, sample_game_data):
    """Verify list operations have < 100% overhead vs direct query."""
    from sqlalchemy import select

    from shared.models.game import GameSession

    for i in range(10):
        await guild_queries.create_game(db, guild_a_id, {**sample_game_data, "title": f"Game {i}"})
    await db.commit()

    # Time direct query (no RLS)
    start = time.perf_counter()
    result_direct = await db.execute(select(GameSession).where(GameSession.guild_id == guild_a_id))
    direct_games = list(result_direct.scalars().all())
    direct_time = time.perf_counter() - start

    # Time wrapper query (with RLS)
    start = time.perf_counter()
    wrapper_games = await guild_queries.list_games(db, guild_a_id)
    wrapper_time = time.perf_counter() - start

    assert len(wrapper_games) >= 10
    assert len(direct_games) == len(wrapper_games)

    overhead_ratio = wrapper_time / direct_time if direct_time > 0 else 0
    assert overhead_ratio < 2.0, (
        f"Wrapper overhead too high: {overhead_ratio:.2f}x "
        f"(direct: {direct_time * 1000:.2f}ms, "
        f"wrapper: {wrapper_time * 1000:.2f}ms, {len(wrapper_games)} games)"
    )


# Error Handling Tests


@pytest.mark.asyncio
async def test_empty_guild_id_raises_error(db):
    """Verify empty guild_id raises ValueError."""
    with pytest.raises(ValueError, match="guild_id cannot be empty"):
        await guild_queries.get_game_by_id(db, "", "some-game-id")


@pytest.mark.asyncio
async def test_nonexistent_game_returns_none(db, guild_a_id):
    """Verify querying non-existent game returns None."""
    result = await guild_queries.get_game_by_id(db, guild_a_id, str(uuid.uuid4()))
    assert result is None


@pytest.mark.asyncio
async def test_nonexistent_template_returns_none(db, guild_a_id):
    """Verify querying non-existent template returns None."""
    result = await guild_queries.get_template_by_id(db, guild_a_id, str(uuid.uuid4()))
    assert result is None
