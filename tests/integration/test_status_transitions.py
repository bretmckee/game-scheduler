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
def purge_bot_events_queue(rabbitmq_channel):
    """Purge bot_events queue before and after test to prevent cross-test pollution."""
    rabbitmq_channel.queue_purge(QUEUE_BOT_EVENTS)
    yield
    time.sleep(0.5)  # Let daemon process any remaining messages
    rabbitmq_channel.queue_purge(QUEUE_BOT_EVENTS)


class TestPostgresListenerIntegration:
    """Integration tests for PostgreSQL LISTEN/NOTIFY on game_status_schedule."""

    def test_listener_receives_notify_from_status_schedule_trigger(
        self,
        admin_db_url_sync,
        admin_db_sync,
        purge_bot_events_queue,
        test_game_environment,
    ):
        """Listener receives NOTIFY events from game_status_schedule trigger."""
        listener = PostgresNotificationListener(admin_db_url_sync)

        try:
            listener.connect()
            listener.listen("game_status_schedule_changed")

            env = test_game_environment()
            transition_time = datetime.now(UTC).replace(tzinfo=None) + timedelta(minutes=5)

            admin_db_sync.execute(
                text(
                    """
                    INSERT INTO game_status_schedule
                        (id, game_id, target_status, transition_time, executed)
                    VALUES (:id, :game_id, :target_status, :transition_time, :executed)
                    """
                ),
                {
                    "id": str(uuid4()),
                    "game_id": env["game"]["id"],
                    "target_status": "IN_PROGRESS",
                    "transition_time": transition_time,
                    "executed": False,
                },
            )
            admin_db_sync.commit()

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
        admin_db_sync,
        purge_bot_events_queue,
        test_game_environment,
        rabbitmq_channel,
    ):
        """Test that running status-transition-daemon processes due transitions."""
        env = test_game_environment()
        schedule_id = str(uuid4())
        transition_time = datetime.now(UTC).replace(tzinfo=None) - timedelta(minutes=1)

        admin_db_sync.execute(
            text(
                """
                INSERT INTO game_status_schedule
                    (id, game_id, target_status, transition_time, executed)
                VALUES (:id, :game_id, :target_status, :transition_time, :executed)
                """
            ),
            {
                "id": schedule_id,
                "game_id": env["game"]["id"],
                "target_status": "IN_PROGRESS",
                "transition_time": transition_time,
                "executed": False,
            },
        )
        admin_db_sync.commit()

        result = wait_for_db_condition_sync(
            admin_db_sync,
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
        admin_db_sync,
        purge_bot_events_queue,
        test_game_environment,
        rabbitmq_channel,
    ):
        """Test that running daemon doesn't process future transitions."""
        env = test_game_environment()
        schedule_id = str(uuid4())
        transition_time = datetime.now(UTC).replace(tzinfo=None) + timedelta(minutes=10)

        admin_db_sync.execute(
            text(
                """
                INSERT INTO game_status_schedule
                    (id, game_id, target_status, transition_time, executed)
                VALUES (:id, :game_id, :target_status, :transition_time, :executed)
                """
            ),
            {
                "id": schedule_id,
                "game_id": env["game"]["id"],
                "target_status": "IN_PROGRESS",
                "transition_time": transition_time,
                "executed": False,
            },
        )
        admin_db_sync.commit()

        time.sleep(2)

        result = admin_db_sync.execute(
            text("SELECT executed FROM game_status_schedule WHERE id = :id"),
            {"id": schedule_id},
        ).fetchone()

        assert result[0] is False, "Future transition should not be processed"

        message_count = get_queue_message_count(rabbitmq_channel, QUEUE_BOT_EVENTS)
        assert message_count == 0, "Should have no messages for future transition"
