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


"""Bot event publisher wrapper for RabbitMQ messaging."""

import logging
from datetime import datetime
from typing import Any
from uuid import UUID

from shared.messaging.events import (
    Event,
    EventType,
    GameCreatedEvent,
)
from shared.messaging.publisher import EventPublisher

logger = logging.getLogger(__name__)


class BotEventPublisher:
    """Publish events from bot service to RabbitMQ."""

    def __init__(self, publisher: EventPublisher | None = None) -> None:
        """
        Initialize bot event publisher.

        Args:
            publisher: Optional EventPublisher instance, creates default if None
        """
        self.publisher = publisher or EventPublisher()
        self._connected = False

    async def connect(self) -> None:
        """Establish connection to RabbitMQ broker."""
        if not self._connected:
            await self.publisher.connect()
            self._connected = True
            logger.info("Bot event publisher connected to RabbitMQ")

    async def disconnect(self) -> None:
        """Close connection to RabbitMQ broker."""
        if self._connected:
            await self.publisher.close()
            self._connected = False
            logger.info("Bot event publisher disconnected from RabbitMQ")

    async def publish_game_created(
        self,
        game_id: str,
        title: str,
        guild_id: str,
        channel_id: str,
        host_id: str,
        scheduled_at: str,
        signup_method: str,
    ) -> None:
        """
        Publish game created event.

        Args:
            game_id: UUID of the game session
            title: Game title
            guild_id: Discord guild ID
            channel_id: Discord channel ID
            host_id: Discord ID of the host
            scheduled_at: ISO 8601 UTC timestamp string
            signup_method: Method used for player signups
        """
        scheduled_at_dt = datetime.fromisoformat(scheduled_at.replace("Z", "+00:00"))

        event_data = GameCreatedEvent(
            game_id=UUID(game_id),
            title=title,
            guild_id=guild_id,
            channel_id=channel_id,
            host_id=host_id,
            scheduled_at=scheduled_at_dt,
            signup_method=signup_method,
        )

        event = Event(event_type=EventType.GAME_CREATED, data=event_data.model_dump())

        await self.publisher.publish(event=event, routing_key="game.created")

        logger.info(
            "Published game_created event: game=%s, title=%s, guild=%s, channel=%s",
            game_id,
            title,
            guild_id,
            channel_id,
        )

    async def publish_game_updated(
        self, game_id: str, guild_id: str, updated_fields: dict[str, Any]
    ) -> None:
        """
        Publish game updated event.

        Args:
            game_id: UUID of the game session
            guild_id: Discord guild ID
            updated_fields: Dictionary of updated field names and values
        """
        event = Event(
            event_type=EventType.GAME_UPDATED,
            data={
                "game_id": game_id,
                "guild_id": guild_id,
                "updated_fields": updated_fields,
            },
        )

        routing_key = f"game.updated.{guild_id}"
        await self.publisher.publish(event=event, routing_key=routing_key)

        fields_list = list(updated_fields.keys())
        logger.info("Published game_updated event: game=%s, fields=%s", game_id, fields_list)


# Global publisher instance
_publisher_instance: BotEventPublisher | None = None


def get_bot_publisher() -> BotEventPublisher:
    """Get or create global bot event publisher instance."""
    global _publisher_instance  # noqa: PLW0603 - Singleton pattern for event publisher
    if _publisher_instance is None:
        _publisher_instance = BotEventPublisher()
    return _publisher_instance
