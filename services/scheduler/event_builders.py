# Copyright 2025-2026 Bret McKee
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


"""
Event builder functions for generic scheduler daemon.

Each builder function constructs an Event object from a schedule
model instance for publishing to RabbitMQ.
"""

import logging
from uuid import UUID

from shared.messaging.events import Event, EventType, NotificationDueEvent
from shared.models import GameStatusSchedule, NotificationSchedule
from shared.models.base import utc_now
from shared.schemas.events import GameStatusTransitionDueEvent
from shared.utils.time_constants import MILLISECONDS_PER_SECOND, SECONDS_PER_MINUTE

logger = logging.getLogger(__name__)


def build_notification_event(
    notification: NotificationSchedule,
) -> tuple[Event, int | None]:
    """
    Build NOTIFICATION_DUE event from notification schedule with per-message TTL.

    Args:
        notification: NotificationSchedule record

    Returns:
        Tuple of (Event, expiration_ms) where expiration_ms is milliseconds
        until game starts. If game has no scheduled_at or already started,
        returns minimal TTL.
    """
    event_data = NotificationDueEvent(
        game_id=UUID(notification.game_id),
        notification_type=notification.notification_type,
        participant_id=notification.participant_id,
    )

    event = Event(
        event_type=EventType.NOTIFICATION_DUE,
        data=event_data.model_dump(),
    )

    expiration_ms = None
    if notification.game_scheduled_at:
        time_until_game = (notification.game_scheduled_at - utc_now()).total_seconds()

        if time_until_game > SECONDS_PER_MINUTE:
            expiration_ms = int(time_until_game * MILLISECONDS_PER_SECOND)
            logger.debug(
                "Notification TTL: %.0fs until game starts (game_id=%s)",
                time_until_game,
                notification.game_id,
            )
        else:
            expiration_ms = SECONDS_PER_MINUTE * MILLISECONDS_PER_SECOND
            logger.warning(
                "Game already started or starting soon, setting minimal TTL (game_id=%s)",
                notification.game_id,
            )

    return event, expiration_ms


def build_status_transition_event(transition: GameStatusSchedule) -> tuple[Event, None]:
    """
    Build GAME_STATUS_TRANSITION_DUE event from status schedule.

    Status transitions never expire - they must eventually succeed to
    maintain database consistency.

    Args:
        transition: GameStatusSchedule record

    Returns:
        Tuple of (Event, None) - status transitions have no TTL
    """
    event_data = GameStatusTransitionDueEvent(
        game_id=UUID(transition.game_id),
        target_status=transition.target_status,
        transition_time=transition.transition_time,
    )

    event = Event(
        event_type=EventType.GAME_STATUS_TRANSITION_DUE,
        data=event_data.model_dump(),
    )

    return event, None
