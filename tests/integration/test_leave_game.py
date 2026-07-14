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


"""Integration tests for handle_leave_game against a real database.

Same infrastructure pattern as test_join_game.py: call handler directly,
patch get_db_session to BYPASSRLS, use real DB fixtures.
"""

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import text

from services.bot.handlers.leave_game import handle_leave_game
from shared.database import BotAsyncSessionLocal, bot_engine
from shared.message_formats import DMPredicates
from shared.utils.status_transitions import GameStatus

pytestmark = pytest.mark.integration

PLAYER_DISCORD_ID = "600000000000000001"


def _make_interaction(discord_user_id: str) -> MagicMock:
    interaction = MagicMock()
    interaction.user = MagicMock()
    interaction.user.id = int(discord_user_id)
    interaction.user.global_name = None
    interaction.user.name = f"TestUser{discord_user_id[-4:]}"
    interaction.user.display_avatar = None
    interaction.user.send = AsyncMock()
    interaction.response = MagicMock()
    interaction.response.is_done = MagicMock(return_value=False)
    interaction.response.defer = AsyncMock()
    return interaction


def _patch_db():
    def _bypass():
        return BotAsyncSessionLocal()

    return patch("services.bot.handlers.leave_game.get_db_session", side_effect=_bypass)


@pytest.fixture(autouse=True)
async def _cleanup_engines():
    yield
    await bot_engine.dispose()


@pytest.fixture
def test_game(create_guild, create_channel, create_user, create_game):
    guild = create_guild(discord_guild_id="600111111111111111")
    channel = create_channel(guild_id=guild["id"], discord_channel_id="600222222222222222")
    host = create_user(discord_user_id="600333333333333333")
    game = create_game(
        guild_id=guild["id"],
        channel_id=channel["id"],
        host_id=host["id"],
        title="Leave Integration Test Game",
        status=GameStatus.SCHEDULED,
    )
    assert game["title"] == "Leave Integration Test Game"
    return {"guild": guild, "channel": channel, "host": host, "game": game}


def _insert_participant(
    admin_db_sync,
    game_id: str,
    user_id: str,
    position: int = 1,
    position_type: int = 1,
    joined_at: datetime | None = None,
) -> str:
    participant_id = str(uuid.uuid4())
    admin_db_sync.execute(
        text(
            "INSERT INTO game_participants "
            "(id, game_session_id, user_id, position, position_type, joined_at) "
            "VALUES (:id, :game_id, :user_id, :position, :position_type, :joined_at)"
        ),
        {
            "id": participant_id,
            "game_id": game_id,
            "user_id": user_id,
            "position": position,
            "position_type": position_type,
            "joined_at": joined_at or datetime.now(UTC),
        },
    )
    admin_db_sync.commit()
    return participant_id


@pytest.mark.asyncio
async def test_invalid_uuid_returns_error_without_touching_db(test_game, admin_db_sync) -> None:
    """An unparseable game_id sends an error DM and makes no DB changes."""
    interaction = _make_interaction(PLAYER_DISCORD_ID)
    rows_before = admin_db_sync.execute(text("SELECT COUNT(*) FROM game_participants")).scalar()

    with _patch_db():
        await handle_leave_game(interaction, "not-a-uuid")

    rows_after = admin_db_sync.execute(text("SELECT COUNT(*) FROM game_participants")).scalar()
    assert rows_after == rows_before
    interaction.user.send.assert_called_once()
    assert "Invalid game ID" in interaction.user.send.call_args.kwargs["content"]


@pytest.mark.asyncio
async def test_game_not_found_sends_error(test_game) -> None:
    """A valid UUID with no matching game sends the 'Game not found' error."""
    interaction = _make_interaction(PLAYER_DISCORD_ID)

    with _patch_db():
        await handle_leave_game(interaction, str(uuid.uuid4()))

    interaction.user.send.assert_called_once()
    assert "Game not found" in interaction.user.send.call_args.kwargs["content"]


@pytest.mark.asyncio
async def test_completed_game_sends_error(test_game, admin_db_sync) -> None:
    """Attempting to leave a completed game sends the appropriate error."""
    guild = test_game["guild"]
    channel = test_game["channel"]
    host = test_game["host"]

    completed_game_id = str(uuid.uuid4())
    admin_db_sync.execute(
        text(
            "INSERT INTO game_sessions "
            "(id, guild_id, channel_id, host_id, title, description, "
            "scheduled_at, max_players, status, created_at, updated_at) "
            "VALUES (:id, :guild_id, :channel_id, :host_id, :title, :description, "
            ":scheduled_at, :max_players, :status, :created_at, :updated_at)"
        ),
        {
            "id": completed_game_id,
            "guild_id": guild["id"],
            "channel_id": channel["id"],
            "host_id": host["id"],
            "title": "Completed Leave Test Game",
            "description": "A completed game",
            "scheduled_at": datetime.now(UTC) - timedelta(hours=1),
            "max_players": 4,
            "status": GameStatus.COMPLETED,
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
        },
    )
    admin_db_sync.commit()

    interaction = _make_interaction(PLAYER_DISCORD_ID)

    with _patch_db():
        await handle_leave_game(interaction, completed_game_id)

    interaction.user.send.assert_called_once()
    assert "Cannot leave a completed game" in interaction.user.send.call_args.kwargs["content"]


@pytest.mark.asyncio
async def test_user_not_in_db_returns_silently(test_game) -> None:
    """User with no DB record returns without error message or event."""
    interaction = _make_interaction("699000000000000001")
    game = test_game["game"]

    with _patch_db():
        await handle_leave_game(interaction, game["id"])

    interaction.user.send.assert_not_called()


@pytest.mark.asyncio
async def test_user_not_participant_returns_silently(test_game, create_user) -> None:
    """User exists but has no participant row; returns without error or event."""
    create_user(discord_user_id=PLAYER_DISCORD_ID)
    game = test_game["game"]
    interaction = _make_interaction(PLAYER_DISCORD_ID)

    with _patch_db():
        await handle_leave_game(interaction, game["id"])

    interaction.user.send.assert_not_called()


@pytest.mark.asyncio
async def test_successful_leave_deletes_participant_and_publishes_event(
    test_game, create_user, admin_db_sync
) -> None:
    """Happy path: participant row deleted and message_refresh_queue row upserted."""
    player = create_user(discord_user_id=PLAYER_DISCORD_ID)
    game = test_game["game"]
    participant_id = _insert_participant(admin_db_sync, game["id"], player["id"])

    rows_before = admin_db_sync.execute(
        text("SELECT id FROM game_participants WHERE id = :id"), {"id": participant_id}
    ).fetchall()
    assert len(rows_before) == 1, "Precondition: participant must exist"

    interaction = _make_interaction(PLAYER_DISCORD_ID)

    with _patch_db():
        await handle_leave_game(interaction, game["id"])

    rows_after = admin_db_sync.execute(
        text("SELECT id FROM game_participants WHERE id = :id"), {"id": participant_id}
    ).fetchall()
    assert len(rows_after) == 0, "Participant must be deleted after leave"

    mrq_row = admin_db_sync.execute(
        text("SELECT game_id FROM message_refresh_queue WHERE game_id = :game_id"),
        {"game_id": game["id"]},
    ).fetchone()
    assert mrq_row is not None, "message_refresh_queue row must exist after successful leave"

    interaction.user.send.assert_called_once()
    assert "You've left" in interaction.user.send.call_args.kwargs["content"]


@pytest.mark.asyncio
async def test_host_added_leave_sends_dm_to_host(test_game, create_user, admin_db_sync) -> None:
    """When a HOST_ADDED participant leaves, a host_added_dropout DM is enqueued."""
    player = create_user(discord_user_id=PLAYER_DISCORD_ID)
    host = test_game["host"]
    game = test_game["game"]

    _insert_participant(
        admin_db_sync,
        game["id"],
        player["id"],
        position_type=8000,  # ParticipantType.HOST_ADDED
    )

    interaction = _make_interaction(PLAYER_DISCORD_ID)
    interaction.client = MagicMock()

    with _patch_db():
        await handle_leave_game(interaction, game["id"])

    interaction.client.get_user.assert_not_called()

    dm_rows = admin_db_sync.execute(
        text(
            "SELECT discord_id, payload FROM bot_action_queue "
            "WHERE action_type = 'send_dm' AND game_id = :game_id"
        ),
        {"game_id": game["id"]},
    ).fetchall()
    dropout_rows = [
        row for row in dm_rows if row[1].get("notification_type") == "host_added_dropout"
    ]
    assert len(dropout_rows) == 1, "No host_added_dropout send_dm row found in bot_action_queue"
    assert dropout_rows[0][0] == host["discord_id"]

    @dataclass
    class _DM:
        content: str | None

    assert DMPredicates.host_added_dropout(game["title"])(_DM(dropout_rows[0][1]["message"]))


@pytest.mark.asyncio
async def test_confirmed_leave_via_handler_promotes_waitlisted_participant(
    test_game, create_user, create_game, admin_db_sync
) -> None:
    """A confirmed participant leaving via the Discord button promotes a waitlisted user."""
    guild = test_game["guild"]
    channel = test_game["channel"]
    host = test_game["host"]

    game = create_game(
        guild_id=guild["id"],
        channel_id=channel["id"],
        host_id=host["id"],
        title="Leave Promotion Handler Test Game",
        max_players=1,
    )

    confirmed_user = create_user(discord_user_id=PLAYER_DISCORD_ID)
    waitlisted_user = create_user()

    confirmed_participant_id = _insert_participant(
        admin_db_sync,
        game["id"],
        confirmed_user["id"],
        joined_at=datetime.now(UTC),
    )
    _insert_participant(
        admin_db_sync,
        game["id"],
        waitlisted_user["id"],
        joined_at=datetime.now(UTC) + timedelta(seconds=1),
    )

    interaction = _make_interaction(PLAYER_DISCORD_ID)

    with _patch_db():
        await handle_leave_game(interaction, game["id"])

    participant_row = admin_db_sync.execute(
        text("SELECT id FROM game_participants WHERE id = :id"),
        {"id": confirmed_participant_id},
    ).fetchone()
    assert participant_row is None, "Confirmed participant must be deleted after leaving"

    dm_rows = admin_db_sync.execute(
        text(
            "SELECT discord_id, payload FROM bot_action_queue "
            "WHERE action_type = 'send_dm' AND game_id = :game_id"
        ),
        {"game_id": game["id"]},
    ).fetchall()
    promotion_rows = [
        row for row in dm_rows if row[1].get("notification_type") == "waitlist_promotion"
    ]
    assert len(promotion_rows) == 1, f"No waitlist_promotion send_dm row found: {dm_rows}"
    assert promotion_rows[0][0] == waitlisted_user["discord_id"]
