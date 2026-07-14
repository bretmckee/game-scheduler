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

import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import discord
import pytest

from services.bot.handlers.leave_game import handle_leave_game
from shared.message_formats import DMPredicates
from shared.models.bot_action_queue import BotActionQueue
from shared.models.game import GameSession
from shared.models.notification_schedule import NotificationSchedule
from shared.models.participant import GameParticipant, ParticipantType
from shared.models.signup_method import SignupMethod
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
    game.max_players = 5
    game.signup_method = SignupMethod.SELF_SIGNUP
    game.host = None
    return game


@pytest.fixture
def mock_participant(participant_db_id, mock_game):
    participant = MagicMock(spec=GameParticipant)
    participant.id = participant_db_id
    participant.game_session_id = mock_game.id
    participant.position_type = ParticipantType.SELF_ADDED
    participant.position = 0
    participant.joined_at = datetime.datetime(2026, 1, 1, tzinfo=datetime.UTC)
    participant.user = MagicMock(spec=User)
    participant.user.discord_id = USER_DISCORD_ID
    mock_game.participants = [participant]
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
    mock_db.flush = AsyncMock()
    mock_db.refresh = AsyncMock()
    mock_db.add = MagicMock()
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
    game.max_players = 5
    game.signup_method = SignupMethod.SELF_SIGNUP
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
    participant.position = 0
    participant.joined_at = datetime.datetime(2026, 1, 1, tzinfo=datetime.UTC)
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
    mock_db.flush = AsyncMock()
    mock_db.refresh = AsyncMock()
    mock_db.add = MagicMock()
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
    """HOST_ADDED participant leaves → a host_added_dropout DM is enqueued via BotActionQueue."""
    game = _make_host_added_game(game_id)
    participant = _make_host_added_participant(participant_db_id, game_id)
    game.participants = [participant]
    interaction = _make_host_added_interaction()

    mock_db = _make_host_added_mock_db(participant, game)

    with _patch_db(mock_db):
        await handle_leave_game(interaction, game_id)

    added = [c.args[0] for c in mock_db.add.call_args_list]
    dropout_rows = [
        r
        for r in added
        if isinstance(r, BotActionQueue)
        and r.payload.get("notification_type") == "host_added_dropout"
    ]
    assert len(dropout_rows) == 1
    row = dropout_rows[0]
    assert row.action_type == "send_dm"
    assert row.discord_id == HOST_DISCORD_ID
    predicate = DMPredicates.host_added_dropout(game.title)
    assert predicate(MagicMock(content=row.payload["message"])), (
        f"Enqueued DM did not match host_added_dropout predicate: {row.payload['message']!r}"
    )


@pytest.mark.asyncio
async def test_non_host_added_leave_does_not_send_host_dm(game_id, participant_db_id):
    """SELF_ADDED participant leaves → no host_added_dropout row is enqueued."""
    game = _make_host_added_game(game_id)
    participant = _make_host_added_participant(participant_db_id, game_id)
    participant.position_type = ParticipantType.SELF_ADDED
    game.participants = [participant]

    interaction = _make_host_added_interaction()

    mock_db = _make_host_added_mock_db(participant, game)

    with _patch_db(mock_db):
        await handle_leave_game(interaction, game_id)

    added = [c.args[0] for c in mock_db.add.call_args_list]
    dropout_rows = [
        r
        for r in added
        if isinstance(r, BotActionQueue)
        and r.payload.get("notification_type") == "host_added_dropout"
    ]
    assert len(dropout_rows) == 0
    interaction.client.get_user.assert_not_called()


@pytest.mark.asyncio
async def test_host_added_leave_dm_independent_of_gateway_cache(game_id, participant_db_id):
    """HOST_ADDED leave enqueues the dropout DM without ever touching the gateway user cache.

    Delivery moved from a live discord.Client.get_user() lookup to a durable
    BotActionQueue row built from the DB-loaded game.host relationship, so a
    host missing from the bot's gateway cache no longer suppresses the DM.
    """
    game = _make_host_added_game(game_id)
    participant = _make_host_added_participant(participant_db_id, game_id)
    game.participants = [participant]
    interaction = _make_host_added_interaction()

    mock_db = _make_host_added_mock_db(participant, game)

    with _patch_db(mock_db):
        await handle_leave_game(interaction, game_id)

    added = [c.args[0] for c in mock_db.add.call_args_list]
    dropout_rows = [
        r
        for r in added
        if isinstance(r, BotActionQueue)
        and r.payload.get("notification_type") == "host_added_dropout"
    ]
    assert len(dropout_rows) == 1, "Dropout DM must be enqueued regardless of gateway cache state"
    interaction.client.get_user.assert_not_called()


# ---------------------------------------------------------------------------
# Confirmed leave promotes a waitlisted participant (TDD RED)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_confirmed_leave_promotes_waitlisted_participant(game_id, participant_db_id):
    """A confirmed HOST_ADDED leaver frees a slot, promoting a waitlisted HOST_ADDED user."""
    game = _make_host_added_game(game_id)
    game.max_players = 1
    game.signup_method = SignupMethod.HOST_SELECTED_WITH_WAITLIST

    leaver = _make_host_added_participant(participant_db_id, game_id)

    waitlisted_discord_id = "waitlisted-discord-id"
    waitlisted = MagicMock(spec=GameParticipant)
    waitlisted.id = str(uuid4())
    waitlisted.game_session_id = game_id
    waitlisted.position_type = ParticipantType.HOST_ADDED
    waitlisted.position = 1
    waitlisted.joined_at = datetime.datetime(2026, 1, 2, tzinfo=datetime.UTC)
    waitlisted.user = MagicMock(spec=User)
    waitlisted.user.discord_id = waitlisted_discord_id

    game.participants = [leaver, waitlisted]

    interaction = _make_host_added_interaction()
    mock_db = _make_host_added_mock_db(leaver, game)

    async def refresh_side_effect(g: MagicMock, attribute_names: list[str] | None = None) -> None:
        g.participants = [waitlisted]

    mock_db.refresh = AsyncMock(side_effect=refresh_side_effect)

    with _patch_db(mock_db):
        await handle_leave_game(interaction, game_id)

    added = [c.args[0] for c in mock_db.add.call_args_list]
    promotion_rows = [
        r
        for r in added
        if isinstance(r, BotActionQueue)
        and r.payload.get("notification_type") == "waitlist_promotion"
    ]
    assert len(promotion_rows) == 1
    assert promotion_rows[0].discord_id == waitlisted_discord_id


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
