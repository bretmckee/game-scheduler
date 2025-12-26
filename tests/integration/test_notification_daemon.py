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


"""Integration tests for notification daemon with PostgreSQL LISTEN/NOTIFY.

These tests are designed to run in Docker with docker-compose where all
services (PostgreSQL, RabbitMQ) are available.
"""

import os
import time
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from services.scheduler.postgres_listener import PostgresNotificationListener
from shared.messaging.infrastructure import QUEUE_BOT_EVENTS
from tests.shared.polling import wait_for_db_condition_sync

pytestmark = pytest.mark.integration


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


@pytest.fixture(scope="module")
def db_url():
    """Get database URL from environment (set by docker-compose)."""
    return os.getenv(
        "DATABASE_URL",
        "postgresql://gamebot:dev_password_change_in_prod@postgres:5432/game_scheduler",
    )


@pytest.fixture
def db_session(db_url):
    """Create a database session for tests."""
    sync_url = db_url.replace("postgresql://", "postgresql+psycopg2://")
    engine = create_engine(sync_url, pool_pre_ping=True)
    session_local = sessionmaker(bind=engine)

    session = session_local()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture
def clean_notification_schedule(db_session, rabbitmq_channel):
    """Clean notification_schedule table and queue before and after test."""
    db_session.execute(text("DELETE FROM notification_schedule"))
    db_session.commit()
    time.sleep(0.5)  # Let daemon process any remaining notifications
    rabbitmq_channel.queue_purge(QUEUE_BOT_EVENTS)

    yield

    db_session.execute(text("DELETE FROM notification_schedule"))
    db_session.commit()
    time.sleep(0.5)  # Let daemon process cleanup
    rabbitmq_channel.queue_purge(QUEUE_BOT_EVENTS)


@pytest.fixture
def test_game_session(db_session):
    """
    Create minimal test data for foreign key constraints.

    Creates: guild -> channel -> user -> game_session
    Returns the game_session.id for use in notification_schedule inserts.
    """
    guild_id = str(uuid4())
    channel_id = str(uuid4())
    user_id = str(uuid4())
    game_id = str(uuid4())
    now = datetime.now(UTC).replace(tzinfo=None)

    db_session.execute(
        text(
            "INSERT INTO guild_configurations "
            "(id, guild_id, created_at, updated_at) "
            "VALUES (:id, :guild_id, :created_at, :updated_at)"
        ),
        {
            "id": guild_id,
            "guild_id": "123456789",
            "created_at": now,
            "updated_at": now,
        },
    )

    db_session.execute(
        text(
            "INSERT INTO channel_configurations "
            "(id, channel_id, guild_id, created_at, updated_at) "
            "VALUES (:id, :channel_id, :guild_id, :created_at, :updated_at)"
        ),
        {
            "id": channel_id,
            "channel_id": "987654321",
            "guild_id": guild_id,
            "created_at": now,
            "updated_at": now,
        },
    )

    db_session.execute(
        text(
            "INSERT INTO users (id, discord_id, created_at, updated_at) "
            "VALUES (:id, :discord_id, :created_at, :updated_at)"
        ),
        {
            "id": user_id,
            "discord_id": "111222333",
            "created_at": now,
            "updated_at": now,
        },
    )

    db_session.execute(
        text(
            "INSERT INTO game_sessions "
            "(id, title, scheduled_at, guild_id, channel_id, host_id, "
            "status, created_at, updated_at) "
            "VALUES (:id, :title, :scheduled_at, :guild_id, :channel_id, :host_id, "
            ":status, :created_at, :updated_at)"
        ),
        {
            "id": game_id,
            "title": "Test Game",
            "scheduled_at": now + timedelta(hours=2),
            "guild_id": guild_id,
            "channel_id": channel_id,
            "host_id": user_id,
            "status": "scheduled",
            "created_at": now,
            "updated_at": now,
        },
    )
    db_session.commit()

    yield game_id

    # Cleanup in reverse order
    db_session.execute(
        text("DELETE FROM notification_schedule WHERE game_id = :game_id"),
        {"game_id": game_id},
    )
    db_session.execute(text("DELETE FROM game_sessions WHERE id = :id"), {"id": game_id})
    db_session.execute(text("DELETE FROM users WHERE id = :id"), {"id": user_id})
    db_session.execute(
        text("DELETE FROM channel_configurations WHERE id = :id"), {"id": channel_id}
    )
    db_session.execute(text("DELETE FROM guild_configurations WHERE id = :id"), {"id": guild_id})
    db_session.commit()


@pytest.fixture
def rabbitmq_url():
    """Get RabbitMQ URL from environment (set by docker-compose)."""
    return os.getenv("RABBITMQ_URL", "amqp://gamebot:dev_password_change_in_prod@rabbitmq:5672/")


class TestPostgresListenerIntegration:
    """Integration tests for PostgreSQL LISTEN/NOTIFY."""

    def test_listener_connects_to_real_database(self, db_url):
        """Listener can connect to actual PostgreSQL database."""
        listener = PostgresNotificationListener(db_url)

        try:
            listener.connect()
            assert listener.conn is not None
            assert not listener.conn.closed
        finally:
            listener.close()

    def test_listener_subscribes_to_channel(self, db_url):
        """Listener can subscribe to notification channel."""
        listener = PostgresNotificationListener(db_url)

        try:
            listener.connect()
            listener.listen("test_channel")

            # Verify channel is registered
            assert "test_channel" in listener._channels
        finally:
            listener.close()

    def test_listener_receives_notify_from_trigger(
        self, db_url, db_session, clean_notification_schedule, test_game_session
    ):
        """Listener receives NOTIFY events from PostgreSQL trigger."""
        listener = PostgresNotificationListener(db_url)

        try:
            listener.connect()
            listener.listen("notification_schedule_changed")

            # Insert notification record (should trigger NOTIFY)
            game_id = test_game_session
            notification_time = datetime.now(UTC).replace(tzinfo=None) + timedelta(minutes=5)

            db_session.execute(
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
                    "game_id": game_id,
                    "reminder_minutes": 60,
                    "notification_time": notification_time,
                    "game_scheduled_at": notification_time + timedelta(minutes=60),
                    "sent": False,
                },
            )
            db_session.commit()

            # Wait for notification with timeout
            received, payload = listener.wait_for_notification(timeout=2.0)

            assert received is True
            assert payload is not None
            # Trigger only sends NOTIFY for near-term notifications
            # (within 10 minutes), so this may not trigger

        finally:
            listener.close()

    def test_listener_timeout_when_no_notification(self, db_url):
        """Listener times out when no notifications received."""
        listener = PostgresNotificationListener(db_url)

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
        db_session,
        clean_notification_schedule,
        test_game_session,
        rabbitmq_channel,
    ):
        """Test that running notification-daemon processes due notifications."""
        game_id = test_game_session
        notif_id = str(uuid4())
        notification_time = datetime.now(UTC).replace(tzinfo=None) - timedelta(minutes=1)

        db_session.execute(
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
                "game_id": game_id,
                "reminder_minutes": 60,
                "notification_time": notification_time,
                "game_scheduled_at": notification_time + timedelta(minutes=60),
                "sent": False,
            },
        )
        db_session.commit()

        result = wait_for_db_condition_sync(
            db_session,
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
        db_session,
        clean_notification_schedule,
        test_game_session,
        rabbitmq_channel,
    ):
        """Test that running daemon doesn't process future notifications."""
        game_id = test_game_session
        notif_id = str(uuid4())
        notification_time = datetime.now(UTC).replace(tzinfo=None) + timedelta(minutes=10)

        db_session.execute(
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
                "game_id": game_id,
                "reminder_minutes": 60,
                "notification_time": notification_time,
                "game_scheduled_at": notification_time + timedelta(minutes=60),
                "sent": False,
            },
        )
        db_session.commit()

        time.sleep(2)

        result = db_session.execute(
            text("SELECT sent FROM notification_schedule WHERE id = :id"),
            {"id": notif_id},
        ).fetchone()

        assert result[0] is False, "Future notification should not be processed"

        message_count = get_queue_message_count(rabbitmq_channel, QUEUE_BOT_EVENTS)
        assert message_count == 0, "Should have no messages for future notification"
