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


"""Integration tests for SchedulerLoop against real PostgreSQL.

Each test inserts a due schedule row directly, runs SchedulerLoop for up to
five seconds, and asserts that the bot_action_queue row was written and the
schedule row was marked as processed.  No scheduler container is needed — the
loop runs in-process inside the test runner.
"""

import asyncio
import contextlib
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import text

from services.bot.scheduler_loop import SchedulerLoop
from shared.models import GameStatusSchedule, NotificationSchedule, ParticipantActionSchedule
from shared.models.participant import ParticipantType
from shared.services.event_builders import build_notification_event, build_status_transition_event
from shared.services.participant_action_event_builder import build_participant_action_event

pytestmark = pytest.mark.integration

_RUN_TIMEOUT = 5.0


def _now_minus_one_minute() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None) - timedelta(minutes=1)


def _insert_participant(admin_db_sync, game_id: str, user_id: str) -> str:
    participant_id = str(uuid4())
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
            "position_type": int(ParticipantType.HOST_ADDED),
        },
    )
    admin_db_sync.commit()
    return participant_id


@pytest.mark.asyncio
async def test_notification_schedule_due_item_enqueued(
    admin_db_sync,
    bot_db_url,
    test_game_environment,
):
    """SchedulerLoop writes a notification_due row and marks notification_schedule.sent=True."""
    env = test_game_environment()
    game_id = env["game"]["id"]

    notif_id = str(uuid4())
    admin_db_sync.execute(
        text(
            "INSERT INTO notification_schedule "
            "(id, game_id, reminder_minutes, notification_time, game_scheduled_at, sent) "
            "VALUES (:id, :game_id, :reminder_minutes, :notification_time, "
            ":game_scheduled_at, :sent)"
        ),
        {
            "id": notif_id,
            "game_id": game_id,
            "reminder_minutes": 60,
            "notification_time": _now_minus_one_minute(),
            "game_scheduled_at": datetime.now(UTC).replace(tzinfo=None) + timedelta(hours=1),
            "sent": False,
        },
    )
    admin_db_sync.commit()

    loop = SchedulerLoop(
        db_url=bot_db_url,
        notify_channel="notification_schedule_changed",
        model_class=NotificationSchedule,
        time_field="notification_time",
        status_field="sent",
        event_builder=build_notification_event,
    )

    try:
        with contextlib.suppress(asyncio.TimeoutError):
            await asyncio.wait_for(loop.run(), timeout=_RUN_TIMEOUT)

        row = admin_db_sync.execute(
            text("SELECT action_type, game_id FROM bot_action_queue WHERE game_id = :game_id"),
            {"game_id": game_id},
        ).fetchone()
        assert row is not None, "Expected a bot_action_queue row for the notification"
        assert row[0] == "notification_due"
        assert row[1] == game_id

        sent_row = admin_db_sync.execute(
            text("SELECT sent FROM notification_schedule WHERE id = :id"),
            {"id": notif_id},
        ).fetchone()
        assert sent_row is not None
        assert sent_row[0] is True, "notification_schedule.sent should be True"
    finally:
        admin_db_sync.execute(
            text("DELETE FROM bot_action_queue WHERE game_id = :game_id"),
            {"game_id": game_id},
        )
        admin_db_sync.commit()


@pytest.mark.asyncio
async def test_status_transition_due_item_enqueued(
    admin_db_sync,
    bot_db_url,
    test_game_environment,
):
    """SchedulerLoop writes a status_transition_due row and marks
    game_status_schedule.executed=True.
    """
    env = test_game_environment()
    game_id = env["game"]["id"]

    schedule_id = str(uuid4())
    admin_db_sync.execute(
        text(
            "INSERT INTO game_status_schedule "
            "(id, game_id, target_status, transition_time, executed) "
            "VALUES (:id, :game_id, :target_status, :transition_time, :executed)"
        ),
        {
            "id": schedule_id,
            "game_id": game_id,
            "target_status": "in_progress",
            "transition_time": _now_minus_one_minute(),
            "executed": False,
        },
    )
    admin_db_sync.commit()

    loop = SchedulerLoop(
        db_url=bot_db_url,
        notify_channel="game_status_schedule_changed",
        model_class=GameStatusSchedule,
        time_field="transition_time",
        status_field="executed",
        event_builder=build_status_transition_event,
    )

    try:
        with contextlib.suppress(asyncio.TimeoutError):
            await asyncio.wait_for(loop.run(), timeout=_RUN_TIMEOUT)

        row = admin_db_sync.execute(
            text("SELECT action_type, game_id FROM bot_action_queue WHERE game_id = :game_id"),
            {"game_id": game_id},
        ).fetchone()
        assert row is not None, "Expected a bot_action_queue row for the status transition"
        assert row[0] == "status_transition_due"
        assert row[1] == game_id

        exec_row = admin_db_sync.execute(
            text("SELECT executed FROM game_status_schedule WHERE id = :id"),
            {"id": schedule_id},
        ).fetchone()
        assert exec_row is not None
        assert exec_row[0] is True, "game_status_schedule.executed should be True"
    finally:
        admin_db_sync.execute(
            text("DELETE FROM bot_action_queue WHERE game_id = :game_id"),
            {"game_id": game_id},
        )
        admin_db_sync.commit()


@pytest.mark.asyncio
async def test_participant_action_due_item_enqueued(
    admin_db_sync,
    bot_db_url,
    test_game_environment,
):
    """SchedulerLoop writes a participant_drop_due row and marks
    participant_action_schedule.processed=True.
    """
    env = test_game_environment()
    game_id = env["game"]["id"]
    user_id = env["user"]["id"]

    participant_id = _insert_participant(admin_db_sync, game_id, user_id)

    action_id = str(uuid4())
    admin_db_sync.execute(
        text(
            "INSERT INTO participant_action_schedule "
            "(id, game_id, participant_id, action, action_time, processed) "
            "VALUES (:id, :game_id, :participant_id, :action, :action_time, :processed)"
        ),
        {
            "id": action_id,
            "game_id": game_id,
            "participant_id": participant_id,
            "action": "drop",
            "action_time": _now_minus_one_minute(),
            "processed": False,
        },
    )
    admin_db_sync.commit()

    loop = SchedulerLoop(
        db_url=bot_db_url,
        notify_channel="participant_action_schedule_changed",
        model_class=ParticipantActionSchedule,
        time_field="action_time",
        status_field="processed",
        event_builder=build_participant_action_event,
    )

    try:
        with contextlib.suppress(asyncio.TimeoutError):
            await asyncio.wait_for(loop.run(), timeout=_RUN_TIMEOUT)

        row = admin_db_sync.execute(
            text("SELECT action_type, game_id FROM bot_action_queue WHERE game_id = :game_id"),
            {"game_id": game_id},
        ).fetchone()
        assert row is not None, "Expected a bot_action_queue row for the participant action"
        assert row[0] == "participant_drop_due"
        assert row[1] == game_id

        proc_row = admin_db_sync.execute(
            text("SELECT processed FROM participant_action_schedule WHERE id = :id"),
            {"id": action_id},
        ).fetchone()
        assert proc_row is not None
        assert proc_row[0] is True, "participant_action_schedule.processed should be True"
    finally:
        admin_db_sync.execute(
            text("DELETE FROM bot_action_queue WHERE game_id = :game_id"),
            {"game_id": game_id},
        )
        admin_db_sync.commit()
