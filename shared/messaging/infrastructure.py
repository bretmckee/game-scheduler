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
Shared RabbitMQ infrastructure configuration.

Centralizes queue and exchange definitions to ensure consistency
across init scripts, consumers, and publishers.
"""

from typing import Any, TypedDict


class QueueArguments(TypedDict, total=False):
    """Queue declaration arguments."""

    x_dead_letter_exchange: str
    x_message_ttl: int


# Exchange names
MAIN_EXCHANGE = "game_scheduler"
DLX_EXCHANGE = "game_scheduler.dlx"

# Queue names
QUEUE_BOT_EVENTS = "bot_events"
QUEUE_NOTIFICATION = "notification_queue"

# Dead letter queue names (per-queue DLQ pattern)
QUEUE_BOT_EVENTS_DLQ = "bot_events.dlq"
QUEUE_NOTIFICATION_DLQ = "notification_queue.dlq"

# Queue configuration
PRIMARY_QUEUE_TTL_MS = 3600000  # 1 hour in milliseconds

PRIMARY_QUEUE_ARGUMENTS: dict[str, Any] = {
    "x-dead-letter-exchange": DLX_EXCHANGE,
    "x-message-ttl": PRIMARY_QUEUE_TTL_MS,
}

# List of primary queues (with TTL and DLX)
PRIMARY_QUEUES = [
    QUEUE_BOT_EVENTS,
    QUEUE_NOTIFICATION,
]

# List of dead letter queues (no TTL, durable)
DEAD_LETTER_QUEUES = [
    QUEUE_BOT_EVENTS_DLQ,
    QUEUE_NOTIFICATION_DLQ,
]

# Routing key bindings (queue_name, routing_key)
QUEUE_BINDINGS = [
    # bot_events receives game, guild, and channel events
    (QUEUE_BOT_EVENTS, "game.*"),
    (QUEUE_BOT_EVENTS, "guild.*"),
    (QUEUE_BOT_EVENTS, "channel.*"),
    # notification_queue receives DM notifications
    (QUEUE_NOTIFICATION, "notification.send_dm"),
]

# DLQ bindings to dead letter exchange
# Each DLQ receives messages from its corresponding primary queue
# using the same routing keys
DLQ_BINDINGS = [
    # bot_events.dlq receives dead-lettered messages with game.*, guild.*, channel.* keys
    (QUEUE_BOT_EVENTS_DLQ, "game.*"),
    (QUEUE_BOT_EVENTS_DLQ, "guild.*"),
    (QUEUE_BOT_EVENTS_DLQ, "channel.*"),
    # notification_queue.dlq receives dead-lettered messages with notification.send_dm key
    (QUEUE_NOTIFICATION_DLQ, "notification.send_dm"),
]
