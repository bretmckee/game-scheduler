# Copyright 2025 Bret McKee (bret.mckee@gmail.com)
#
# This file is part of Game_Scheduler. (https://github.com/game-scheduler)
#
# Game_Scheduler is free software: you can redistribute it and/or
# modify it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or (at your
# option) any later version.
#
# Game_Scheduler is distributed in the hope that it will be
# useful, but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Affero General
# Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License along
# with Game_Scheduler If not, see <https://www.gnu.org/licenses/>.


"""
Event builder functions for generic scheduler daemon.

Each builder function constructs an Event object from a schedule
model instance for publishing to RabbitMQ.
"""

from uuid import UUID

from shared.messaging.events import Event, EventType, GameReminderDueEvent
from shared.models import GameStatusSchedule, NotificationSchedule
from shared.schemas.events import GameStatusTransitionDueEvent


def build_game_reminder_event(notification: NotificationSchedule) -> Event:
    """
    Build GAME_REMINDER_DUE event from notification schedule.

    Args:
        notification: NotificationSchedule record

    Returns:
        Event with GAME_REMINDER_DUE type and payload
    """
    event_data = GameReminderDueEvent(
        game_id=UUID(notification.game_id),
        reminder_minutes=notification.reminder_minutes,
    )

    return Event(
        event_type=EventType.GAME_REMINDER_DUE,
        data=event_data.model_dump(),
    )


def build_status_transition_event(transition: GameStatusSchedule) -> Event:
    """
    Build GAME_STATUS_TRANSITION_DUE event from status schedule.

    Args:
        transition: GameStatusSchedule record

    Returns:
        Event with GAME_STATUS_TRANSITION_DUE type and payload
    """
    event_data = GameStatusTransitionDueEvent(
        game_id=UUID(transition.game_id),
        target_status=transition.target_status,
        transition_time=transition.transition_time,
    )

    return Event(
        event_type=EventType.GAME_STATUS_TRANSITION_DUE,
        data=event_data.model_dump(),
    )
