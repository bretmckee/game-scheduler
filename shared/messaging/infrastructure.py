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
Shared RabbitMQ infrastructure configuration.

Centralizes queue and exchange definitions to ensure consistency
across init scripts, consumers, and publishers.
"""

from typing import TypedDict


class QueueArguments(TypedDict, total=False):
    """Queue declaration arguments."""

    x_dead_letter_exchange: str
    x_message_ttl: int


# Exchange names
MAIN_EXCHANGE = "game_scheduler"
DLX_EXCHANGE = "game_scheduler.dlx"

# Queue names
QUEUE_BOT_EVENTS = "bot_events"
QUEUE_API_EVENTS = "api_events"
QUEUE_SCHEDULER_EVENTS = "scheduler_events"
QUEUE_NOTIFICATION = "notification_queue"
QUEUE_DLQ = "DLQ"

# Queue configuration
PRIMARY_QUEUE_TTL_MS = 3600000  # 1 hour in milliseconds

PRIMARY_QUEUE_ARGUMENTS: dict[str, str | int] = {
    "x-dead-letter-exchange": DLX_EXCHANGE,
    "x-message-ttl": PRIMARY_QUEUE_TTL_MS,
}

# List of primary queues (with TTL and DLX)
PRIMARY_QUEUES = [
    QUEUE_BOT_EVENTS,
    QUEUE_API_EVENTS,
    QUEUE_SCHEDULER_EVENTS,
    QUEUE_NOTIFICATION,
]

# Routing key bindings (queue_name, routing_key)
QUEUE_BINDINGS = [
    # bot_events receives game, guild, and channel events
    (QUEUE_BOT_EVENTS, "game.*"),
    (QUEUE_BOT_EVENTS, "guild.*"),
    (QUEUE_BOT_EVENTS, "channel.*"),
    # api_events receives game events for API updates
    (QUEUE_API_EVENTS, "game.*"),
    # scheduler_events receives specific game lifecycle events
    (QUEUE_SCHEDULER_EVENTS, "game.created"),
    (QUEUE_SCHEDULER_EVENTS, "game.updated"),
    (QUEUE_SCHEDULER_EVENTS, "game.cancelled"),
    # notification_queue receives DM notifications
    (QUEUE_NOTIFICATION, "notification.send_dm"),
]
