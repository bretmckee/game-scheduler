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


"""Shared game schedule setup logic used by both the API service and the bot.

Placing this in shared/ ensures the bot service can call it without importing
from services.api, which is not included in the bot Docker image.
"""

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from shared.models import game as game_model
from shared.models import game_status_schedule as game_status_schedule_model
from shared.models import notification_schedule as notification_schedule_model
from shared.models.base import utc_now
from shared.utils.participant_sorting import partition_participants
from shared.utils.status_transitions import GameStatus

_DEFAULT_GAME_DURATION_MINUTES = 60


async def setup_game_schedules(
    db: AsyncSession,
    game: game_model.GameSession,
    reminder_minutes: list[int],
    expected_duration_minutes: int | None,
) -> None:
    """Set up all game schedules after a game is announced.

    Creates join-notification entries for confirmed participants, populates the
    reminder schedule, and creates status-transition schedule records.

    Does not commit.  The caller is responsible for committing the transaction.

    Args:
        db: Active async database session.
        game: The just-announced GameSession (participants relationship must be loaded).
        reminder_minutes: Minutes before game start at which to send reminders.
        expected_duration_minutes: Game duration for calculating the COMPLETED transition.
    """
    await _schedule_join_notifications(db, game)
    await _populate_reminder_schedule(db, game, reminder_minutes)
    _create_status_schedules(db, game, expected_duration_minutes)


async def _schedule_join_notifications(
    db: AsyncSession,
    game: game_model.GameSession,
) -> None:
    partitioned = partition_participants(
        game.participants, game.max_players, signup_method=game.signup_method
    )
    for participant in partitioned.confirmed:
        if participant.user_id:
            schedule = notification_schedule_model.NotificationSchedule(
                game_id=game.id,
                participant_id=participant.id,
                notification_type="join_notification",
                notification_time=utc_now() + timedelta(seconds=60),
                sent=False,
                game_scheduled_at=game.scheduled_at,
                reminder_minutes=None,
            )
            db.add(schedule)
            await db.flush()


async def _populate_reminder_schedule(
    db: AsyncSession,
    game: game_model.GameSession,
    reminder_minutes: list[int],
) -> None:
    if not reminder_minutes:
        return
    now = datetime.now(UTC).replace(tzinfo=None)
    for reminder_min in reminder_minutes:
        notification_time = game.scheduled_at - timedelta(minutes=reminder_min)
        if notification_time > now:
            db.add(
                notification_schedule_model.NotificationSchedule(
                    game_id=game.id,
                    reminder_minutes=reminder_min,
                    notification_time=notification_time,
                    game_scheduled_at=game.scheduled_at,
                    sent=False,
                )
            )


def _create_status_schedules(
    db: AsyncSession,
    game: game_model.GameSession,
    expected_duration_minutes: int | None,
) -> None:
    if game.status != GameStatus.SCHEDULED.value:
        return

    db.add(
        game_status_schedule_model.GameStatusSchedule(
            id=str(uuid.uuid4()),
            game_id=game.id,
            target_status=GameStatus.IN_PROGRESS.value,
            transition_time=game.scheduled_at,
            executed=False,
        )
    )

    duration = expected_duration_minutes or _DEFAULT_GAME_DURATION_MINUTES
    db.add(
        game_status_schedule_model.GameStatusSchedule(
            id=str(uuid.uuid4()),
            game_id=game.id,
            target_status=GameStatus.COMPLETED.value,
            transition_time=game.scheduled_at + timedelta(minutes=duration),
            executed=False,
        )
    )
