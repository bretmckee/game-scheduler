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


"""Integration tests for EmbedDeletionConsumer._handle_embed_deleted.

Verifies that the handler deletes the game row when called with valid event data.
The Discord message is already gone when this handler runs, so no bot_action_queue
notification is enqueued.

Note: These tests call the handler directly (not via RabbitMQ dispatch) because
the bot container is not part of the integration environment. Event dispatch
registration is verified separately in unit tests.
"""

import asyncio
import uuid

import pytest
from sqlalchemy import text

from services.api.services.embed_deletion_consumer import EmbedDeletionConsumer
from shared.database import bot_engine
from shared.messaging.events import Event, EventType

pytestmark = pytest.mark.integration


@pytest.fixture(autouse=True)
async def _cleanup_engines():
    """Dispose engine pools after each test for clean event loop state."""
    yield
    await bot_engine.dispose()


@pytest.mark.asyncio
async def test_handle_embed_deleted_removes_game_and_publishes_cancelled(
    admin_db_sync,
    create_user,
    create_guild,
    create_channel,
    create_game,
):
    """_handle_embed_deleted must delete the game row."""
    guild = create_guild(discord_guild_id="550000000000000001")
    channel = create_channel(guild_id=guild["id"], discord_channel_id="550000000000000002")
    host = create_user(discord_user_id="550000000000000003")
    game = create_game(
        guild_id=guild["id"],
        channel_id=channel["id"],
        host_id=host["id"],
        title="Embed Deletion Consumer Integration Test",
    )

    rows_before = admin_db_sync.execute(
        text("SELECT id FROM game_sessions WHERE id = :id"),
        {"id": game["id"]},
    ).fetchall()
    assert len(rows_before) == 1, "Game must exist before the handler runs"

    consumer = EmbedDeletionConsumer()
    event = Event(
        event_type=EventType.EMBED_DELETED,
        data={"game_id": game["id"], "channel_id": "550000000000000002", "message_id": "1"},
    )

    await consumer._handle_embed_deleted(event)

    await asyncio.sleep(0.1)

    rows_after = admin_db_sync.execute(
        text("SELECT id FROM game_sessions WHERE id = :id"),
        {"id": game["id"]},
    ).fetchall()
    assert len(rows_after) == 0, "Game must be deleted after the handler runs"

    # The Discord message is already gone, so no bot_action_queue row should be enqueued.
    bot_queue_rows = admin_db_sync.execute(
        text("SELECT id FROM bot_action_queue WHERE game_id = :game_id"),
        {"game_id": game["id"]},
    ).fetchall()
    assert len(bot_queue_rows) == 0, "No bot_action_queue row should be enqueued for embed deletion"


@pytest.mark.asyncio
async def test_handle_embed_deleted_is_idempotent_when_game_missing(admin_db_sync):
    """_handle_embed_deleted must not raise when the game is already gone."""
    consumer = EmbedDeletionConsumer()
    missing_game_id = str(uuid.uuid4())
    event = Event(
        event_type=EventType.EMBED_DELETED,
        data={
            "game_id": missing_game_id,
            "channel_id": "550000000000000002",
            "message_id": "1",
        },
    )

    await consumer._handle_embed_deleted(event)

    # No bot_action_queue row should be created for a missing game.
    bot_queue_rows = admin_db_sync.execute(
        text("SELECT id FROM bot_action_queue WHERE game_id = :game_id"),
        {"game_id": missing_game_id},
    ).fetchall()
    assert len(bot_queue_rows) == 0


@pytest.mark.asyncio
async def test_handle_embed_deleted_with_participant_removes_game_and_publishes_cancelled(
    admin_db_sync,
    create_user,
    create_guild,
    create_channel,
    create_game,
):
    """_handle_embed_deleted must delete game and participant rows."""
    guild = create_guild(discord_guild_id="551000000000000001")
    channel = create_channel(guild_id=guild["id"], discord_channel_id="551000000000000002")
    host = create_user(discord_user_id="551000000000000003")
    game = create_game(
        guild_id=guild["id"],
        channel_id=channel["id"],
        host_id=host["id"],
        title="Embed Deletion With Participant Integration Test",
    )
    participant = create_user(discord_user_id="551000000000000004")
    admin_db_sync.execute(
        text(
            "INSERT INTO game_participants (id, game_session_id, user_id, position_type, position) "
            "VALUES (:id, :game_id, :user_id, 24000, 0)"
        ),
        {"id": str(uuid.uuid4()), "game_id": game["id"], "user_id": participant["id"]},
    )
    admin_db_sync.commit()

    rows_before = admin_db_sync.execute(
        text("SELECT id FROM game_sessions WHERE id = :id"),
        {"id": game["id"]},
    ).fetchall()
    assert len(rows_before) == 1, "Game must exist before the handler runs"

    participant_rows_before = admin_db_sync.execute(
        text("SELECT id FROM game_participants WHERE game_session_id = :id"),
        {"id": game["id"]},
    ).fetchall()
    assert len(participant_rows_before) == 1, "Participant must exist before the handler runs"

    consumer = EmbedDeletionConsumer()
    event = Event(
        event_type=EventType.EMBED_DELETED,
        data={"game_id": game["id"], "channel_id": "551000000000000002", "message_id": "1"},
    )

    await consumer._handle_embed_deleted(event)

    await asyncio.sleep(0.1)

    rows_after = admin_db_sync.execute(
        text("SELECT id FROM game_sessions WHERE id = :id"),
        {"id": game["id"]},
    ).fetchall()
    assert len(rows_after) == 0, "Game must be deleted after the handler runs"

    participant_rows_after = admin_db_sync.execute(
        text("SELECT id FROM game_participants WHERE game_session_id = :id"),
        {"id": game["id"]},
    ).fetchall()
    assert len(participant_rows_after) == 0, "Participant rows must be deleted with the game"

    bot_queue_rows = admin_db_sync.execute(
        text("SELECT id FROM bot_action_queue WHERE game_id = :game_id"),
        {"game_id": game["id"]},
    ).fetchall()
    assert len(bot_queue_rows) == 0, "No bot_action_queue row should be enqueued for embed deletion"
