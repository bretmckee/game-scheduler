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
from shared.models import participant as participant_model
from shared.models.base import utc_now
from shared.services.image_storage import increment_image_ref
from shared.utils.participant_sorting import partition_participants
from shared.utils.status_transitions import GameStatus

_DEFAULT_GAME_DURATION_MINUTES = 60


async def schedule_join_notification(
    db: AsyncSession,
    game_id: str,
    participant_id: str,
    game_scheduled_at: datetime | None,
    delay_seconds: int = 60,
) -> notification_schedule_model.NotificationSchedule:
    """
    Schedule delayed join notification for a participant.

    Creates a notification_schedule entry that will trigger a notification
    after the specified delay. If the participant is removed before the
    notification time, the schedule is automatically cancelled via CASCADE delete.

    Does not commit. Caller must commit transaction. Uses flush() to generate
    schedule ID immediately.

    Args:
        db: Database session
        game_id: ID of the game joined
        participant_id: ID of the participant who joined
        game_scheduled_at: When the game is scheduled (for TTL calculation)
        delay_seconds: Delay before notification (default: 60)

    Returns:
        Created NotificationSchedule instance
    """
    schedule = notification_schedule_model.NotificationSchedule(
        game_id=game_id,
        participant_id=participant_id,
        notification_type="join_notification",
        notification_time=utc_now() + timedelta(seconds=delay_seconds),
        sent=False,
        game_scheduled_at=game_scheduled_at,
        reminder_minutes=None,
    )

    db.add(schedule)
    await db.flush()

    return schedule


async def setup_game_schedules(
    db: AsyncSession,
    game: game_model.GameSession,
    reminder_minutes: list[int],
) -> None:
    """Set up announcement schedules after a game is announced.

    Creates join-notification entries for every Discord participant, confirmed
    or waitlisted, and populates the reminder schedule. Status-transition
    schedules (IN_PROGRESS/COMPLETED) are created unconditionally at game
    creation time and must not be created here.

    Does not commit.  The caller is responsible for committing the transaction.

    Args:
        db: Active async database session.
        game: The just-announced GameSession (participants relationship must be loaded).
        reminder_minutes: Minutes before game start at which to send reminders.
    """
    await schedule_join_notifications_for_game(db, game)
    await _populate_reminder_schedule(db, game, reminder_minutes)


async def schedule_join_notifications_for_game(
    db: AsyncSession,
    game: game_model.GameSession,
) -> None:
    """Schedule delayed join notifications for every Discord participant in a game.

    Schedules every participant in game.participants, confirmed or waitlisted alike
    (unlike schedule_join_notification, which schedules a single, already-known-new
    participant). Safe only when the entire game.participants list is known to
    contain no previously-scheduled rows, i.e. at bulk "activation" moments such as
    game announcement or recurrence-clone creation — not for incremental joins,
    which must call schedule_join_notification directly to avoid re-scheduling
    (and re-notifying) pre-existing participants.

    Does not commit. Caller must commit transaction.

    Args:
        db: Active async database session.
        game: The GameSession whose participants should be scheduled.
    """
    for participant in game.participants:
        if participant.user_id:
            await schedule_join_notification(
                db=db,
                game_id=game.id,
                participant_id=participant.id,
                game_scheduled_at=game.scheduled_at,
                delay_seconds=60,
            )


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


async def clone_game_for_recurrence(
    db: AsyncSession,
    source: game_model.GameSession,
    next_at: datetime,
) -> game_model.GameSession:
    """Create a recurrence clone of a completed game for the next scheduled occurrence.

    Sets post_at=None so the announcement loop ignores the clone until the host confirms.
    Carries over confirmed participants and creates status-transition schedules.
    Does not commit. The caller is responsible for committing the transaction.

    Args:
        db: Active async database session.
        source: The completed GameSession to clone.
        next_at: The datetime for the next occurrence (aware or naive; stored naive).
    """
    next_at_naive = next_at.replace(tzinfo=None)
    clone = game_model.GameSession(
        id=game_model.generate_uuid(),
        title=source.title,
        description=source.description,
        signup_instructions=source.signup_instructions,
        scheduled_at=next_at_naive,
        where=source.where,
        template_id=source.template_id,
        guild_id=source.guild_id,
        channel_id=source.channel_id,
        host_id=source.host_id,
        max_players=source.max_players,
        reminder_minutes=source.reminder_minutes,
        expected_duration_minutes=source.expected_duration_minutes,
        archive_delay_seconds=source.archive_delay_seconds,
        archive_channel_id=source.archive_channel_id,
        notify_role_ids=source.notify_role_ids,
        allowed_player_role_ids=source.allowed_player_role_ids,
        signup_method=source.signup_method,
        recur_rule=source.recur_rule,
        remind_host_rewards=source.remind_host_rewards,
        thumbnail_id=source.thumbnail_id,
        banner_image_id=source.banner_image_id,
        status=game_model.GameStatus.SCHEDULED.value,
        post_at=None,
        message_id=None,
        rewards=None,
    )
    db.add(clone)
    await increment_image_ref(db, source.thumbnail_id)
    await increment_image_ref(db, source.banner_image_id)
    await db.flush()

    partitioned = partition_participants(
        source.participants,
        source.max_players,
        signup_method=source.signup_method,
    )
    for position, source_participant in enumerate(partitioned.confirmed, start=1):
        db.add(
            participant_model.GameParticipant(
                game_session_id=clone.id,
                user_id=source_participant.user_id,
                display_name=source_participant.display_name,
                position_type=source_participant.position_type,
                position=position,
            )
        )
    await db.flush()
    _create_status_schedules(db, clone, source.expected_duration_minutes)
    return clone
