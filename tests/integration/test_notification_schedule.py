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


"""Integration tests for NotificationScheduleService against real PostgreSQL.

Regression coverage for a bug found via a live report: update_schedule's
DELETE was unscoped by notification_type, so refreshing a game's reminder
schedule (e.g. from a host edit that also adds a participant in the same
request) collaterally deleted that participant's join_notification row,
silently dropping their join/waitlist DM.
"""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import select, text

from services.api.services.notification_schedule import NotificationScheduleService
from shared.models.game import GameSession
from shared.models.participant import ParticipantType

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_update_schedule_preserves_join_notification_row(admin_db, test_game_environment):
    """A join_notification row survives update_schedule refreshing reminders.

    Both notification types share the notification_schedule table (see
    NotificationSchedule's docstring); update_schedule's job is only to
    refresh reminder rows, and must not collaterally delete join_notification
    rows for the same game.
    """
    env = test_game_environment()
    game_id = env["game"]["id"]
    user_id = env["user"]["id"]

    participant_id = str(uuid4())
    await admin_db.execute(
        text(
            "INSERT INTO game_participants "
            "(id, game_session_id, user_id, position, position_type, joined_at) "
            "VALUES (:id, :game_id, :user_id, :position, :position_type, :joined_at)"
        ),
        {
            "id": participant_id,
            "game_id": game_id,
            "user_id": user_id,
            "position": 1,
            "position_type": int(ParticipantType.HOST_ADDED),
            "joined_at": datetime.now(UTC).replace(tzinfo=None),
        },
    )

    join_notification_id = str(uuid4())
    scheduled_at = datetime.now(UTC).replace(tzinfo=None) + timedelta(hours=2)
    await admin_db.execute(
        text(
            "INSERT INTO notification_schedule "
            "(id, game_id, participant_id, notification_type, reminder_minutes, "
            "notification_time, game_scheduled_at, sent) "
            "VALUES (:id, :game_id, :participant_id, 'join_notification', 0, "
            ":notification_time, :game_scheduled_at, false)"
        ),
        {
            "id": join_notification_id,
            "game_id": game_id,
            "participant_id": participant_id,
            "notification_time": datetime.now(UTC).replace(tzinfo=None) + timedelta(seconds=60),
            "game_scheduled_at": scheduled_at,
        },
    )
    await admin_db.commit()

    game = (
        await admin_db.execute(select(GameSession).where(GameSession.id == game_id))
    ).scalar_one()
    game.scheduled_at = scheduled_at

    await NotificationScheduleService(admin_db).update_schedule(game, [30])
    await admin_db.commit()

    result = await admin_db.execute(
        text("SELECT notification_type FROM notification_schedule WHERE game_id = :game_id"),
        {"game_id": game_id},
    )
    rows = {row[0] for row in result.fetchall()}
    assert "join_notification" in rows, (
        "join_notification row was collaterally deleted by the reminder refresh"
    )
    assert "reminder" in rows
