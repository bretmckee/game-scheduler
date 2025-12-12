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


"""Unit tests for RetryDaemon class."""

from collections import namedtuple
from unittest.mock import Mock, patch

import pytest

from services.retry.retry_daemon import RetryDaemon
from shared.messaging.events import Event, EventType
from shared.messaging.infrastructure import QUEUE_BOT_EVENTS_DLQ, QUEUE_NOTIFICATION_DLQ


class TestRetryDaemon:
    """Test suite for RetryDaemon class."""

    @pytest.fixture
    def daemon(self):
        """Create RetryDaemon instance for testing."""
        return RetryDaemon(
            rabbitmq_url="amqp://guest:guest@localhost:5672/",
            retry_interval_seconds=60,
        )

    def test_init(self, daemon):
        """Test RetryDaemon initialization."""
        assert daemon.rabbitmq_url == "amqp://guest:guest@localhost:5672/"
        assert daemon.retry_interval == 60
        assert daemon.publisher is None
        assert daemon.dlq_names == [QUEUE_BOT_EVENTS_DLQ, QUEUE_NOTIFICATION_DLQ]

    @patch("services.retry.retry_daemon.SyncEventPublisher")
    def test_connect(self, mock_publisher_class, daemon):
        """Test connection establishment."""
        mock_publisher = Mock()
        mock_publisher_class.return_value = mock_publisher

        daemon.connect()

        mock_publisher_class.assert_called_once()
        mock_publisher.connect.assert_called_once()
        assert daemon.publisher == mock_publisher

    def test_get_routing_key_from_x_death(self, daemon):
        """Test routing key extraction from x-death header."""
        properties = Mock()
        properties.headers = {
            "x-death": [
                {
                    "queue": "bot_events",
                    "reason": "expired",
                    "routing-keys": ["game.created"],
                }
            ]
        }
        properties.routing_key = "fallback.key"

        result = daemon._get_routing_key(properties)

        assert result == "game.created"

    def test_get_routing_key_from_properties(self, daemon):
        """Test routing key extraction from message properties when x-death missing."""
        properties = Mock()
        properties.headers = None
        properties.routing_key = "notification.send_dm"

        result = daemon._get_routing_key(properties)

        assert result == "notification.send_dm"

    def test_get_routing_key_unknown_fallback(self, daemon):
        """Test routing key fallback to 'unknown' when both sources missing."""
        properties = Mock()
        properties.headers = None
        properties.routing_key = None

        result = daemon._get_routing_key(properties)

        assert result == "unknown"

    def test_get_routing_key_with_empty_x_death(self, daemon):
        """Test routing key extraction when x-death exists but is empty."""
        properties = Mock()
        properties.headers = {"x-death": []}
        properties.routing_key = "fallback.key"

        result = daemon._get_routing_key(properties)

        assert result == "fallback.key"

    def test_get_routing_key_with_empty_routing_keys(self, daemon):
        """Test routing key extraction when x-death has no routing-keys."""
        properties = Mock()
        properties.headers = {
            "x-death": [
                {
                    "queue": "bot_events",
                    "reason": "expired",
                    "routing-keys": [],
                }
            ]
        }
        properties.routing_key = "fallback.key"

        result = daemon._get_routing_key(properties)

        assert result == "fallback.key"

    def test_process_dlq_empty_queue(self, daemon, caplog):
        """Test processing of empty DLQ."""
        with caplog.at_level("DEBUG"):
            with patch("pika.BlockingConnection") as mock_connection_class:
                # Mock connection and channel
                mock_connection = Mock()
                mock_channel = Mock()
                mock_connection_class.return_value = mock_connection
                mock_connection.channel.return_value = mock_channel

                # Mock queue state showing empty queue
                Method = namedtuple("Method", ["message_count"])
                mock_queue_state = Mock()
                mock_queue_state.method = Method(message_count=0)
                mock_channel.queue_declare.return_value = mock_queue_state

                daemon._process_dlq(QUEUE_BOT_EVENTS_DLQ)

                mock_channel.queue_declare.assert_called_once_with(
                    queue=QUEUE_BOT_EVENTS_DLQ, durable=True
                )
                mock_connection.close.assert_called_once()
                assert "is empty, nothing to process" in caplog.text

    def test_process_dlq_with_messages(self, daemon):
        """Test processing DLQ with messages."""
        with patch("pika.BlockingConnection") as mock_connection_class:
            # Create mock publisher
            mock_publisher = Mock()
            daemon.publisher = mock_publisher

            # Mock connection and channel
            mock_connection = Mock()
            mock_channel = Mock()
            mock_connection_class.return_value = mock_connection
            mock_connection.channel.return_value = mock_channel

            # Mock queue state showing 2 messages
            Method = namedtuple("Method", ["message_count", "delivery_tag"])
            mock_queue_state = Mock()
            mock_queue_state.method = Method(message_count=2, delivery_tag=None)
            mock_channel.queue_declare.return_value = mock_queue_state

            # Mock message properties
            mock_properties1 = Mock()
            mock_properties1.headers = {"x-death": [{"routing-keys": ["game.created"]}]}
            mock_properties1.routing_key = "game.created"

            mock_properties2 = Mock()
            mock_properties2.headers = {"x-death": [{"routing-keys": ["game.updated"]}]}
            mock_properties2.routing_key = "game.updated"

            # Create valid Event messages
            event1 = Event(
                event_type=EventType.GAME_CREATED,
                data={"game_id": "123"},
            )
            event2 = Event(
                event_type=EventType.GAME_UPDATED,
                data={"game_id": "456"},
            )

            # Mock consume to return 2 messages
            mock_method1 = Method(message_count=2, delivery_tag=1)
            mock_method2 = Method(message_count=2, delivery_tag=2)
            mock_channel.consume.return_value = [
                (mock_method1, mock_properties1, event1.model_dump_json()),
                (mock_method2, mock_properties2, event2.model_dump_json()),
            ]

            daemon._process_dlq(QUEUE_BOT_EVENTS_DLQ)

            assert mock_publisher.publish.call_count == 2
            mock_channel.basic_ack.assert_any_call(1)
            mock_channel.basic_ack.assert_any_call(2)
            mock_channel.cancel.assert_called_once()
            mock_connection.close.assert_called_once()

    def test_process_dlq_with_publish_error(self, daemon):
        """Test error handling when republish fails."""
        with patch("pika.BlockingConnection") as mock_connection_class:
            # Create mock publisher that raises error
            mock_publisher = Mock()
            mock_publisher.publish.side_effect = Exception("Publish failed")
            daemon.publisher = mock_publisher

            # Mock connection and channel
            mock_connection = Mock()
            mock_channel = Mock()
            mock_connection_class.return_value = mock_connection
            mock_connection.channel.return_value = mock_channel

            # Mock queue state showing 1 message
            Method = namedtuple("Method", ["message_count", "delivery_tag"])
            mock_queue_state = Mock()
            mock_queue_state.method = Method(message_count=1, delivery_tag=None)
            mock_channel.queue_declare.return_value = mock_queue_state

            # Mock message properties
            mock_properties = Mock()
            mock_properties.headers = {"x-death": [{"routing-keys": ["game.created"]}]}
            mock_properties.routing_key = "game.created"

            # Create valid Event message
            event = Event(
                event_type=EventType.GAME_CREATED,
                data={"game_id": "123"},
            )

            # Mock consume to return 1 message
            mock_method = Method(message_count=1, delivery_tag=1)
            mock_channel.consume.return_value = [
                (mock_method, mock_properties, event.model_dump_json()),
            ]

            daemon._process_dlq(QUEUE_BOT_EVENTS_DLQ)

            # Should NACK with requeue when publish fails
            mock_channel.basic_nack.assert_called_once_with(1, requeue=True)
            mock_connection.close.assert_called_once()

    def test_process_dlq_connection_error(self, daemon, caplog):
        """Test error handling when connection fails."""
        with patch("pika.BlockingConnection") as mock_connection_class:
            mock_connection_class.side_effect = Exception("Connection failed")

            daemon._process_dlq(QUEUE_BOT_EVENTS_DLQ)

            assert "Error during DLQ processing" in caplog.text

    def test_cleanup(self, daemon):
        """Test cleanup closes publisher connection."""
        mock_publisher = Mock()
        daemon.publisher = mock_publisher

        daemon._cleanup()

        mock_publisher.close.assert_called_once()

    def test_cleanup_with_error(self, daemon, caplog):
        """Test cleanup handles publisher close errors."""
        mock_publisher = Mock()
        mock_publisher.close.side_effect = Exception("Close failed")
        daemon.publisher = mock_publisher

        daemon._cleanup()

        assert "Error closing publisher" in caplog.text

    def test_cleanup_without_publisher(self, daemon):
        """Test cleanup when publisher is None."""
        daemon.publisher = None

        daemon._cleanup()

    @patch("services.retry.retry_daemon.time")
    @patch("services.retry.retry_daemon.SyncEventPublisher")
    def test_run_loop(self, mock_publisher_class, mock_time, daemon):
        """Test main daemon run loop."""
        mock_publisher = Mock()
        mock_publisher_class.return_value = mock_publisher

        # Shutdown after processing both DLQs once
        iteration_count = [0]

        def shutdown_after_first_iteration():
            # Called at start of while loop, before processing
            if iteration_count[0] > 0:
                return True
            return False

        def sleep_side_effect(duration):
            # Increment counter after sleep (end of iteration)
            iteration_count[0] += 1

        mock_time.sleep.side_effect = sleep_side_effect

        with patch.object(daemon, "_process_dlq") as mock_process:
            daemon.run(shutdown_after_first_iteration)

            # Should process both DLQs once
            assert mock_process.call_count == 2  # 1 iteration * 2 DLQs
            mock_process.assert_any_call(QUEUE_BOT_EVENTS_DLQ)
            mock_process.assert_any_call(QUEUE_NOTIFICATION_DLQ)

    @patch("services.retry.retry_daemon.time")
    @patch("services.retry.retry_daemon.SyncEventPublisher")
    def test_run_loop_handles_exceptions(self, mock_publisher_class, mock_time, daemon):
        """Test run loop continues after exceptions."""
        mock_publisher = Mock()
        mock_publisher_class.return_value = mock_publisher

        iteration_count = [0]

        def shutdown_after_iterations():
            # Shutdown after 2 complete iterations
            if iteration_count[0] >= 2:
                return True
            return False

        def sleep_side_effect(duration):
            iteration_count[0] += 1

        mock_time.sleep.side_effect = sleep_side_effect

        with patch.object(daemon, "_process_dlq") as mock_process:
            # Raise exception on first call, daemon catches it and continues after sleep
            mock_process.side_effect = [
                Exception("First error"),  # First iteration - triggers exception handler
                None,  # Second iteration, first DLQ
                None,  # Second iteration, second DLQ
            ]

            daemon.run(shutdown_after_iterations)

            # Should continue processing after exception (1 failed + 1 successful iteration)
            assert mock_process.call_count == 3

    @patch("services.retry.retry_daemon.SyncEventPublisher")
    def test_run_loop_keyboard_interrupt(self, mock_publisher_class, daemon):
        """Test run loop exits cleanly on KeyboardInterrupt."""
        mock_publisher = Mock()
        mock_publisher_class.return_value = mock_publisher

        with patch.object(daemon, "_process_dlq") as mock_process:
            mock_process.side_effect = KeyboardInterrupt()

            daemon.run(lambda: False)

            mock_process.assert_called_once()

    def test_process_dlq_publisher_not_initialized(self, daemon):
        """Test _process_dlq raises error if publisher not initialized."""
        with patch("pika.BlockingConnection") as mock_connection_class:
            mock_connection = Mock()
            mock_channel = Mock()
            mock_connection_class.return_value = mock_connection
            mock_connection.channel.return_value = mock_channel

            Method = namedtuple("Method", ["message_count", "delivery_tag"])
            mock_queue_state = Mock()
            mock_queue_state.method = Method(message_count=1, delivery_tag=None)
            mock_channel.queue_declare.return_value = mock_queue_state

            event = Event(
                event_type=EventType.GAME_CREATED,
                data={"game_id": "123"},
            )

            mock_method = Method(message_count=1, delivery_tag=1)
            mock_properties = Mock()
            mock_properties.headers = {"x-death": [{"routing-keys": ["game.created"]}]}
            mock_channel.consume.return_value = [
                (mock_method, mock_properties, event.model_dump_json())
            ]

            # Publisher is None
            daemon.publisher = None

            daemon._process_dlq(QUEUE_BOT_EVENTS_DLQ)

            # Should NACK message due to RuntimeError
            mock_channel.basic_nack.assert_called_once_with(1, requeue=True)
