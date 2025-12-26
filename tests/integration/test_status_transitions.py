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


"""Integration tests for status transition daemon with PostgreSQL LISTEN/NOTIFY.

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
def clean_game_status_schedule(db_session, rabbitmq_channel):
    """Clean game_status_schedule table and queue before and after test."""
    db_session.execute(text("DELETE FROM game_status_schedule"))
    db_session.commit()
    time.sleep(0.5)  # Let daemon process any remaining transitions
    rabbitmq_channel.queue_purge(QUEUE_BOT_EVENTS)

    yield

    db_session.execute(text("DELETE FROM game_status_schedule"))
    db_session.commit()
    time.sleep(0.5)  # Let daemon process cleanup
    rabbitmq_channel.queue_purge(QUEUE_BOT_EVENTS)


@pytest.fixture
def test_game_session(db_session):
    """
    Create minimal test data for foreign key constraints.

    Creates: guild -> channel -> user -> game_session
    Returns the game_session.id for use in game_status_schedule inserts.
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
            "status": "SCHEDULED",
            "created_at": now,
            "updated_at": now,
        },
    )
    db_session.commit()

    yield game_id

    # Cleanup in reverse order
    db_session.execute(
        text("DELETE FROM game_status_schedule WHERE game_id = :game_id"),
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
    """Integration tests for PostgreSQL LISTEN/NOTIFY on game_status_schedule."""

    def test_listener_receives_notify_from_status_schedule_trigger(
        self, db_url, db_session, clean_game_status_schedule, test_game_session
    ):
        """Listener receives NOTIFY events from game_status_schedule trigger."""
        listener = PostgresNotificationListener(db_url)

        try:
            listener.connect()
            listener.listen("game_status_schedule_changed")

            # Insert status schedule record (should trigger NOTIFY)
            game_id = test_game_session
            transition_time = datetime.now(UTC).replace(tzinfo=None) + timedelta(minutes=5)

            db_session.execute(
                text(
                    """
                    INSERT INTO game_status_schedule
                        (id, game_id, target_status, transition_time, executed)
                    VALUES (:id, :game_id, :target_status, :transition_time, :executed)
                    """
                ),
                {
                    "id": str(uuid4()),
                    "game_id": game_id,
                    "target_status": "IN_PROGRESS",
                    "transition_time": transition_time,
                    "executed": False,
                },
            )
            db_session.commit()

            # Wait for notification with timeout
            received, payload = listener.wait_for_notification(timeout=2.0)

            assert received is True
            assert payload is not None

        finally:
            listener.close()


class TestStatusTransitionDaemonIntegration:
    """Integration tests for status transition daemon service.

    These tests run against the actual status-transition-daemon container
    started by docker-compose, validating that the running service processes
    status transitions correctly.
    """

    def test_daemon_transitions_game_status_when_due(
        self,
        db_session,
        clean_game_status_schedule,
        test_game_session,
        rabbitmq_channel,
    ):
        """Test that running status-transition-daemon processes due transitions."""
        game_id = test_game_session
        schedule_id = str(uuid4())
        transition_time = datetime.now(UTC).replace(tzinfo=None) - timedelta(minutes=1)

        db_session.execute(
            text(
                """
                INSERT INTO game_status_schedule
                    (id, game_id, target_status, transition_time, executed)
                VALUES (:id, :game_id, :target_status, :transition_time, :executed)
                """
            ),
            {
                "id": schedule_id,
                "game_id": game_id,
                "target_status": "IN_PROGRESS",
                "transition_time": transition_time,
                "executed": False,
            },
        )
        db_session.commit()

        result = wait_for_db_condition_sync(
            db_session,
            "SELECT executed FROM game_status_schedule WHERE id = :id",
            {"id": schedule_id},
            lambda row: row[0] is True,
            timeout=5,
            interval=0.5,
            description="transition marked as executed",
        )

        assert result[0] is True, "Transition should be marked as executed"

        message_count = get_queue_message_count(rabbitmq_channel, QUEUE_BOT_EVENTS)
        assert message_count == 1, "Should have published 1 status transition event"

    def test_daemon_waits_for_future_transition(
        self,
        db_session,
        clean_game_status_schedule,
        test_game_session,
        rabbitmq_channel,
    ):
        """Test that running daemon doesn't process future transitions."""
        game_id = test_game_session
        schedule_id = str(uuid4())
        transition_time = datetime.now(UTC).replace(tzinfo=None) + timedelta(minutes=10)

        db_session.execute(
            text(
                """
                INSERT INTO game_status_schedule
                    (id, game_id, target_status, transition_time, executed)
                VALUES (:id, :game_id, :target_status, :transition_time, :executed)
                """
            ),
            {
                "id": schedule_id,
                "game_id": game_id,
                "target_status": "IN_PROGRESS",
                "transition_time": transition_time,
                "executed": False,
            },
        )
        db_session.commit()

        time.sleep(2)

        result = db_session.execute(
            text("SELECT executed FROM game_status_schedule WHERE id = :id"),
            {"id": schedule_id},
        ).fetchone()

        assert result[0] is False, "Future transition should not be processed"

        message_count = get_queue_message_count(rabbitmq_channel, QUEUE_BOT_EVENTS)
        assert message_count == 0, "Should have no messages for future transition"
