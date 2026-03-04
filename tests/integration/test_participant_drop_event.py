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


"""Integration tests for handle_participant_drop_due against a real database.

Verifies that the handler deletes the target participant record and publishes
GAME_UPDATED when called with valid event data.
"""

import asyncio
import uuid
from unittest.mock import AsyncMock, MagicMock

import discord
import pytest
from sqlalchemy import text

from services.bot.events.publisher import BotEventPublisher
from services.bot.handlers.participant_drop import handle_participant_drop_due
from shared.models.participant import ParticipantType

pytestmark = pytest.mark.integration

PLAYER_DISCORD_ID = "444000000000000001"


def _insert_participant(admin_db_sync, game_id: str, user_id: str) -> str:
    participant_id = str(uuid.uuid4())
    admin_db_sync.execute(
        text(
            "INSERT INTO game_participants "
            "(id, game_session_id, user_id, position, position_type) "
            "VALUES (:id, :game_id, :user_id, :position, :position_type)"
        ),
        {
            "id": participant_id,
            "game_id": game_id,
            "user_id": user_id,
            "position": 1,
            "position_type": ParticipantType.HOST_ADDED,
        },
    )
    admin_db_sync.commit()
    return participant_id


def test_handler_removes_participant_from_db(
    admin_db_sync,
    create_user,
    create_guild,
    create_channel,
    create_game,
):
    """handle_participant_drop_due must delete the participant row from the DB."""
    guild = create_guild(discord_guild_id="333000000000000001")
    channel = create_channel(guild_id=guild["id"], discord_channel_id="333000000000000002")
    host = create_user(discord_user_id="333000000000000003")
    player = create_user(discord_user_id=PLAYER_DISCORD_ID)

    game = create_game(
        guild_id=guild["id"],
        channel_id=channel["id"],
        host_id=host["id"],
        title="Drop Integration Test Game",
    )
    participant_id = _insert_participant(admin_db_sync, game["id"], player["id"])

    rows_before = admin_db_sync.execute(
        text("SELECT id FROM game_participants WHERE id = :id"),
        {"id": participant_id},
    ).fetchall()
    assert len(rows_before) == 1, "Participant must exist before the handler runs"

    mock_bot = MagicMock(spec=discord.Client)
    mock_bot.fetch_user = AsyncMock(return_value=AsyncMock())
    mock_publisher = MagicMock(spec=BotEventPublisher)
    mock_publisher.publish_game_updated = AsyncMock()

    data = {"game_id": game["id"], "participant_id": participant_id}

    asyncio.get_event_loop().run_until_complete(
        handle_participant_drop_due(data, mock_bot, mock_publisher)
    )

    rows_after = admin_db_sync.execute(
        text("SELECT id FROM game_participants WHERE id = :id"),
        {"id": participant_id},
    ).fetchall()
    assert len(rows_after) == 0, "Participant must be deleted after the handler runs"
    mock_publisher.publish_game_updated.assert_called_once()


def test_handler_is_idempotent_when_participant_missing(
    admin_db_sync,
    create_user,
    create_guild,
    create_channel,
    create_game,
):
    """handle_participant_drop_due must not raise when participant is already gone."""
    guild = create_guild(discord_guild_id="334000000000000001")
    channel = create_channel(guild_id=guild["id"], discord_channel_id="334000000000000002")
    host = create_user(discord_user_id="334000000000000003")

    game = create_game(
        guild_id=guild["id"],
        channel_id=channel["id"],
        host_id=host["id"],
        title="Idempotent Drop Test",
    )

    missing_participant_id = str(uuid.uuid4())

    mock_bot = MagicMock(spec=discord.Client)
    mock_bot.fetch_user = AsyncMock(return_value=AsyncMock())
    mock_publisher = MagicMock(spec=BotEventPublisher)
    mock_publisher.publish_game_updated = AsyncMock()

    data = {"game_id": game["id"], "participant_id": missing_participant_id}

    asyncio.get_event_loop().run_until_complete(
        handle_participant_drop_due(data, mock_bot, mock_publisher)
    )
