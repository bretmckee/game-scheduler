"""Notification service for sending game reminders."""

import logging
import uuid

from shared.messaging import events, publisher

logger = logging.getLogger(__name__)


class NotificationService:
    """Service for managing game notifications."""

    def __init__(self):
        """Initialize notification service with event publisher."""
        self.event_publisher = publisher.EventPublisher()

    async def send_game_reminder(
        self,
        game_id: uuid.UUID,
        user_id: uuid.UUID,
        game_title: str,
        game_time_unix: int,
        reminder_minutes: int,
    ) -> bool:
        """
        Send game reminder notification to user via Discord DM.

        Args:
            game_id: Game session UUID
            user_id: User UUID
            game_title: Title of the game
            game_time_unix: Unix timestamp of game start time
            reminder_minutes: Minutes before game this reminder is for

        Returns:
            True if notification published successfully
        """
        logger.info(
            f"=== NotificationService.send_game_reminder called: "
            f"game={game_id}, user={user_id}, reminder={reminder_minutes}min ==="
        )

        try:
            logger.info("Connecting to RabbitMQ event publisher")
            await self.event_publisher.connect()
            logger.info("Successfully connected to RabbitMQ")

            message = (
                f"Your game '{game_title}' starts <t:{game_time_unix}:R> "
                f"(in {reminder_minutes} minutes)"
            )

            notification_event = events.NotificationSendDMEvent(
                user_id=str(user_id),
                game_id=game_id,
                game_title=game_title,
                game_time_unix=game_time_unix,
                notification_type=f"{reminder_minutes}_minutes_before",
                message=message,
            )

            logger.info(f"Created notification event: {notification_event.model_dump()}")

            event_wrapper = events.Event(
                event_type=events.EventType.NOTIFICATION_SEND_DM,
                data=notification_event.model_dump(),
            )

            logger.info("Publishing event to RabbitMQ with routing key: notification.send_dm")
            await self.event_publisher.publish(event_wrapper)
            logger.info("Event published successfully to RabbitMQ")

            logger.info(
                f"Successfully published notification for user {user_id} game {game_id} "
                f"({reminder_minutes} min before)"
            )

            return True

        except Exception as e:
            logger.error(
                f"Failed to publish notification for user {user_id} game {game_id}: {e}",
                exc_info=True,
            )
            return False

        finally:
            logger.info("Closing RabbitMQ connection")
            await self.event_publisher.close()
            logger.info("RabbitMQ connection closed")


async def get_notification_service() -> NotificationService:
    """Get singleton notification service instance."""
    return NotificationService()
