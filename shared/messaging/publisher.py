"""
Event publisher for RabbitMQ messaging.

Provides async event publishing with automatic exchange creation
and message persistence.
"""

import logging
from typing import Any

from aio_pika import DeliveryMode, ExchangeType, Message
from aio_pika.abc import AbstractChannel, AbstractRobustConnection

from shared.messaging.config import get_rabbitmq_connection
from shared.messaging.events import Event

logger = logging.getLogger(__name__)


class EventPublisher:
    """
    Publishes events to RabbitMQ exchange.

    Events are published to a topic exchange with routing key
    based on event type, allowing flexible message routing.
    """

    def __init__(
        self,
        exchange_name: str = "game_scheduler",
        connection: AbstractRobustConnection | None = None,
    ):
        self.exchange_name = exchange_name
        self._connection = connection
        self._channel: AbstractChannel | None = None

    async def connect(self) -> None:
        """Establish connection and declare exchange."""
        # Close existing connection if present
        if self._connection and not self._connection.is_closed:
            try:
                await self._connection.close()
            except Exception:
                logger.warning("Error closing existing connection during reconnect", exc_info=True)

        self._connection = None
        self._channel = None

        if self._connection is None:
            self._connection = await get_rabbitmq_connection()

        self._channel = await self._connection.channel()

        self._exchange = await self._channel.declare_exchange(
            self.exchange_name,
            ExchangeType.TOPIC,
            durable=True,
        )

        logger.info(f"Publisher connected to exchange: {self.exchange_name}")

    async def publish(
        self,
        event: Event,
        routing_key: str | None = None,
    ) -> None:
        """
        Publish event to exchange.

        Args:
            event: Event to publish.
            routing_key: Optional routing key override. Uses event_type if not
                provided.

        Raises:
            RuntimeError: If not connected.
        """
        if self._channel is None or self._channel.is_closed:
            logger.warning("Channel not open, reconnecting...")
            await self.connect()

        if routing_key is None:
            routing_key = event.event_type.value

        message_body = event.model_dump_json().encode()

        message = Message(
            body=message_body,
            delivery_mode=DeliveryMode.PERSISTENT,
            content_type="application/json",
        )

        await self._exchange.publish(
            message,
            routing_key=routing_key,
        )

        logger.debug(f"Published event: {event.event_type} with routing key: {routing_key}")

    async def publish_dict(
        self,
        event_type: str,
        data: dict[str, Any],
        trace_id: str | None = None,
    ) -> None:
        """
        Publish event from dictionary data.

        Convenience method for publishing without creating Event object.

        Args:
            event_type: Event type string.
            data: Event payload.
            trace_id: Optional correlation ID.
        """
        from shared.messaging.events import EventType

        event = Event(
            event_type=EventType(event_type),
            data=data,
            trace_id=trace_id,
        )

        await self.publish(event)

    async def close(self) -> None:
        """Close channel gracefully."""
        if self._channel and not self._channel.is_closed:
            await self._channel.close()
            self._channel = None
            logger.info("Publisher channel closed")
