"""Periodic task to check for upcoming games and schedule notifications."""

import asyncio
import datetime
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from services.scheduler.celery_app import app
from services.scheduler.utils import notification_windows
from shared import database
from shared.models import channel, game

logger = logging.getLogger(__name__)


@app.task(name="services.scheduler.tasks.check_notifications.check_upcoming_notifications")
def check_upcoming_notifications():
    """Check for games needing notifications and schedule delivery."""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(_check_upcoming_notifications_async())


async def _check_upcoming_notifications_async():
    """Check upcoming games and schedule notifications."""
    logger.info("=== Starting notification check cycle ===")
    logger.info("Checking for upcoming game notifications")

    start_time, end_time = notification_windows.get_upcoming_games_window()
    logger.info(f"Notification window: {start_time} to {end_time}")

    async with database.get_db_session() as db:
        upcoming_games = await _get_upcoming_games(db, start_time, end_time)
        logger.info(f"Found {len(upcoming_games)} games in notification window")

        notification_count = 0
        for game_session in upcoming_games:
            try:
                logger.info(
                    f"Processing game {game_session.id} - {game_session.title} "
                    f"scheduled at {game_session.scheduled_at}"
                )
                notifications_sent = await _schedule_game_notifications(db, game_session)
                notification_count += notifications_sent
                logger.info(
                    f"Scheduled {notifications_sent} notifications for game {game_session.id}"
                )
                await db.commit()
            except Exception as e:
                logger.error(
                    f"Failed to schedule notifications for game {game_session.id}: {e}",
                    exc_info=True,
                )
                await db.rollback()

        logger.info(
            f"=== Notification check complete: {notification_count} notifications "
            f"scheduled for {len(upcoming_games)} games ==="
        )

    return {
        "games_checked": len(upcoming_games),
        "notifications_scheduled": notification_count,
    }


async def _get_upcoming_games(
    db: AsyncSession, start_time: datetime.datetime, end_time: datetime.datetime
) -> list[game.GameSession]:
    """Query games scheduled in the notification window."""
    stmt = (
        select(game.GameSession)
        .where(game.GameSession.scheduled_at >= start_time)
        .where(game.GameSession.scheduled_at <= end_time)
        .where(game.GameSession.status == "SCHEDULED")
        .options(
            selectinload(game.GameSession.participants),
            selectinload(game.GameSession.channel).selectinload(channel.ChannelConfiguration.guild),
        )
    )

    result = await db.execute(stmt)
    return list(result.scalars().all())


async def _schedule_game_notifications(db: AsyncSession, game_session: game.GameSession) -> int:
    """Schedule notifications for a game using inherited reminder settings."""
    from services.scheduler.celery_app import app as celery_app

    reminder_minutes = _resolve_reminder_minutes(game_session)
    now = datetime.datetime.now(datetime.UTC).replace(tzinfo=None)

    logger.info(
        f"Game {game_session.id}: reminder_minutes={reminder_minutes}, "
        f"participants={len(game_session.participants)}"
    )

    notification_count = 0

    for reminder_min in reminder_minutes:
        should_send, notification_time = notification_windows.should_send_notification(
            game_session.scheduled_at, reminder_min, now
        )

        logger.debug(
            f"Game {game_session.id}, reminder {reminder_min}min: "
            f"should_send={should_send}, notification_time={notification_time}"
        )

        if should_send:
            # All participants with user_id are active (no status field needed)
            participants = [p for p in game_session.participants if p.user_id is not None]
            logger.info(
                f"Scheduling {reminder_min}min reminder for {len(participants)} participants"
            )

            for participant_record in participants:
                notification_key = f"{game_session.id}_{participant_record.user_id}_{reminder_min}"

                already_sent = await _notification_already_sent(db, notification_key)
                logger.debug(f"Notification key {notification_key}: already_sent={already_sent}")

                if not already_sent:
                    logger.info(
                        f"Scheduling notification: game={game_session.id}, "
                        f"user={participant_record.user_id}, reminder={reminder_min}min, "
                        f"eta={notification_time}"
                    )
                    # Use send_task with the full task name
                    celery_app.send_task(
                        "services.scheduler.tasks.send_notification.send_game_notification",
                        args=[
                            str(game_session.id),
                            str(participant_record.user_id),
                            reminder_min,
                        ],
                        eta=notification_time,
                    )
                    await _mark_notification_sent(db, notification_key)
                    notification_count += 1
                else:
                    logger.debug(f"Skipping already sent notification: {notification_key}")

    return notification_count


def _resolve_reminder_minutes(game_session: game.GameSession) -> list[int]:
    """Resolve reminder minutes using game → channel → guild inheritance."""
    if game_session.reminder_minutes:
        return game_session.reminder_minutes

    if game_session.channel and game_session.channel.reminder_minutes:
        return game_session.channel.reminder_minutes

    if (
        game_session.channel
        and game_session.channel.guild
        and game_session.channel.guild.default_reminder_minutes
    ):
        return game_session.channel.guild.default_reminder_minutes

    return [60, 15]


async def _notification_already_sent(db: AsyncSession, notification_key: str) -> bool:
    """Check if notification has already been sent."""
    from shared.cache import client as cache_client

    redis = await cache_client.get_redis_client()
    cache_key = f"notification_sent:{notification_key}"

    result = await redis.get(cache_key)
    return result is not None


async def _mark_notification_sent(db: AsyncSession, notification_key: str) -> None:
    """Mark notification as sent to prevent duplicates."""
    from shared.cache import client as cache_client

    redis = await cache_client.get_redis_client()
    cache_key = f"notification_sent:{notification_key}"

    await redis.set(cache_key, "1", ttl=86400 * 7)  # 7 days
