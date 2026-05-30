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
from shared.services.game_schedules import (
    _create_status_schedules,
    _populate_reminder_schedule,
    _schedule_join_notifications,
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
async def test_setup_game_schedules_delegates_to_all_three_helpers(db, game):
    """setup_game_schedules must call all three helper functions."""
    with (
        patch(
            "shared.services.game_schedules._schedule_join_notifications", new=AsyncMock()
        ) as mock_join,
        patch(
            "shared.services.game_schedules._populate_reminder_schedule", new=AsyncMock()
        ) as mock_reminder,
        patch("shared.services.game_schedules._create_status_schedules") as mock_status,
    ):
        await setup_game_schedules(db, game, reminder_minutes=[30], expected_duration_minutes=90)

    mock_join.assert_awaited_once_with(db, game)
    mock_reminder.assert_awaited_once_with(db, game, [30])
    mock_status.assert_called_once_with(db, game, 90)


@pytest.mark.asyncio
async def test_schedule_join_notifications_adds_entry_for_confirmed_participant_with_user_id(
    db, game
):
    """A confirmed participant with a user_id must get a join-notification entry."""
    participant = MagicMock()
    participant.id = "participant-1"
    participant.user_id = "user-1"

    partitioned = MagicMock()
    partitioned.confirmed = [participant]

    with (
        patch("shared.services.game_schedules.partition_participants", return_value=partitioned),
        patch(
            "shared.services.game_schedules.utc_now",
            return_value=datetime.datetime(2026, 1, 1, 12, 0, 0, tzinfo=datetime.UTC).replace(
                tzinfo=None
            ),
        ),
    ):
        await _schedule_join_notifications(db, game)

    db.add.assert_called_once()
    added = db.add.call_args[0][0]
    assert isinstance(added, ns_model.NotificationSchedule)
    assert added.game_id == "game-1"
    assert added.participant_id == "participant-1"
    assert added.notification_type == "join_notification"
    assert added.sent is False
    db.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_schedule_join_notifications_skips_participant_without_user_id(db, game):
    """Participants without a user_id must not produce a notification entry."""
    participant = MagicMock()
    participant.user_id = None

    partitioned = MagicMock()
    partitioned.confirmed = [participant]

    with patch("shared.services.game_schedules.partition_participants", return_value=partitioned):
        await _schedule_join_notifications(db, game)

    db.add.assert_not_called()


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
