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


"""Integration tests for games database query patterns before guild_queries migration.

These tests establish behavioral baseline for GameService database operations.
Focus: Verify current database query behavior with minimal mocking.

IMPORTANT: Many tests document CURRENT INSECURE BEHAVIOR (no guild filtering in get_game).
After migration to guild_queries wrappers, tests must be updated to verify enforcement.
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

import pytest

from services.api.services.games import GameService
from shared.messaging.publisher import EventPublisher
from shared.models.game import GameSession, GameStatus

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_get_game_returns_any_game_without_guild_filter(
    admin_db, create_guild, create_channel, create_user, create_template, create_game
):
    """Verify current GameService.get_game: returns any game by ID, NO guild filtering.

    SECURITY GAP: This documents current insecure behavior.
    After migration: get_game should require guild_id parameter and enforce filtering.
    """
    # Create test data for two guilds
    guild_a = create_guild()
    channel_a = create_channel(guild_id=guild_a["id"])
    user_a = create_user()
    template_a = create_template(guild_id=guild_a["id"], channel_id=channel_a["id"])
    game_a = create_game(
        guild_id=guild_a["id"],
        channel_id=channel_a["id"],
        template_id=template_a["id"],
        host_id=user_a["id"],
        title="Game A",
    )

    guild_b = create_guild()
    channel_b = create_channel(guild_id=guild_b["id"])
    user_b = create_user()
    template_b = create_template(guild_id=guild_b["id"], channel_id=channel_b["id"])
    game_b = create_game(
        guild_id=guild_b["id"],
        channel_id=channel_b["id"],
        template_id=template_b["id"],
        host_id=user_b["id"],
        title="Game B",
    )

    service = GameService(
        db=admin_db,
        event_publisher=EventPublisher(),
        discord_client=MagicMock(),
        participant_resolver=MagicMock(),
    )

    await admin_db.commit()

    # Current: get_game returns ANY game by ID
    result_a = await service.get_game(game_a["id"])
    assert result_a is not None
    assert result_a.id == game_a["id"]

    # SECURITY GAP: Also returns game from different guild
    result_b = await service.get_game(game_b["id"])
    assert result_b is not None
    assert result_b.id == game_b["id"]


@pytest.mark.asyncio
async def test_list_games_filters_by_guild_when_specified(
    admin_db, create_guild, create_channel, create_user, create_template, create_game
):
    """Verify list_games correctly filters by guild_id when parameter provided."""
    # Create test data for two guilds
    guild_a = create_guild()
    channel_a = create_channel(guild_id=guild_a["id"])
    user_a = create_user()
    template_a = create_template(guild_id=guild_a["id"], channel_id=channel_a["id"])
    game_a = create_game(
        guild_id=guild_a["id"],
        channel_id=channel_a["id"],
        template_id=template_a["id"],
        host_id=user_a["id"],
        title="Game A",
    )

    guild_b = create_guild()
    channel_b = create_channel(guild_id=guild_b["id"])
    user_b = create_user()
    template_b = create_template(guild_id=guild_b["id"], channel_id=channel_b["id"])
    game_b = create_game(
        guild_id=guild_b["id"],
        channel_id=channel_b["id"],
        template_id=template_b["id"],
        host_id=user_b["id"],
        title="Game B",
    )

    service = GameService(
        db=admin_db,
        event_publisher=EventPublisher(),
        discord_client=MagicMock(),
        participant_resolver=MagicMock(),
    )

    await admin_db.commit()

    # List games for guild A
    games_a, total_a = await service.list_games(guild_id=guild_a["id"])
    assert total_a == 1
    assert len(games_a) == 1
    assert games_a[0].id == game_a["id"]
    assert games_a[0].guild_id == guild_a["id"]

    # List games for guild B
    games_b, total_b = await service.list_games(guild_id=guild_b["id"])
    assert total_b == 1
    assert len(games_b) == 1
    assert games_b[0].id == game_b["id"]
    assert games_b[0].guild_id == guild_b["id"]


@pytest.mark.asyncio
async def test_list_games_with_channel_filter(
    admin_db, create_guild, create_channel, create_user, create_template, create_game
):
    """Verify list_games respects channel filter within guild."""
    guild = create_guild()
    channel = create_channel(guild_id=guild["id"])
    user = create_user()
    template = create_template(guild_id=guild["id"], channel_id=channel["id"])
    game = create_game(
        guild_id=guild["id"],
        channel_id=channel["id"],
        template_id=template["id"],
        host_id=user["id"],
        title="Test Game",
    )

    service = GameService(
        db=admin_db,
        event_publisher=EventPublisher(),
        discord_client=MagicMock(),
        participant_resolver=MagicMock(),
    )

    await admin_db.commit()

    games, total = await service.list_games(guild_id=guild["id"], channel_id=channel["id"])
    assert total == 1
    assert len(games) == 1
    assert games[0].id == game["id"]
    assert games[0].channel_id == channel["id"]


@pytest.mark.asyncio
async def test_list_games_with_status_filter(
    admin_db, create_guild, create_channel, create_user, create_template
):
    """Verify list_games respects status filter."""
    guild = create_guild()
    channel = create_channel(guild_id=guild["id"])
    user = create_user()
    template = create_template(guild_id=guild["id"], channel_id=channel["id"])

    # Create game directly in async session
    game = GameSession(
        guild_id=guild["id"],
        channel_id=channel["id"],
        template_id=template["id"],
        host_id=user["id"],
        title="Test Game",
        scheduled_at=datetime.now(UTC).replace(tzinfo=None) + timedelta(hours=2),
        max_players=4,
        status=GameStatus.SCHEDULED,
    )
    admin_db.add(game)
    await admin_db.commit()

    service = GameService(
        db=admin_db,
        event_publisher=EventPublisher(),
        discord_client=MagicMock(),
        participant_resolver=MagicMock(),
    )

    # List scheduled games
    games, total = await service.list_games(guild_id=guild["id"], status="SCHEDULED")
    assert total == 1
    assert games[0].status == GameStatus.SCHEDULED

    # List completed games (should be empty)
    games_completed, total_completed = await service.list_games(
        guild_id=guild["id"], status="COMPLETED"
    )
    assert total_completed == 0
    assert len(games_completed) == 0


@pytest.mark.asyncio
async def test_list_games_pagination(
    admin_db, create_guild, create_channel, create_user, create_template
):
    """Verify list_games pagination works correctly."""
    guild = create_guild()
    channel = create_channel(guild_id=guild["id"])
    user = create_user()
    template = create_template(guild_id=guild["id"], channel_id=channel["id"])

    # Create multiple games
    for i in range(5):
        game = GameSession(
            guild_id=guild["id"],
            channel_id=channel["id"],
            template_id=template["id"],
            host_id=user["id"],
            title=f"Game {i}",
            scheduled_at=datetime.now(UTC).replace(tzinfo=None) + timedelta(days=i + 1),
            max_players=4,
            status=GameStatus.SCHEDULED,
        )
        admin_db.add(game)

    await admin_db.commit()

    service = GameService(
        db=admin_db,
        event_publisher=EventPublisher(),
        discord_client=MagicMock(),
        participant_resolver=MagicMock(),
    )

    # Get first page
    games_page1, total = await service.list_games(guild_id=guild["id"], limit=2, offset=0)
    assert total == 5
    assert len(games_page1) == 2

    # Get second page
    games_page2, total = await service.list_games(guild_id=guild["id"], limit=2, offset=2)
    assert total == 5
    assert len(games_page2) == 2

    # Verify different games on each page
    page1_ids = {g.id for g in games_page1}
    page2_ids = {g.id for g in games_page2}
    assert len(page1_ids & page2_ids) == 0


@pytest.mark.asyncio
async def test_guild_isolation_in_list_games(
    admin_db, create_guild, create_channel, create_user, create_template, create_game
):
    """Verify complete guild isolation in list_games across multiple operations."""
    # Create test data for two guilds
    guild_a = create_guild()
    channel_a = create_channel(guild_id=guild_a["id"])
    user_a = create_user()
    template_a = create_template(guild_id=guild_a["id"], channel_id=channel_a["id"])
    game_a = create_game(
        guild_id=guild_a["id"],
        channel_id=channel_a["id"],
        template_id=template_a["id"],
        host_id=user_a["id"],
        title="Game A",
    )

    guild_b = create_guild()
    channel_b = create_channel(guild_id=guild_b["id"])
    user_b = create_user()
    template_b = create_template(guild_id=guild_b["id"], channel_id=channel_b["id"])
    game_b = create_game(
        guild_id=guild_b["id"],
        channel_id=channel_b["id"],
        template_id=template_b["id"],
        host_id=user_b["id"],
        title="Game B",
    )

    service = GameService(
        db=admin_db,
        event_publisher=EventPublisher(),
        discord_client=MagicMock(),
        participant_resolver=MagicMock(),
    )

    await admin_db.commit()

    # Guild A listing
    games_a, total_a = await service.list_games(guild_id=guild_a["id"])
    assert total_a == 1
    assert all(g.guild_id == guild_a["id"] for g in games_a)
    assert game_b["id"] not in [g.id for g in games_a]

    # Guild B listing
    games_b, total_b = await service.list_games(guild_id=guild_b["id"])
    assert total_b == 1
    assert all(g.guild_id == guild_b["id"] for g in games_b)
    assert game_a["id"] not in [g.id for g in games_b]
