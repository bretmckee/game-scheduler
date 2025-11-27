"""Notification service for sending game reminders."""

import logging
import uuid

from shared.messaging import events
from shared.messaging.sync_publisher import SyncEventPublisher

logger = logging.getLogger(__name__)


class NotificationService:
    """Service for managing game notifications."""

    def __init__(self):
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
            f"=== NotificationService.send_game_reminder_due called: "
            f"game={game_id}, reminder={reminder_minutes}min ==="
        )

        try:
            logger.info("Connecting to RabbitMQ event publisher")
            self.event_publisher.connect()
            logger.info("Successfully connected to RabbitMQ")

            reminder_event = events.GameReminderDueEvent(
                game_id=game_id,
                reminder_minutes=reminder_minutes,
            )

            logger.info(f"Created game reminder event: {reminder_event.model_dump()}")

            event_wrapper = events.Event(
                event_type=events.EventType.GAME_REMINDER_DUE,
                data=reminder_event.model_dump(),
            )

            logger.info("Publishing event to RabbitMQ with routing key: game.reminder_due")
            self.event_publisher.publish(event_wrapper)
            logger.info("Event published successfully to RabbitMQ")

            logger.info(
                f"Successfully published game reminder for game {game_id} "
                f"({reminder_minutes} min before)"
            )

            return True

        except Exception as e:
            logger.error(
                f"Failed to publish game reminder for game {game_id}: {e}",
                exc_info=True,
            )
            return False

        finally:
            logger.info("Closing RabbitMQ connection")
            self.event_publisher.close()
            logger.info("RabbitMQ connection closed")


def get_notification_service() -> NotificationService:
    """Get singleton notification service instance."""
    return NotificationService()
