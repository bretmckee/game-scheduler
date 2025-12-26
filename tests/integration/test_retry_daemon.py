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


"""Integration tests for retry daemon DLQ processing.

Critical tests to prevent DLQ exponential growth bug by verifying:
1. Queue configuration has proper DLQ setup
2. Retry daemon republishes without TTL
3. Messages don't re-enter DLQ (preventing exponential growth)
4. Both bot_events.dlq and notification_queue.dlq are processed

These tests run against the actual retry-daemon container in docker-compose.
"""

import os
import time
from uuid import uuid4

import pika
import pytest

from shared.messaging.events import Event, EventType
from shared.messaging.infrastructure import (
    MAIN_EXCHANGE,
    QUEUE_BOT_EVENTS,
    QUEUE_BOT_EVENTS_DLQ,
    QUEUE_NOTIFICATION,
    QUEUE_NOTIFICATION_DLQ,
)

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def rabbitmq_url():
    """Get RabbitMQ URL from environment."""
    return os.getenv("RABBITMQ_URL", "amqp://guest:guest@rabbitmq:5672/")


@pytest.fixture
def rabbitmq_connection(rabbitmq_url):
    """Create RabbitMQ connection for test setup/assertions."""
    connection = pika.BlockingConnection(pika.URLParameters(rabbitmq_url))
    yield connection
    connection.close()


@pytest.fixture
def rabbitmq_channel(rabbitmq_connection):
    """Create RabbitMQ channel for test operations."""
    channel = rabbitmq_connection.channel()
    yield channel
    channel.close()


def purge_queue(channel, queue_name):
    """Purge all messages from a queue."""
    try:
        channel.queue_purge(queue_name)
    except Exception:
        pass


def publish_event_with_ttl(channel, routing_key, event, ttl_ms=1000):
    """
    Publish event with short TTL to trigger DLQ entry.

    This simulates the normal flow where messages with TTL expire
    and enter the DLQ when not consumed in time.
    """
    properties = pika.BasicProperties(
        delivery_mode=pika.DeliveryMode.Persistent,
        content_type="application/json",
        expiration=str(ttl_ms),
    )

    channel.basic_publish(
        exchange=MAIN_EXCHANGE,
        routing_key=routing_key,
        body=event.model_dump_json().encode(),
        properties=properties,
    )


def get_queue_message_count(channel, queue_name):
    """Get number of messages in queue."""
    result = channel.queue_declare(queue=queue_name, durable=True, passive=True)
    return result.method.message_count


def consume_one_message(channel, queue_name, timeout=5):
    """Consume one message from queue with timeout."""
    for method, properties, body in channel.consume(
        queue_name, auto_ack=False, inactivity_timeout=timeout
    ):
        if method is None:
            return None, None, None
        channel.basic_ack(method.delivery_tag)
        channel.cancel()
        return method, properties, body
    return None, None, None


def get_queue_arguments(channel, queue_name):
    """Get queue configuration arguments."""
    result = channel.queue_declare(queue=queue_name, durable=True, passive=True)
    # Arguments are available via management API or queue.declare response
    # For passive declare, we can't get arguments directly, but we can verify queue exists
    return result


def publish_to_dlq_with_metadata(
    channel, dlq_name, event, original_routing_key="game.reminder_due"
):
    """
    Publish message directly to DLQ with simulated dead-letter metadata.

    When RabbitMQ dead-letters a message, it adds x-death headers with metadata.
    We simulate this to test retry daemon behavior without waiting for TTL expiry.
    """
    x_death_header = [
        {
            "count": 1,
            "reason": "expired",
            "queue": QUEUE_BOT_EVENTS if "bot" in dlq_name else QUEUE_NOTIFICATION,
            "time": int(time.time()),
            "exchange": MAIN_EXCHANGE,
            "routing-keys": [original_routing_key],
        }
    ]

    properties = pika.BasicProperties(
        delivery_mode=pika.DeliveryMode.Persistent,
        content_type="application/json",
        headers={"x-death": x_death_header},
    )

    channel.basic_publish(
        exchange="",
        routing_key=dlq_name,
        body=event.model_dump_json().encode(),
        properties=properties,
    )


class TestRetryDaemonEndToEnd:
    """
    End-to-end integration tests with actual retry-daemon container.

    Tests the critical bug fix: preventing DLQ exponential growth by
    ensuring retry daemon republishes without TTL.
    """

    @pytest.fixture(autouse=True)
    def setup_queues(self, rabbitmq_channel):
        """Ensure queues are empty before each test."""
        purge_queue(rabbitmq_channel, QUEUE_BOT_EVENTS)
        purge_queue(rabbitmq_channel, QUEUE_BOT_EVENTS_DLQ)
        purge_queue(rabbitmq_channel, QUEUE_NOTIFICATION)
        purge_queue(rabbitmq_channel, QUEUE_NOTIFICATION_DLQ)

    def test_queue_configuration_has_dlq(self, rabbitmq_channel):
        """
        Verify that queues are configured with DLQs.

        This ensures the infrastructure is set up correctly for DLQ processing.
        We trust RabbitMQ's TTL implementation; we just verify our configuration.
        """
        # Verify primary queues exist
        bot_queue = rabbitmq_channel.queue_declare(
            queue=QUEUE_BOT_EVENTS, durable=True, passive=True
        )
        notif_queue = rabbitmq_channel.queue_declare(
            queue=QUEUE_NOTIFICATION, durable=True, passive=True
        )

        # Verify DLQs exist
        bot_dlq = rabbitmq_channel.queue_declare(
            queue=QUEUE_BOT_EVENTS_DLQ, durable=True, passive=True
        )
        notif_dlq = rabbitmq_channel.queue_declare(
            queue=QUEUE_NOTIFICATION_DLQ, durable=True, passive=True
        )

        assert bot_queue.method.queue == QUEUE_BOT_EVENTS
        assert notif_queue.method.queue == QUEUE_NOTIFICATION
        assert bot_dlq.method.queue == QUEUE_BOT_EVENTS_DLQ
        assert notif_dlq.method.queue == QUEUE_NOTIFICATION_DLQ

    def test_retry_daemon_republishes_from_dlq_without_ttl(self, rabbitmq_channel):
        """
        Critical test: Verify retry daemon republishes WITHOUT TTL.

        This is the key bug fix - if retry daemon republishes WITH TTL,
        messages re-enter DLQ causing exponential growth. Messages must
        be republished WITHOUT TTL to prevent this.
        """
        event = Event(
            event_type=EventType.NOTIFICATION_DUE,
            data={"game_id": str(uuid4()), "test": "no_ttl_republish"},
        )

        # Publish to DLQ with proper metadata
        publish_to_dlq_with_metadata(rabbitmq_channel, QUEUE_BOT_EVENTS_DLQ, event)

        # Wait for retry daemon to process (may have already processed it)
        retry_interval = int(os.getenv("RETRY_INTERVAL_SECONDS", "15"))
        time.sleep(retry_interval + 2)

        # Verify message republished to primary queue
        dlq_count = get_queue_message_count(rabbitmq_channel, QUEUE_BOT_EVENTS_DLQ)
        primary_count = get_queue_message_count(rabbitmq_channel, QUEUE_BOT_EVENTS)

        assert dlq_count == 0, "DLQ should be empty after retry daemon processes"
        assert primary_count == 1, "Primary queue should have republished message"

        # CRITICAL: Consume message and verify it has NO TTL
        method, properties, body = consume_one_message(rabbitmq_channel, QUEUE_BOT_EVENTS)

        assert method is not None, "Should consume republished message"
        assert properties.expiration is None, (
            "Republished message MUST NOT have TTL (prevents DLQ re-entry)"
        )

        # Verify event content preserved
        republished_event = Event.model_validate_json(body)
        assert republished_event.event_type == event.event_type
        assert republished_event.data == event.data

    def test_no_exponential_growth_after_multiple_cycles(self, rabbitmq_channel):
        """
        Critical test: Verify NO exponential DLQ growth.

        This directly tests the bug that started this refactoring:
        - Old behavior: Each daemon processed DLQ, republished WITH TTL
        - Result: Message re-enters DLQ, gets processed N times, creates N copies
        - Bug: Exponential growth (1 -> 2 -> 4 -> 8 -> 16...)

        New behavior: Single retry daemon, republishes WITHOUT TTL
        - Result: Message processed once, never re-enters DLQ
        """
        event = Event(
            event_type=EventType.NOTIFICATION_DUE,
            data={"game_id": str(uuid4()), "test": "no_exponential_growth"},
        )

        # Publish to DLQ with proper metadata
        publish_to_dlq_with_metadata(rabbitmq_channel, QUEUE_BOT_EVENTS_DLQ, event)

        # Wait for retry daemon to process
        retry_interval = int(os.getenv("RETRY_INTERVAL_SECONDS", "15"))
        time.sleep(retry_interval + 3)

        # Consume the republished message (simulating bot processing it)
        method, properties, body = consume_one_message(rabbitmq_channel, QUEUE_BOT_EVENTS)
        assert method is not None, "Should have republished message"

        # Wait for another retry cycle
        time.sleep(retry_interval + 3)

        # CRITICAL: DLQ should still be empty (no exponential growth)
        final_dlq_count = get_queue_message_count(rabbitmq_channel, QUEUE_BOT_EVENTS_DLQ)
        assert final_dlq_count == 0, "DLQ MUST remain empty - no exponential growth"

    def test_both_dlqs_processed_independently(self, rabbitmq_channel):
        """
        Test that retry daemon processes both bot_events.dlq and notification_queue.dlq.

        Verifies the per-queue DLQ pattern is working correctly.
        """
        bot_event = Event(
            event_type=EventType.NOTIFICATION_DUE,
            data={"game_id": str(uuid4()), "queue": "bot_events"},
        )
        notification_event = Event(
            event_type=EventType.NOTIFICATION_SEND_DM,
            data={"user_id": str(uuid4()), "queue": "notification_queue"},
        )

        # Publish to both DLQs with proper metadata
        publish_to_dlq_with_metadata(
            rabbitmq_channel, QUEUE_BOT_EVENTS_DLQ, bot_event, "game.reminder_due"
        )
        publish_to_dlq_with_metadata(
            rabbitmq_channel,
            QUEUE_NOTIFICATION_DLQ,
            notification_event,
            "notification.send_dm",
        )

        # Verify both messages in their respective DLQs
        bot_dlq_count = get_queue_message_count(rabbitmq_channel, QUEUE_BOT_EVENTS_DLQ)
        notif_dlq_count = get_queue_message_count(rabbitmq_channel, QUEUE_NOTIFICATION_DLQ)

        assert bot_dlq_count == 1, "bot_events.dlq should have 1 message"
        assert notif_dlq_count == 1, "notification_queue.dlq should have 1 message"

        # Wait for retry daemon to process both
        retry_interval = int(os.getenv("RETRY_INTERVAL_SECONDS", "15"))
        time.sleep(retry_interval + 2)

        # Verify both DLQs empty and messages republished
        bot_dlq_count = get_queue_message_count(rabbitmq_channel, QUEUE_BOT_EVENTS_DLQ)
        notif_dlq_count = get_queue_message_count(rabbitmq_channel, QUEUE_NOTIFICATION_DLQ)
        bot_primary_count = get_queue_message_count(rabbitmq_channel, QUEUE_BOT_EVENTS)
        notif_primary_count = get_queue_message_count(rabbitmq_channel, QUEUE_NOTIFICATION)

        assert bot_dlq_count == 0, "bot_events.dlq should be empty"
        assert notif_dlq_count == 0, "notification_queue.dlq should be empty"
        assert bot_primary_count == 1, "bot_events should have 1 republished message"
        assert notif_primary_count == 1, "notification_queue should have 1 republished message"

    def test_routing_key_preserved_from_x_death_header(self, rabbitmq_channel):
        """
        Test that original routing key is preserved when republishing.

        This ensures messages route correctly back to their consumers.
        """
        event = Event(
            event_type=EventType.GAME_STATUS_TRANSITION_DUE,
            data={"game_id": str(uuid4()), "test": "routing_key_check"},
        )
        original_routing_key = "game.status_transition"

        # Publish to DLQ with proper metadata
        publish_to_dlq_with_metadata(
            rabbitmq_channel, QUEUE_BOT_EVENTS_DLQ, event, original_routing_key
        )

        # Wait for retry daemon
        retry_interval = int(os.getenv("RETRY_INTERVAL_SECONDS", "15"))
        time.sleep(retry_interval + 3)

        # Consume and verify routing key
        method, properties, body = consume_one_message(rabbitmq_channel, QUEUE_BOT_EVENTS)

        assert method is not None, "Should have republished message"
        assert method.routing_key == original_routing_key, "Routing key must be preserved"
