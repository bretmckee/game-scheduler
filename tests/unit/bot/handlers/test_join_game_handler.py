# Copyright 2026 Bret McKee
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

"""Unit tests for handle_join_game — Phase 7 TDD.

Verifies that the join handler inserts into message_refresh_queue and calls
pg_notify('game_updated_sse', ...) directly instead of using BotEventPublisher.
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import discord
import pytest

from services.bot.handlers.join_game import handle_join_game
from shared.models.game import GameSession
from shared.models.user import User

USER_DISCORD_ID = "200111222333444555"


@pytest.fixture
def game_id():
    return str(uuid4())


@pytest.fixture
def mock_game(game_id):
    game = MagicMock(spec=GameSession)
    game.id = game_id
    game.title = "Join Handler Test Game"
    game.guild_id = "guild-db-uuid-join"
    game.status = "SCHEDULED"
    game.max_players = 8
    template = MagicMock()
    template.signup_priority_role_ids = []
    template.max_players = None
    game.template = template
    guild = MagicMock()
    guild.guild_id = "discord-guild-id-join"
    game.guild = guild
    channel = MagicMock()
    channel.channel_id = "discord-channel-id-join"
    game.channel = channel
    return game


@pytest.fixture
def mock_interaction():
    interaction = MagicMock(spec=discord.Interaction)
    interaction.user = MagicMock()
    interaction.user.id = int(USER_DISCORD_ID)
    interaction.user.global_name = None
    interaction.user.name = "TestUser"
    interaction.user.display_avatar = None
    interaction.user.send = AsyncMock()
    interaction.user.roles = []
    interaction.response = MagicMock()
    interaction.response.is_done = MagicMock(return_value=False)
    interaction.response.defer = AsyncMock()
    interaction.followup = MagicMock()
    interaction.followup.send = AsyncMock()
    interaction.client = MagicMock()
    return interaction


def _make_mock_db(mock_game: MagicMock) -> MagicMock:
    """Build a mock DB session for join_game handler tests.

    _validate_join_game runs 3 queries (game, user, participant count).
    The new Phase 7 implementation then runs 2 more (upsert + pg_notify).
    """
    mock_db = AsyncMock()
    mock_db.add = MagicMock()
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()
    mock_db.delete = AsyncMock()

    game_result = MagicMock()
    game_result.scalar_one_or_none = MagicMock(return_value=mock_game)

    user = MagicMock(spec=User)
    user.id = str(uuid4())
    user_result = MagicMock()
    user_result.scalar_one_or_none = MagicMock(return_value=user)

    count_result = MagicMock()
    count_result.scalars = MagicMock()
    count_result.scalars.return_value.all = MagicMock(return_value=[])

    upsert_result = MagicMock()
    notify_result = MagicMock()

    mock_db.execute = AsyncMock(
        side_effect=[game_result, user_result, count_result, upsert_result, notify_result]
    )
    return mock_db


def _patch_db(mock_db: MagicMock) -> MagicMock:
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=mock_db)
    ctx.__aexit__ = AsyncMock(return_value=False)
    return patch("services.bot.handlers.join_game.get_db_session", return_value=ctx)


# ---------------------------------------------------------------------------
# Phase 7 TDD — xfail tests for direct DB operations (no publisher)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_join_game_executes_message_refresh_upsert(mock_game, mock_interaction, game_id):
    """After a successful join, db.execute is called for the MessageRefreshQueue upsert."""
    mock_db = _make_mock_db(mock_game)

    with _patch_db(mock_db):
        await handle_join_game(mock_interaction, game_id)

    upsert_calls = [
        call
        for call in mock_db.execute.call_args_list
        if "message_refresh_queue" in str(call.args[0]).lower()
    ]
    assert len(upsert_calls) >= 1, (
        "Expected at least one db.execute call for message_refresh_queue upsert"
    )


@pytest.mark.asyncio
async def test_join_game_executes_pg_notify(mock_game, mock_interaction, game_id):
    """After a successful join, db.execute is called with pg_notify('game_updated_sse', ...)."""
    mock_db = _make_mock_db(mock_game)

    with _patch_db(mock_db):
        await handle_join_game(mock_interaction, game_id)

    notify_calls = [
        call for call in mock_db.execute.call_args_list if "game_updated_sse" in str(call.args[0])
    ]
    assert len(notify_calls) >= 1, (
        "Expected db.execute call with pg_notify('game_updated_sse', ...)"
    )
