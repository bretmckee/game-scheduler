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


"""Unit tests for event builder functions."""

from datetime import timedelta
from uuid import uuid4

from shared.models import GameStatus, GameStatusSchedule, NotificationSchedule
from shared.models.base import utc_now
from shared.models.bot_action_queue import BotActionQueue
from shared.services.event_builders import (
    build_notification_event,
    build_status_transition_event,
)


class TestBuildNotificationEvent:
    """Test build_notification_event function."""

    def test_returns_bot_action_queue_instance(self):
        """build_notification_event returns a BotActionQueue row."""
        notification = NotificationSchedule(
            id=str(uuid4()),
            game_id=str(uuid4()),
            notification_type="reminder",
            reminder_minutes=60,
            notification_time=utc_now() + timedelta(minutes=60),
            game_scheduled_at=utc_now() + timedelta(hours=2),
            sent=False,
        )

        result = build_notification_event(notification)

        assert isinstance(result, BotActionQueue)

    def test_notification_due_action_type(self):
        """Row has action_type='notification_due'."""
        notification = NotificationSchedule(
            id=str(uuid4()),
            game_id=str(uuid4()),
            notification_type="reminder",
            reminder_minutes=60,
            notification_time=utc_now() + timedelta(minutes=60),
            game_scheduled_at=None,
            sent=False,
        )

        result = build_notification_event(notification)

        assert result.action_type == "notification_due"

    def test_game_id_stored_on_row(self):
        """Row game_id matches the notification's game_id."""
        game_id = str(uuid4())
        notification = NotificationSchedule(
            id=str(uuid4()),
            game_id=game_id,
            notification_type="reminder",
            reminder_minutes=60,
            notification_time=utc_now() + timedelta(minutes=60),
            game_scheduled_at=None,
            sent=False,
        )

        result = build_notification_event(notification)

        assert result.game_id == game_id

    def test_payload_contains_notification_type_for_reminder(self):
        """Payload stores notification_type='reminder' and participant_id=None."""
        notification = NotificationSchedule(
            id=str(uuid4()),
            game_id=str(uuid4()),
            notification_type="reminder",
            participant_id=None,
            reminder_minutes=60,
            notification_time=utc_now() + timedelta(minutes=60),
            game_scheduled_at=None,
            sent=False,
        )

        result = build_notification_event(notification)

        assert result.payload["notification_type"] == "reminder"
        assert result.payload["participant_id"] is None

    def test_payload_contains_participant_id_for_join_notification(self):
        """Payload stores participant_id for join_notification type."""
        participant_id = str(uuid4())
        notification = NotificationSchedule(
            id=str(uuid4()),
            game_id=str(uuid4()),
            notification_type="join_notification",
            participant_id=participant_id,
            reminder_minutes=None,
            notification_time=utc_now() + timedelta(seconds=60),
            game_scheduled_at=None,
            sent=False,
        )

        result = build_notification_event(notification)

        assert result.payload["notification_type"] == "join_notification"
        assert result.payload["participant_id"] == participant_id


class TestBuildStatusTransitionEvent:
    """Test build_status_transition_event function."""

    def test_returns_bot_action_queue_instance(self):
        """build_status_transition_event returns a BotActionQueue row."""
        transition = GameStatusSchedule(
            id=str(uuid4()),
            game_id=str(uuid4()),
            target_status=GameStatus.IN_PROGRESS.value,
            transition_time=utc_now(),
            executed=False,
        )

        result = build_status_transition_event(transition)

        assert isinstance(result, BotActionQueue)

    def test_status_transition_due_action_type(self):
        """Row has action_type='status_transition_due'."""
        transition = GameStatusSchedule(
            id=str(uuid4()),
            game_id=str(uuid4()),
            target_status=GameStatus.IN_PROGRESS.value,
            transition_time=utc_now(),
            executed=False,
        )

        result = build_status_transition_event(transition)

        assert result.action_type == "status_transition_due"

    def test_game_id_and_payload_fields(self):
        """Row stores game_id and payload with target_status and transition_time ISO string."""
        game_id = str(uuid4())
        transition_time = utc_now()
        transition = GameStatusSchedule(
            id=str(uuid4()),
            game_id=game_id,
            target_status=GameStatus.COMPLETED.value,
            transition_time=transition_time,
            executed=False,
        )

        result = build_status_transition_event(transition)

        assert result.game_id == game_id
        assert result.payload["target_status"] == GameStatus.COMPLETED.value
        assert result.payload["transition_time"] == transition_time.isoformat()
