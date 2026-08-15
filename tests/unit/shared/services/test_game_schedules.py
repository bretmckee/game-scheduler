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


"""Unit tests for shared.services.game_schedules."""

import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from shared.models import game as game_model
from shared.models import notification_schedule as ns_model
from shared.models import participant as participant_model
from shared.models.signup_method import SignupMethod
from shared.services.game_schedules import (
    _create_status_schedules,
    _populate_reminder_schedule,
    schedule_join_notification,
    schedule_join_notifications_for_game,
    setup_game_schedules,
)
from shared.utils.status_transitions import GameStatus

_FUTURE_SCHEDULED_AT = datetime.datetime(2099, 12, 1, 18, 0, 0, tzinfo=datetime.UTC).replace(
    tzinfo=None
)


@pytest.fixture
def db():
    mock_db = MagicMock()
    mock_db.add = MagicMock()
    mock_db.flush = AsyncMock()
    return mock_db


@pytest.fixture
def game():
    g = MagicMock(spec=game_model.GameSession)
    g.id = "game-1"
    g.max_players = 4
    g.scheduled_at = _FUTURE_SCHEDULED_AT
    g.status = GameStatus.SCHEDULED.value
    g.participants = []
    return g


@pytest.mark.asyncio
async def test_schedule_join_notification_adds_and_returns_entry(db):
    """The primitive must add a join_notification row and return that same object."""
    result = await schedule_join_notification(
        db,
        game_id="game-1",
        participant_id="participant-1",
        game_scheduled_at=_FUTURE_SCHEDULED_AT,
        delay_seconds=60,
    )

    db.add.assert_called_once()
    added = db.add.call_args[0][0]
    assert isinstance(added, ns_model.NotificationSchedule)
    assert added.game_id == "game-1"
    assert added.participant_id == "participant-1"
    assert added.notification_type == "join_notification"
    assert added.sent is False
    assert added.game_scheduled_at == _FUTURE_SCHEDULED_AT
    assert added.reminder_minutes is None
    db.flush.assert_awaited_once()
    assert result is added


@pytest.mark.asyncio
async def test_schedule_join_notification_uses_default_delay(db):
    """Omitting delay_seconds must schedule the notification 60 seconds out."""
    fixed_now = datetime.datetime(2026, 1, 1, 12, 0, 0, tzinfo=datetime.UTC).replace(tzinfo=None)

    with patch("shared.services.game_schedules.utc_now", return_value=fixed_now):
        result = await schedule_join_notification(
            db,
            game_id="game-1",
            participant_id="participant-1",
            game_scheduled_at=_FUTURE_SCHEDULED_AT,
        )

    expected_notification_time = fixed_now + datetime.timedelta(seconds=60)
    assert result.notification_time == expected_notification_time


@pytest.mark.asyncio
async def test_setup_game_schedules_delegates_to_helpers(db, game):
    """setup_game_schedules must call join-notification and reminder helpers."""
    with (
        patch(
            "shared.services.game_schedules.schedule_join_notifications_for_game", new=AsyncMock()
        ) as mock_join,
        patch(
            "shared.services.game_schedules._populate_reminder_schedule", new=AsyncMock()
        ) as mock_reminder,
    ):
        await setup_game_schedules(db, game, reminder_minutes=[30])

    mock_join.assert_awaited_once_with(db, game)
    mock_reminder.assert_awaited_once_with(db, game, [30])


@pytest.mark.asyncio
async def test_schedule_join_notifications_for_game_delegates_for_confirmed_participant(db, game):
    """A participant with a user_id must be scheduled via the shared primitive."""
    participant = MagicMock()
    participant.id = "participant-1"
    participant.user_id = "user-1"
    game.participants = [participant]

    with patch(
        "shared.services.game_schedules.schedule_join_notification", new=AsyncMock()
    ) as mock_schedule:
        await schedule_join_notifications_for_game(db, game)

    mock_schedule.assert_called_once_with(
        db=db,
        game_id=game.id,
        participant_id=participant.id,
        game_scheduled_at=game.scheduled_at,
        delay_seconds=60,
    )


@pytest.mark.asyncio
async def test_schedule_join_notifications_skips_participant_without_user_id(db, game):
    """Participants without a user_id must not produce a notification entry."""
    participant = MagicMock()
    participant.user_id = None
    game.participants = [participant]

    with patch(
        "shared.services.game_schedules.schedule_join_notification", new=AsyncMock()
    ) as mock_schedule:
        await schedule_join_notifications_for_game(db, game)

    mock_schedule.assert_not_called()


@pytest.mark.asyncio
async def test_schedule_join_notifications_for_game_includes_overflow_participant(db, game):
    """Waitlisted (overflow) participants must be scheduled, not just confirmed ones."""
    game.max_players = 1
    game.signup_method = SignupMethod.SELF_SIGNUP
    joined_at = datetime.datetime(2026, 1, 1, tzinfo=datetime.UTC)
    confirmed_participant = MagicMock()
    confirmed_participant.id = "participant-confirmed"
    confirmed_participant.user_id = "user-confirmed"
    confirmed_participant.position_type = participant_model.ParticipantType.SELF_ADDED
    confirmed_participant.position = 1
    confirmed_participant.joined_at = joined_at
    overflow_participant = MagicMock()
    overflow_participant.id = "participant-overflow"
    overflow_participant.user_id = "user-overflow"
    overflow_participant.position_type = participant_model.ParticipantType.SELF_ADDED
    overflow_participant.position = 2
    overflow_participant.joined_at = joined_at
    game.participants = [confirmed_participant, overflow_participant]

    with patch(
        "shared.services.game_schedules.schedule_join_notification", new=AsyncMock()
    ) as mock_schedule:
        await schedule_join_notifications_for_game(db, game)

    assert mock_schedule.call_count == 2


@pytest.mark.asyncio
async def test_populate_reminder_schedule_skips_empty_list(db, game):
    """Empty reminder_minutes list must cause an early return with no DB writes."""
    await _populate_reminder_schedule(db, game, reminder_minutes=[])

    db.add.assert_not_called()


@pytest.mark.asyncio
async def test_populate_reminder_schedule_adds_entry_for_future_reminder(db, game):
    """A reminder whose notification_time is in the future must be added to the DB."""
    await _populate_reminder_schedule(db, game, reminder_minutes=[30])

    db.add.assert_called_once()
    added = db.add.call_args[0][0]
    assert isinstance(added, ns_model.NotificationSchedule)
    assert added.reminder_minutes == 30
    assert added.sent is False


@pytest.mark.asyncio
async def test_populate_reminder_schedule_skips_past_reminder(db, game):
    """A reminder whose notification_time is in the past must not be added."""
    past_scheduled_at = datetime.datetime(2020, 1, 1, 18, 0, 0, tzinfo=datetime.UTC).replace(
        tzinfo=None
    )
    game.scheduled_at = past_scheduled_at

    await _populate_reminder_schedule(db, game, reminder_minutes=[30])

    db.add.assert_not_called()


def test_create_status_schedules_adds_in_progress_and_completed_entries(db, game):
    """SCHEDULED game must get both IN_PROGRESS and COMPLETED status entries."""
    _create_status_schedules(db, game, expected_duration_minutes=90)

    assert db.add.call_count == 2
    added_statuses = {call[0][0].target_status for call in db.add.call_args_list}
    assert GameStatus.IN_PROGRESS.value in added_statuses
    assert GameStatus.COMPLETED.value in added_statuses

    completed = next(
        call[0][0]
        for call in db.add.call_args_list
        if call[0][0].target_status == GameStatus.COMPLETED.value
    )
    expected_completion = _FUTURE_SCHEDULED_AT + datetime.timedelta(minutes=90)
    assert completed.transition_time == expected_completion


def test_create_status_schedules_uses_default_duration_when_none(db, game):
    """When expected_duration_minutes is None, the 60-minute default must be used."""
    _create_status_schedules(db, game, expected_duration_minutes=None)

    completed = next(
        call[0][0]
        for call in db.add.call_args_list
        if call[0][0].target_status == GameStatus.COMPLETED.value
    )
    expected_completion = _FUTURE_SCHEDULED_AT + datetime.timedelta(minutes=60)
    assert completed.transition_time == expected_completion


def test_create_status_schedules_skips_non_scheduled_game(db, game):
    """A game not in SCHEDULED status must not get any status schedule entries."""
    game.status = GameStatus.IN_PROGRESS.value

    _create_status_schedules(db, game, expected_duration_minutes=90)

    db.add.assert_not_called()
