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


"""Unit tests for GameService._system_clone_for_recurrence (Phase 4 RED stubs)."""

import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.api.services.games import GameService
from shared.models import game as game_model
from shared.models import participant as participant_model
from shared.models.signup_method import SignupMethod

SCHEDULED_AT = datetime.datetime(2026, 6, 1, 18, 0, 0, tzinfo=datetime.UTC)
NEXT_AT = datetime.datetime(2026, 7, 1, 18, 0, 0, tzinfo=datetime.UTC)
RRULE = "FREQ=MONTHLY;COUNT=12"


@pytest.fixture
def confirmed_player():
    p = MagicMock(spec=participant_model.GameParticipant)
    p.user_id = "player-uuid"
    p.display_name = None
    p.position_type = participant_model.ParticipantType.HOST_ADDED
    p.position = 1
    p.user = MagicMock()
    p.user.discord_id = "player-discord"
    return p


@pytest.fixture
def source_game(confirmed_player):
    game = MagicMock(spec=game_model.GameSession)
    game.id = "source-uuid"
    game.title = "Monthly Game"
    game.description = "Happens monthly"
    game.signup_instructions = "Sign up here"
    game.scheduled_at = SCHEDULED_AT.replace(tzinfo=None)
    game.where = "Discord"
    game.max_players = 4
    game.template_id = "tmpl-uuid"
    game.guild_id = "guild-db-uuid"
    game.channel_id = "chan-db-uuid"
    game.host_id = "host-db-uuid"
    game.reminder_minutes = [30, 10]
    game.notify_role_ids = ["role-1"]
    game.allowed_player_role_ids = None
    game.expected_duration_minutes = 90
    game.status = game_model.GameStatus.COMPLETED.value
    game.signup_method = SignupMethod.SELF_SIGNUP.value
    game.thumbnail_id = None
    game.banner_image_id = None
    game.message_id = "discord-msg-id"
    game.recur_rule = RRULE
    game.remind_host_rewards = False
    game.rewards = None
    game.participants = [confirmed_player]
    return game


@pytest.fixture
def game_service():
    db = AsyncMock()
    db.flush = AsyncMock()
    db.add = MagicMock()
    event_publisher = MagicMock()
    event_publisher.publish_deferred = MagicMock()
    return GameService(
        db=db,
        event_publisher=event_publisher,
        discord_client=AsyncMock(),
        participant_resolver=AsyncMock(),
        channel_resolver=AsyncMock(),
    )


@pytest.mark.asyncio
@pytest.mark.xfail(strict=True, reason="Phase 4 RED — not yet implemented")
async def test_system_clone_sets_post_at_none(game_service, source_game):
    """Clone created by _system_clone_for_recurrence must have post_at=None."""
    with patch.object(game_service, "_create_game_status_schedules", new=AsyncMock()):
        await game_service._system_clone_for_recurrence(game_service.db, source_game, NEXT_AT)

    add_calls = game_service.db.add.call_args_list
    game_calls = [c[0][0] for c in add_calls if isinstance(c[0][0], game_model.GameSession)]
    assert len(game_calls) == 1
    assert game_calls[0].post_at is None


@pytest.mark.asyncio
@pytest.mark.xfail(strict=True, reason="Phase 4 RED — not yet implemented")
async def test_system_clone_copies_recur_rule(game_service, source_game):
    """Clone must inherit recur_rule from source."""
    with patch.object(game_service, "_create_game_status_schedules", new=AsyncMock()):
        await game_service._system_clone_for_recurrence(game_service.db, source_game, NEXT_AT)

    add_calls = game_service.db.add.call_args_list
    game_calls = [c[0][0] for c in add_calls if isinstance(c[0][0], game_model.GameSession)]
    assert len(game_calls) == 1
    assert game_calls[0].recur_rule == RRULE


@pytest.mark.asyncio
@pytest.mark.xfail(strict=True, reason="Phase 4 RED — not yet implemented")
async def test_system_clone_sets_scheduled_at_to_next_at(game_service, source_game):
    """Clone scheduled_at must equal the provided next_at argument."""
    with patch.object(game_service, "_create_game_status_schedules", new=AsyncMock()):
        await game_service._system_clone_for_recurrence(game_service.db, source_game, NEXT_AT)

    add_calls = game_service.db.add.call_args_list
    game_calls = [c[0][0] for c in add_calls if isinstance(c[0][0], game_model.GameSession)]
    assert len(game_calls) == 1
    assert game_calls[0].scheduled_at == NEXT_AT.replace(tzinfo=None)


@pytest.mark.asyncio
@pytest.mark.xfail(strict=True, reason="Phase 4 RED — not yet implemented")
async def test_system_clone_carries_over_confirmed_players(
    game_service, source_game, confirmed_player
):
    """Confirmed participants must be copied to the clone."""
    with patch.object(game_service, "_create_game_status_schedules", new=AsyncMock()):
        await game_service._system_clone_for_recurrence(game_service.db, source_game, NEXT_AT)

    add_calls = game_service.db.add.call_args_list
    participant_calls = [
        c[0][0] for c in add_calls if isinstance(c[0][0], participant_model.GameParticipant)
    ]
    assert len(participant_calls) == 1
    assert participant_calls[0].user_id == confirmed_player.user_id


@pytest.mark.asyncio
@pytest.mark.xfail(strict=True, reason="Phase 4 RED — not yet implemented")
async def test_system_clone_does_not_publish_game_created(game_service, source_game):
    """_publish_game_created must NOT be called (no Discord event at clone time)."""
    with (
        patch.object(game_service, "_create_game_status_schedules", new=AsyncMock()),
        patch.object(game_service, "_publish_game_created", new=AsyncMock()) as mock_publish,
    ):
        await game_service._system_clone_for_recurrence(game_service.db, source_game, NEXT_AT)

    mock_publish.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.xfail(strict=True, reason="Phase 4 RED — not yet implemented")
async def test_system_clone_creates_status_schedules(game_service, source_game):
    """_create_game_status_schedules must be called for the new clone."""
    with patch.object(
        game_service, "_create_game_status_schedules", new=AsyncMock()
    ) as mock_schedules:
        await game_service._system_clone_for_recurrence(game_service.db, source_game, NEXT_AT)

    mock_schedules.assert_called_once()
    call_args = mock_schedules.call_args
    assert isinstance(call_args[0][0], game_model.GameSession)
    assert call_args[0][1] == source_game.expected_duration_minutes
