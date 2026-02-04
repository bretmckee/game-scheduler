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
RabbitMQ messaging infrastructure for event-driven communication.

Provides async RabbitMQ connection management, event publishing,
and consumption framework for microservices communication.
"""

from shared.messaging.config import get_rabbitmq_connection
from shared.messaging.consumer import EventConsumer
from shared.messaging.events import Event, EventType, GameStartedEvent
from shared.messaging.publisher import EventPublisher
from shared.messaging.sync_publisher import SyncEventPublisher

__all__ = [
    "Event",
    "EventConsumer",
    "EventPublisher",
    "EventType",
    "GameStartedEvent",
    "SyncEventPublisher",
    "get_rabbitmq_connection",
]
