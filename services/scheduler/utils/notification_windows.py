"""Notification time window calculation utilities."""

import datetime


def should_send_notification(
    game_scheduled_at: datetime.datetime,
    reminder_minutes: int,
    current_time: datetime.datetime | None = None,
) -> tuple[bool, datetime.datetime]:
    """
    Check if notification should be sent for a game at specific reminder time.

    Args:
        game_scheduled_at: UTC datetime when game starts
        reminder_minutes: Minutes before game to send reminder
        current_time: Current UTC time (defaults to now)

    Returns:
        Tuple of (should_send, notification_time)
    """
    if current_time is None:
        current_time = datetime.datetime.now(datetime.UTC).replace(tzinfo=None)

    notification_time = game_scheduled_at - datetime.timedelta(minutes=reminder_minutes)

    time_diff = abs((current_time - notification_time).total_seconds())

    return time_diff <= 300, notification_time  # Within 5 minutes


def get_upcoming_games_window(
    lookback_minutes: int = 5, lookahead_minutes: int = 180
) -> tuple[datetime.datetime, datetime.datetime]:
    """
    Get time window for querying upcoming games needing notifications.

    Args:
        lookback_minutes: Minutes in past to check for missed notifications
        lookahead_minutes: Minutes in future to pre-schedule notifications

    Returns:
        Tuple of (start_time, end_time) in UTC
    """
    now = datetime.datetime.now(datetime.UTC).replace(tzinfo=None)

    start_time = now + datetime.timedelta(minutes=lookback_minutes)
    end_time = now + datetime.timedelta(minutes=lookahead_minutes)

    return start_time, end_time
