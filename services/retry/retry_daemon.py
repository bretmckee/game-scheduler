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
Dedicated retry daemon for DLQ processing.

Periodically checks configured DLQs and republishes messages
to their primary queues with configurable intervals.
"""

import logging
import time
from collections.abc import Callable

from opentelemetry import trace

from shared.messaging.events import Event
from shared.messaging.infrastructure import (
    QUEUE_BOT_EVENTS_DLQ,
    QUEUE_NOTIFICATION_DLQ,
)
from shared.messaging.sync_publisher import SyncEventPublisher

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)


class RetryDaemon:
    """Processes DLQs and republishes messages with configurable retry intervals."""

    def __init__(self, rabbitmq_url: str, retry_interval_seconds: int = 900):
        """
        Initialize retry daemon.

        Args:
            rabbitmq_url: RabbitMQ connection string
            retry_interval_seconds: How often to check DLQs (default 15 min)
        """
        self.rabbitmq_url = rabbitmq_url
        self.retry_interval = retry_interval_seconds
        self.publisher: SyncEventPublisher | None = None

        # Map DLQ names to process
        self.dlq_names = [
            QUEUE_BOT_EVENTS_DLQ,
            QUEUE_NOTIFICATION_DLQ,
        ]

    def connect(self) -> None:
        """Establish connection to RabbitMQ."""
        self.publisher = SyncEventPublisher()
        self.publisher.connect()
        logger.info("Retry daemon connected to RabbitMQ")

    def run(self, shutdown_requested: Callable[[], bool]) -> None:
        """
        Main daemon loop.

        Args:
            shutdown_requested: Callable returning True when shutdown is requested
        """
        logger.info("Starting retry daemon")

        self.connect()

        while not shutdown_requested():
            try:
                for dlq_name in self.dlq_names:
                    self._process_dlq(dlq_name)

                time.sleep(self.retry_interval)

            except KeyboardInterrupt:
                logger.info("Keyboard interrupt received")
                break
            except Exception:
                logger.exception("Unexpected error in retry daemon loop")
                time.sleep(5)

        logger.info("Retry daemon shutting down")
        self._cleanup()

    def _process_dlq(self, dlq_name: str) -> None:
        """
        Process messages from one DLQ.

        Args:
            dlq_name: Name of the dead letter queue to process
        """
        with tracer.start_as_current_span(
            "retry.process_dlq",
            attributes={
                "retry.dlq_name": dlq_name,
                "retry.check_interval": self.retry_interval,
            },
        ):
            try:
                import pika

                connection = pika.BlockingConnection(pika.URLParameters(self.rabbitmq_url))
                channel = connection.channel()

                queue_state = channel.queue_declare(queue=dlq_name, durable=True)
                message_count = queue_state.method.message_count

                if message_count == 0:
                    logger.debug(f"DLQ {dlq_name} is empty, nothing to process")
                    connection.close()
                    return

                logger.info(f"Processing {message_count} messages from {dlq_name}")

                processed = 0

                for method, properties, body in channel.consume(dlq_name, auto_ack=False):
                    try:
                        routing_key = self._get_routing_key(properties)

                        event = Event.model_validate_json(body)

                        if self.publisher is None:
                            raise RuntimeError("Publisher not initialized")

                        # Republish without TTL to prevent re-entering DLQ
                        self.publisher.publish(event, routing_key=routing_key, expiration_ms=None)

                        channel.basic_ack(method.delivery_tag)
                        processed += 1

                        if processed >= message_count:
                            break

                    except Exception as e:
                        logger.error(
                            f"Failed to republish message from {dlq_name}: {e}",
                            exc_info=True,
                        )
                        # NACK with requeue - message stays in DLQ for next cycle
                        channel.basic_nack(method.delivery_tag, requeue=True)

                channel.cancel()
                connection.close()

                logger.info(f"Republished {processed} messages from {dlq_name}")

            except Exception as e:
                logger.error(f"Error during DLQ processing for {dlq_name}: {e}", exc_info=True)

    def _get_routing_key(self, properties) -> str:
        """
        Extract original routing key from message headers.

        Args:
            properties: Message properties from RabbitMQ

        Returns:
            Original routing key from x-death header or message properties
        """
        if properties.headers and "x-death" in properties.headers:
            deaths = properties.headers["x-death"]
            if deaths and len(deaths) > 0:
                routing_keys = deaths[0].get("routing-keys", [])
                if routing_keys and len(routing_keys) > 0:
                    return routing_keys[0]

        return properties.routing_key or "unknown"

    def _cleanup(self) -> None:
        """Clean up connections."""
        if self.publisher:
            try:
                self.publisher.close()
            except Exception as e:
                logger.error(f"Error closing publisher: {e}")

        logger.info("Retry daemon cleanup complete")
