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

"""Unit tests for handle_leave_game.

Verifies leave DM suppression when the join notification has not been sent yet.
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import discord
import pytest

from services.bot.handlers.leave_game import handle_leave_game
from shared.message_formats import DMPredicates
from shared.models.game import GameSession
from shared.models.notification_schedule import NotificationSchedule
from shared.models.participant import GameParticipant, ParticipantType
from shared.models.user import User

USER_DISCORD_ID = "111222333444555666"


@pytest.fixture
def game_id():
    return str(uuid4())


@pytest.fixture
def participant_db_id():
    return str(uuid4())


@pytest.fixture
def mock_game(game_id):
    game = MagicMock(spec=GameSession)
    game.id = game_id
    game.title = "Leave Test Game"
    game.guild_id = "guild-db-uuid-42"
    game.status = "SCHEDULED"
    return game


@pytest.fixture
def mock_participant(participant_db_id, mock_game):
    participant = MagicMock(spec=GameParticipant)
    participant.id = participant_db_id
    participant.game_session_id = mock_game.id
    participant.user = MagicMock(spec=User)
    participant.user.discord_id = USER_DISCORD_ID
    return participant


@pytest.fixture
def mock_interaction():
    interaction = MagicMock(spec=discord.Interaction)
    interaction.user = MagicMock()
    interaction.user.id = int(USER_DISCORD_ID)
    interaction.user.send = AsyncMock()
    interaction.response = MagicMock()
    interaction.response.is_done = MagicMock(return_value=False)
    interaction.response.defer = AsyncMock()
    interaction.followup = MagicMock()
    interaction.followup.send = AsyncMock()
    return interaction


def _make_mock_db(mock_participant, mock_game, unsent_notification=None):
    """Build a mock DB session for leave_game handler tests.

    _validate_leave_game runs 3 queries (game, user, participant + count).
    The leave handler then runs 1 notification query + 2 for upsert and pg_notify.
    """
    mock_db = AsyncMock()
    mock_db.delete = AsyncMock()
    mock_db.commit = AsyncMock()

    game_result = MagicMock()
    game_result.scalar_one_or_none = MagicMock(return_value=mock_game)

    user = MagicMock(spec=User)
    user.id = str(uuid4())
    user_result = MagicMock()
    user_result.scalar_one_or_none = MagicMock(return_value=user)

    participant_result = MagicMock()
    participant_result.scalar_one_or_none = MagicMock(return_value=mock_participant)

    count_result = MagicMock()
    count_result.scalar_one_or_none = MagicMock(return_value=1)

    notif_result = MagicMock()
    notif_result.scalar_one_or_none = MagicMock(return_value=unsent_notification)

    upsert_result = MagicMock()
    notify_result = MagicMock()

    mock_db.execute = AsyncMock(
        side_effect=[
            game_result,
            user_result,
            participant_result,
            count_result,
            notif_result,
            upsert_result,
            notify_result,
        ]
    )
    return mock_db


def _patch_db(mock_db):
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=mock_db)
    ctx.__aexit__ = AsyncMock(return_value=False)
    return patch("services.bot.handlers.leave_game.get_db_session", return_value=ctx)


@pytest.mark.asyncio
async def test_leave_sends_dm_when_join_was_already_sent(
    mock_game, mock_participant, mock_interaction, game_id
):
    """Leave DM is sent when no unsent join notification exists (join DM was delivered)."""
    mock_db = _make_mock_db(mock_participant, mock_game, unsent_notification=None)

    with _patch_db(mock_db):
        await handle_leave_game(mock_interaction, game_id)

    mock_interaction.user.send.assert_called_once()
    sent_content = (
        mock_interaction.user.send.call_args.kwargs.get("content")
        or mock_interaction.user.send.call_args.args[0]
    )
    assert mock_game.title in sent_content


@pytest.mark.asyncio
async def test_leave_suppresses_dm_when_join_not_yet_sent(
    mock_game, mock_participant, mock_interaction, game_id
):
    """No leave DM is sent when an unsent join notification still exists."""
    unsent = MagicMock(spec=NotificationSchedule)
    unsent.sent = False
    mock_db = _make_mock_db(mock_participant, mock_game, unsent_notification=unsent)

    with _patch_db(mock_db):
        await handle_leave_game(mock_interaction, game_id)

    mock_interaction.user.send.assert_not_called()


@pytest.mark.asyncio
async def test_leave_deletes_participant_regardless_of_notification(
    mock_game, mock_participant, mock_interaction, game_id
):
    """Participant is always deleted even when the leave DM is suppressed."""
    unsent = MagicMock(spec=NotificationSchedule)
    unsent.sent = False
    mock_db = _make_mock_db(mock_participant, mock_game, unsent_notification=unsent)

    with _patch_db(mock_db):
        await handle_leave_game(mock_interaction, game_id)

    mock_db.delete.assert_called_once_with(mock_participant)
    assert mock_db.commit.call_count == 1


@pytest.mark.asyncio
async def test_leave_notifies_sse_regardless_of_notification(
    mock_game, mock_participant, mock_interaction, game_id
):
    """MRQ upsert and pg_notify are always executed even when leave DM is suppressed."""
    unsent = MagicMock(spec=NotificationSchedule)
    unsent.sent = False
    mock_db = _make_mock_db(mock_participant, mock_game, unsent_notification=unsent)

    with _patch_db(mock_db):
        await handle_leave_game(mock_interaction, game_id)

    notify_calls = [
        call for call in mock_db.execute.call_args_list if "game_updated_sse" in str(call.args[0])
    ]
    assert len(notify_calls) >= 1, "Expected pg_notify('game_updated_sse', ...) call"


# ---------------------------------------------------------------------------
# HOST_ADDED leave — host DM notification (TDD RED)
# ---------------------------------------------------------------------------

HOST_DISCORD_ID = "999888777"
HOST_CHANNEL_ID = "111222333"
HOST_GUILD_DISCORD_ID = "444555666"
HOST_MESSAGE_ID = "777888999"


def _make_host_added_game(game_id: str) -> MagicMock:
    game = MagicMock(spec=GameSession)
    game.id = game_id
    game.title = "Leave Test Game"
    game.guild_id = "guild-db-uuid-42"
    game.status = "SCHEDULED"
    game.message_id = HOST_MESSAGE_ID
    game.scheduled_at = MagicMock()
    game.scheduled_at.timestamp.return_value = 1700000000.0
    host = MagicMock()
    host.discord_id = HOST_DISCORD_ID
    game.host = host
    channel = MagicMock()
    channel.channel_id = HOST_CHANNEL_ID
    game.channel = channel
    guild = MagicMock()
    guild.guild_id = HOST_GUILD_DISCORD_ID
    game.guild = guild
    return game


def _make_host_added_participant(participant_db_id: str, game_id: str) -> MagicMock:
    participant = MagicMock(spec=GameParticipant)
    participant.id = participant_db_id
    participant.game_session_id = game_id
    participant.position_type = ParticipantType.HOST_ADDED
    participant.user = MagicMock(spec=User)
    participant.user.discord_id = USER_DISCORD_ID
    return participant


def _make_host_added_interaction() -> MagicMock:
    interaction = MagicMock(spec=discord.Interaction)
    interaction.user = MagicMock()
    interaction.user.id = int(USER_DISCORD_ID)
    interaction.user.send = AsyncMock()
    interaction.response = MagicMock()
    interaction.response.is_done = MagicMock(return_value=False)
    interaction.response.defer = AsyncMock()
    interaction.followup = MagicMock()
    interaction.followup.send = AsyncMock()
    interaction.client = MagicMock()
    return interaction


def _make_host_added_mock_db(participant: MagicMock, game: MagicMock) -> MagicMock:
    mock_db = AsyncMock()
    mock_db.delete = AsyncMock()
    mock_db.commit = AsyncMock()

    game_result = MagicMock()
    game_result.scalar_one_or_none = MagicMock(return_value=game)

    user = MagicMock(spec=User)
    user.id = str(uuid4())
    user_result = MagicMock()
    user_result.scalar_one_or_none = MagicMock(return_value=user)

    participant_result = MagicMock()
    participant_result.scalar_one_or_none = MagicMock(return_value=participant)

    count_result = MagicMock()
    count_result.scalar_one_or_none = MagicMock(return_value=2)

    notif_result = MagicMock()
    notif_result.scalar_one_or_none = MagicMock(return_value=None)

    upsert_result = MagicMock()
    notify_result = MagicMock()

    mock_db.execute = AsyncMock(
        side_effect=[
            game_result,
            user_result,
            participant_result,
            count_result,
            notif_result,
            upsert_result,
            notify_result,
        ]
    )
    return mock_db


@pytest.mark.asyncio
async def test_host_added_leave_sends_dm_to_host(game_id, participant_db_id):
    """HOST_ADDED participant leaves → host receives a DM matching host_added_dropout."""
    game = _make_host_added_game(game_id)
    participant = _make_host_added_participant(participant_db_id, game_id)
    interaction = _make_host_added_interaction()

    mock_host_user = MagicMock()
    mock_host_user.send = AsyncMock()
    interaction.client.get_user.return_value = mock_host_user

    mock_db = _make_host_added_mock_db(participant, game)

    with _patch_db(mock_db):
        await handle_leave_game(interaction, game_id)

    mock_host_user.send.assert_awaited_once()
    sent_content = mock_host_user.send.call_args.args[0]
    predicate = DMPredicates.host_added_dropout(game.title)
    assert predicate(MagicMock(content=sent_content)), (
        f"Sent DM did not match host_added_dropout predicate: {sent_content!r}"
    )


@pytest.mark.asyncio
async def test_non_host_added_leave_does_not_send_host_dm(game_id, participant_db_id):
    """SELF_ADDED participant leaves → get_user is never called for host notification."""
    game = _make_host_added_game(game_id)
    participant = _make_host_added_participant(participant_db_id, game_id)
    participant.position_type = ParticipantType.SELF_ADDED

    interaction = _make_host_added_interaction()

    mock_db = _make_host_added_mock_db(participant, game)

    with _patch_db(mock_db):
        await handle_leave_game(interaction, game_id)

    interaction.client.get_user.assert_not_called()


@pytest.mark.asyncio
async def test_host_added_leave_no_dm_when_host_not_in_cache(game_id, participant_db_id):
    """HOST_ADDED participant leaves, host not in Discord cache → no exception, leave succeeds."""
    game = _make_host_added_game(game_id)
    participant = _make_host_added_participant(participant_db_id, game_id)
    interaction = _make_host_added_interaction()

    interaction.client.get_user.return_value = None

    mock_db = _make_host_added_mock_db(participant, game)

    with _patch_db(mock_db):
        await handle_leave_game(interaction, game_id)

    notify_calls = [
        call for call in mock_db.execute.call_args_list if "game_updated_sse" in str(call.args[0])
    ]
    assert len(notify_calls) >= 1, (
        "Expected pg_notify('game_updated_sse', ...) even when host not in cache"
    )


# ---------------------------------------------------------------------------
# Phase 7 TDD — xfail tests for direct DB operations (no publisher)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_leave_game_executes_message_refresh_upsert(
    mock_game, mock_participant, mock_interaction, game_id
):
    """After leave, db.execute is called for the MessageRefreshQueue upsert (no publisher)."""
    mock_db = _make_mock_db(mock_participant, mock_game)

    with _patch_db(mock_db):
        await handle_leave_game(mock_interaction, game_id)

    upsert_calls = [
        call
        for call in mock_db.execute.call_args_list
        if "message_refresh_queue" in str(call.args[0]).lower()
    ]
    assert len(upsert_calls) >= 1, "Expected db.execute call for MessageRefreshQueue upsert"


@pytest.mark.asyncio
async def test_leave_game_executes_pg_notify(
    mock_game, mock_participant, mock_interaction, game_id
):
    """After leave, db.execute is called with pg_notify('game_updated_sse', ...) (no publisher)."""
    mock_db = _make_mock_db(mock_participant, mock_game)

    with _patch_db(mock_db):
        await handle_leave_game(mock_interaction, game_id)

    notify_calls = [
        call for call in mock_db.execute.call_args_list if "game_updated_sse" in str(call.args[0])
    ]
    assert len(notify_calls) >= 1, (
        "Expected db.execute call with pg_notify('game_updated_sse', ...)"
    )
