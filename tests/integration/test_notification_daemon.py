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


"""Integration tests for notification daemon with PostgreSQL LISTEN/NOTIFY.

These tests are designed to run in Docker with docker-compose where all
services (PostgreSQL, RabbitMQ) are available.
"""

import time
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import text

from services.scheduler.postgres_listener import PostgresNotificationListener
from shared.messaging.infrastructure import QUEUE_BOT_EVENTS
from tests.integration.conftest import get_queue_message_count
from tests.shared.polling import wait_for_db_condition_sync

pytestmark = pytest.mark.integration


@pytest.fixture
def clean_notification_schedule(rabbitmq_channel):
    """Clean RabbitMQ queue before and after test, with daemon processing time."""
    time.sleep(0.5)  # Let daemon process any remaining notifications
    rabbitmq_channel.queue_purge(QUEUE_BOT_EVENTS)

    yield

    time.sleep(0.5)  # Let daemon process cleanup
    rabbitmq_channel.queue_purge(QUEUE_BOT_EVENTS)


class TestPostgresListenerIntegration:
    """Integration tests for PostgreSQL LISTEN/NOTIFY."""

    def test_listener_connects_to_real_database(self, admin_db_url_sync):
        """Listener can connect to actual PostgreSQL database."""
        listener = PostgresNotificationListener(admin_db_url_sync)

        try:
            listener.connect()
            assert listener.conn is not None
            assert not listener.conn.closed
        finally:
            listener.close()

    def test_listener_subscribes_to_channel(self, admin_db_url_sync):
        """Listener can subscribe to notification channel."""
        listener = PostgresNotificationListener(admin_db_url_sync)

        try:
            listener.connect()
            listener.listen("test_channel")

            # Verify channel is registered
            assert "test_channel" in listener._channels
        finally:
            listener.close()

    def test_listener_receives_notify_from_trigger(
        self,
        admin_db_url_sync,
        admin_db_sync,
        clean_notification_schedule,
        test_game_environment,
    ):
        """Listener receives NOTIFY events from PostgreSQL trigger."""
        listener = PostgresNotificationListener(admin_db_url_sync)

        try:
            listener.connect()
            listener.listen("notification_schedule_changed")

            env = test_game_environment()
            notification_time = datetime.now(UTC).replace(tzinfo=None) + timedelta(minutes=5)

            admin_db_sync.execute(
                text(
                    """
                    INSERT INTO notification_schedule
                        (id, game_id, reminder_minutes, notification_time,
                         game_scheduled_at, sent)
                    VALUES (:id, :game_id, :reminder_minutes,
                            :notification_time, :game_scheduled_at, :sent)
                    """
                ),
                {
                    "id": str(uuid4()),
                    "game_id": env["game"]["id"],
                    "reminder_minutes": 60,
                    "notification_time": notification_time,
                    "game_scheduled_at": notification_time + timedelta(minutes=60),
                    "sent": False,
                },
            )
            admin_db_sync.commit()

            # Wait for notification with timeout
            received, payload = listener.wait_for_notification(timeout=2.0)

            assert received is True
            assert payload is not None
            # Trigger only sends NOTIFY for near-term notifications
            # (within 10 minutes), so this may not trigger

        finally:
            listener.close()

    @pytest.mark.xfail(reason="RLS changes may affect PostgreSQL connection timing")
    def test_listener_timeout_when_no_notification(self, admin_db_url_sync):
        """Listener times out when no notifications received."""
        listener = PostgresNotificationListener(admin_db_url_sync)

        try:
            listener.connect()
            listener.listen("notification_schedule_changed")

            # Wait with short timeout
            start_time = time.time()
            received, payload = listener.wait_for_notification(timeout=0.5)
            elapsed_time = time.time() - start_time

            assert received is False
            assert payload is None
            assert 0.4 <= elapsed_time <= 0.7  # Allow some margin

        finally:
            listener.close()


class TestNotificationDaemonIntegration:
    """Integration tests for notification daemon service.

    These tests run against the actual notification-daemon container started
    by docker-compose, validating that the running service processes
    notifications correctly.
    """

    def test_daemon_processes_due_notification(
        self,
        admin_db_sync,
        clean_notification_schedule,
        rabbitmq_channel,
        test_game_environment,
    ):
        """Test that running notification-daemon processes due notifications."""
        env = test_game_environment()

        notif_id = str(uuid4())
        notification_time = datetime.now(UTC).replace(tzinfo=None) - timedelta(minutes=1)

        admin_db_sync.execute(
            text(
                """
                INSERT INTO notification_schedule
                    (id, game_id, reminder_minutes, notification_time,
                     game_scheduled_at, sent)
                VALUES (:id, :game_id, :reminder_minutes,
                        :notification_time, :game_scheduled_at, :sent)
                """
            ),
            {
                "id": notif_id,
                "game_id": env["game"]["id"],
                "reminder_minutes": 60,
                "notification_time": notification_time,
                "game_scheduled_at": notification_time + timedelta(minutes=60),
                "sent": False,
            },
        )
        admin_db_sync.commit()

        result = wait_for_db_condition_sync(
            admin_db_sync,
            "SELECT sent FROM notification_schedule WHERE id = :id",
            {"id": notif_id},
            lambda row: row[0] is True,
            timeout=5,
            interval=0.5,
            description="notification marked as sent",
        )

        assert result[0] is True, "Notification should be marked as sent"

        message_count = get_queue_message_count(rabbitmq_channel, QUEUE_BOT_EVENTS)
        assert message_count == 1, "Should have published 1 notification event"

    def test_daemon_waits_for_future_notification(
        self,
        admin_db_sync,
        clean_notification_schedule,
        rabbitmq_channel,
        test_game_environment,
    ):
        """Test that running daemon doesn't process future notifications."""
        env = test_game_environment()

        notif_id = str(uuid4())
        notification_time = datetime.now(UTC).replace(tzinfo=None) + timedelta(minutes=10)

        admin_db_sync.execute(
            text(
                """
                INSERT INTO notification_schedule
                    (id, game_id, reminder_minutes, notification_time,
                     game_scheduled_at, sent)
                VALUES (:id, :game_id, :reminder_minutes,
                        :notification_time, :game_scheduled_at, :sent)
                """
            ),
            {
                "id": notif_id,
                "game_id": env["game"]["id"],
                "reminder_minutes": 60,
                "notification_time": notification_time,
                "game_scheduled_at": notification_time + timedelta(minutes=60),
                "sent": False,
            },
        )
        admin_db_sync.commit()

        time.sleep(2)

        result = admin_db_sync.execute(
            text("SELECT sent FROM notification_schedule WHERE id = :id"),
            {"id": notif_id},
        ).fetchone()

        assert result[0] is False, "Future notification should not be processed"

        message_count = get_queue_message_count(rabbitmq_channel, QUEUE_BOT_EVENTS)
        assert message_count == 0, "Should have no messages for future notification"
