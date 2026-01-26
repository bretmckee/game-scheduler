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


"""Notification service for sending game reminders."""

import logging
import uuid

from shared.messaging import events
from shared.messaging.sync_publisher import SyncEventPublisher

logger = logging.getLogger(__name__)


class NotificationService:
    """Service for managing game notifications."""

    def __init__(self) -> None:
        """Initialize notification service with event publisher."""
        self.event_publisher = SyncEventPublisher()

    def send_game_reminder_due(
        self,
        game_id: uuid.UUID,
        reminder_minutes: int,
    ) -> bool:
        """
        Publish game reminder due event for bot service to handle.

        Args:
            game_id: Game session UUID
            reminder_minutes: Minutes before game this reminder is for

        Returns:
            True if event published successfully
        """
        logger.info(
            "=== NotificationService.send_game_reminder_due called: game=%s, reminder=%smin ===",
            game_id,
            reminder_minutes,
        )

        try:
            logger.info("Connecting to RabbitMQ event publisher")
            self.event_publisher.connect()
            logger.info("Successfully connected to RabbitMQ")

            notification_event = events.NotificationDueEvent(
                game_id=game_id,
                notification_type="reminder",
            )

            logger.info("Created notification event: %s", notification_event.model_dump())

            event_wrapper = events.Event(
                event_type=events.EventType.NOTIFICATION_DUE,
                data=notification_event.model_dump(),
            )

            logger.info("Publishing event to RabbitMQ with routing key: game.notification_due")
            self.event_publisher.publish(event_wrapper)
            logger.info("Event published successfully to RabbitMQ")

            logger.info(
                "Successfully published game reminder for game %s (%s min before)",
                game_id,
                reminder_minutes,
            )

            return True

        except Exception as e:
            logger.exception(
                "Failed to publish game reminder for game %s: %s",
                game_id,
                e,
            )
            return False

        finally:
            logger.info("Closing RabbitMQ connection")
            self.event_publisher.close()
            logger.info("RabbitMQ connection closed")


def get_notification_service() -> NotificationService:
    """Get singleton notification service instance."""
    return NotificationService()
