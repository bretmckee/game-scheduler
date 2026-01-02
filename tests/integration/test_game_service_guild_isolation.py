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


"""Integration tests for GameService guild isolation via RLS.

Validates that GameService.get_game() and GameService.list_games() respect
guild isolation when guild context is set via set_current_guild_ids().

Test Strategy:
1. Create games in two different guilds (A and B)
2. Set guild context to guild A
3. Verify GameService only returns guild A games
4. Clear context and verify all games visible (no RLS enforcement)

CRITICAL: These tests require RLS policies to be ENABLED in Phase 3.
"""

from unittest.mock import MagicMock

import pytest

from services.api.services.games import GameService
from shared.data_access.guild_isolation import set_current_guild_ids
from shared.discord import client as discord_client_module
from shared.messaging.publisher import EventPublisher

pytestmark = pytest.mark.integration


@pytest.fixture
def game_service(db):
    """Create GameService instance with real database session and mocked dependencies."""
    event_publisher = EventPublisher()
    discord_client = MagicMock(spec=discord_client_module.DiscordAPIClient)
    return GameService(
        db=db,
        event_publisher=event_publisher,
        discord_client=discord_client,
        participant_resolver=None,
    )


class TestGameServiceGetGame:
    """Test GameService.get_game() respects guild isolation."""

    async def test_get_game_with_guild_context_returns_own_guild_game(
        self, game_service, game_a, guild_a_id
    ):
        """GameService.get_game() returns game when guild context matches."""
        set_current_guild_ids([guild_a_id])
        result = await game_service.get_game(game_a.id)
        assert result is not None
        assert result.id == game_a.id
        assert result.title == "Game A"

    @pytest.mark.xfail(reason="RLS not enabled yet - will pass in Phase 3")
    async def test_get_game_with_guild_context_filters_other_guild_game(
        self, game_service, game_a, game_b, guild_a_id
    ):
        """GameService.get_game() returns None for other guild's game."""
        set_current_guild_ids([guild_a_id])
        result = await game_service.get_game(game_b.id)
        assert result is None

    async def test_get_game_without_guild_context_returns_any_game(
        self, game_service, game_a, game_b
    ):
        """GameService.get_game() returns any game when no guild context set."""
        result_a = await game_service.get_game(game_a.id)
        assert result_a is not None
        assert result_a.id == game_a.id

        result_b = await game_service.get_game(game_b.id)
        assert result_b is not None
        assert result_b.id == game_b.id

    async def test_get_game_with_multiple_guild_context_returns_any_matching_guild(
        self, game_service, game_a, game_b, guild_a_id, guild_b_id
    ):
        """GameService.get_game() returns game from any guild in context list."""
        set_current_guild_ids([guild_a_id, guild_b_id])

        result_a = await game_service.get_game(game_a.id)
        assert result_a is not None
        assert result_a.id == game_a.id

        result_b = await game_service.get_game(game_b.id)
        assert result_b is not None
        assert result_b.id == game_b.id


class TestGameServiceListGames:
    """Test GameService.list_games() respects guild isolation."""

    @pytest.mark.xfail(reason="RLS not enabled yet - will pass in Phase 3")
    async def test_list_games_with_guild_context_filters_to_own_guild(
        self, game_service, game_a, game_b, guild_a_id
    ):
        """GameService.list_games() returns only guild A games when context set."""
        set_current_guild_ids([guild_a_id])
        games, total = await game_service.list_games()

        assert total == 1
        assert len(games) == 1
        assert games[0].id == game_a.id
        assert games[0].title == "Game A"

    async def test_list_games_without_guild_context_returns_all_games(
        self, game_service, game_a, game_b
    ):
        """GameService.list_games() returns all games when no context set."""
        games, total = await game_service.list_games()

        assert total >= 2
        assert len(games) >= 2
        game_ids = {game.id for game in games}
        assert game_a.id in game_ids
        assert game_b.id in game_ids

    async def test_list_games_with_multiple_guild_context_returns_matching_guilds(
        self, game_service, game_a, game_b, guild_a_id, guild_b_id
    ):
        """GameService.list_games() returns games from all guilds in context."""
        set_current_guild_ids([guild_a_id, guild_b_id])
        games, total = await game_service.list_games()

        assert total >= 2
        assert len(games) >= 2
        game_ids = {game.id for game in games}
        assert game_a.id in game_ids
        assert game_b.id in game_ids

    async def test_list_games_with_guild_filter_respects_guild_context(
        self, game_service, game_a, game_b, guild_a_id, guild_b_id
    ):
        """GameService.list_games() combines guild_id filter with RLS context."""
        set_current_guild_ids([guild_a_id])
        games, total = await game_service.list_games(guild_id=guild_a_id)

        assert total == 1
        assert len(games) == 1
        assert games[0].id == game_a.id

    @pytest.mark.xfail(reason="RLS not enabled yet - will pass in Phase 3")
    async def test_list_games_with_conflicting_guild_filter_returns_empty(
        self, game_service, game_a, game_b, guild_a_id, guild_b_id
    ):
        """GameService.list_games() returns empty when filter conflicts with RLS."""
        set_current_guild_ids([guild_a_id])
        games, total = await game_service.list_games(guild_id=guild_b_id)

        assert total == 0
        assert len(games) == 0

    async def test_list_games_pagination_respects_guild_context(
        self, game_service, game_a, guild_a_id
    ):
        """GameService.list_games() pagination works with guild context."""
        set_current_guild_ids([guild_a_id])

        all_games, total = await game_service.list_games()
        assert total >= 1
        game_ids = {game.id for game in all_games}
        assert game_a.id in game_ids

        games_page1, total_page1 = await game_service.list_games(limit=1, offset=0)
        assert len(games_page1) == 1
        assert total_page1 >= 1
