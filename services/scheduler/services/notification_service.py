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
