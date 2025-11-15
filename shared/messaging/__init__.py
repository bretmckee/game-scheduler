"""
RabbitMQ messaging infrastructure for event-driven communication.

Provides async RabbitMQ connection management, event publishing,
and consumption framework for microservices communication.
"""

from shared.messaging.config import get_rabbitmq_connection
from shared.messaging.consumer import EventConsumer
from shared.messaging.events import Event, EventType
from shared.messaging.publisher import EventPublisher

__all__ = [
    "get_rabbitmq_connection",
    "Event",
    "EventType",
    "EventPublisher",
    "EventConsumer",
]
