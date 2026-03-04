# Copyright 2026 Bret McKee
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


"""Integration tests for clone_confirmation notification daemon processing.

Verifies that the notification daemon picks up clone_confirmation records,
marks them as sent, and publishes a NOTIFICATION_DUE event to RabbitMQ with
the correct notification_type in the payload.
"""

import json
import time
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import text

from shared.messaging.infrastructure import QUEUE_BOT_EVENTS
from shared.models.participant import ParticipantType
from tests.integration.conftest import consume_one_message, get_queue_message_count
from tests.shared.polling import wait_for_db_condition_sync

pytestmark = pytest.mark.integration


@pytest.fixture
def clean_notifications_queue(rabbitmq_channel):
    """Purge the bot events queue before and after the test."""
    time.sleep(0.5)
    rabbitmq_channel.queue_purge(QUEUE_BOT_EVENTS)

    yield

    time.sleep(0.5)
    rabbitmq_channel.queue_purge(QUEUE_BOT_EVENTS)


def _insert_participant(admin_db_sync, game_id: str, user_id: str) -> str:
    """Insert a game participant and return its ID."""
    participant_id = str(uuid4())
    admin_db_sync.execute(
        text(
            "INSERT INTO game_participants "
            "(id, game_session_id, user_id, position, position_type) "
            "VALUES (:id, :game_id, :user_id, :position, :position_type)"
        ),
        {
            "id": participant_id,
            "game_id": game_id,
            "user_id": user_id,
            "position": 1,
            "position_type": int(ParticipantType.HOST_ADDED),
        },
    )
    admin_db_sync.commit()
    return participant_id


class TestCloneConfirmationNotificationDaemon:
    """Integration tests for notification daemon processing of clone_confirmation records."""

    def test_daemon_fires_clone_confirmation_notification(
        self,
        admin_db_sync,
        clean_notifications_queue,
        rabbitmq_channel,
        test_game_environment,
    ):
        """Notification daemon marks clone_confirmation records sent and publishes to RabbitMQ."""
        env = test_game_environment()
        game_id = env["game"]["id"]
        user_id = env["user"]["id"]

        participant_id = _insert_participant(admin_db_sync, game_id, user_id)

        notif_id = str(uuid4())
        notification_time = datetime.now(UTC).replace(tzinfo=None) - timedelta(minutes=1)
        game_scheduled_at = datetime.now(UTC).replace(tzinfo=None) + timedelta(hours=2)

        admin_db_sync.execute(
            text(
                """
                INSERT INTO notification_schedule
                    (id, game_id, reminder_minutes, notification_time,
                     game_scheduled_at, sent, notification_type, participant_id)
                VALUES (:id, :game_id, :reminder_minutes,
                        :notification_time, :game_scheduled_at, :sent,
                        :notification_type, :participant_id)
                """
            ),
            {
                "id": notif_id,
                "game_id": game_id,
                "reminder_minutes": None,
                "notification_time": notification_time,
                "game_scheduled_at": game_scheduled_at,
                "sent": False,
                "notification_type": "clone_confirmation",
                "participant_id": participant_id,
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
            description="clone_confirmation notification marked as sent",
        )
        assert result[0] is True, "clone_confirmation notification should be marked as sent"

        message_count = get_queue_message_count(rabbitmq_channel, QUEUE_BOT_EVENTS)
        assert message_count == 1, "Should have published 1 clone_confirmation notification event"

        _method, _properties, body = consume_one_message(
            rabbitmq_channel, QUEUE_BOT_EVENTS, timeout=5
        )
        assert body is not None, "RabbitMQ message body should not be None"
        message = json.loads(body)
        assert message["data"]["notification_type"] == "clone_confirmation"
        assert message["data"]["participant_id"] == participant_id
