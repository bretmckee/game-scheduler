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


"""Tests for shared game-participation and game-lifecycle metrics."""

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

from shared.services.game_metrics import (
    record_game_cancelled,
    record_game_completed,
    record_game_joined,
    record_game_left,
    record_game_posted,
)


def test_record_game_joined_labels_action_and_source() -> None:
    """record_game_joined adds 1 with action='join' and the given source."""
    mock_counter = MagicMock()

    with patch("shared.services.game_metrics._game_participation_counter", mock_counter):
        record_game_joined("bot")

    mock_counter.add.assert_called_once_with(1, {"action": "join", "source": "bot"})


def test_record_game_left_labels_action_and_source() -> None:
    """record_game_left adds 1 with action='leave' and the given source."""
    mock_counter = MagicMock()

    with patch("shared.services.game_metrics._game_participation_counter", mock_counter):
        record_game_left("api")

    mock_counter.add.assert_called_once_with(1, {"action": "leave", "source": "api"})


def test_record_game_posted_labels_counter_with_schedule() -> None:
    """record_game_posted labels the counter with action, source, hour_of_day, day_of_week."""
    mock_counter = MagicMock()
    scheduled_at = datetime(2026, 7, 17, 20, 30)  # Friday

    with (
        patch("shared.services.game_metrics._game_lifecycle_counter", mock_counter),
        patch("shared.services.game_metrics._game_lead_time_histogram", MagicMock()),
        patch("shared.services.game_metrics._game_length_histogram", MagicMock()),
    ):
        record_game_posted("immediate", scheduled_at, 120)

    mock_counter.add.assert_called_once_with(
        1,
        {"action": "posted", "source": "immediate", "hour_of_day": 20, "day_of_week": "Fri"},
    )


def test_record_game_posted_records_lead_time_hours() -> None:
    """record_game_posted records hours until scheduled_at on the lead-time histogram."""
    mock_histogram = MagicMock()
    now = datetime(2026, 7, 17, 12, 0)
    scheduled_at = now + timedelta(hours=5)

    with (
        patch("shared.services.game_metrics._game_lifecycle_counter", MagicMock()),
        patch("shared.services.game_metrics._game_lead_time_histogram", mock_histogram),
        patch("shared.services.game_metrics._game_length_histogram", MagicMock()),
        patch("shared.services.game_metrics.utc_now", return_value=now),
    ):
        record_game_posted("immediate", scheduled_at, None)

    mock_histogram.record.assert_called_once_with(5.0, {"action": "posted", "source": "immediate"})


def test_record_game_posted_records_length_when_present() -> None:
    """record_game_posted records expected_duration_minutes on the length histogram."""
    mock_histogram = MagicMock()

    with (
        patch("shared.services.game_metrics._game_lifecycle_counter", MagicMock()),
        patch("shared.services.game_metrics._game_lead_time_histogram", MagicMock()),
        patch("shared.services.game_metrics._game_length_histogram", mock_histogram),
    ):
        record_game_posted("deferred", datetime(2026, 7, 17, 20, 0), 90)

    mock_histogram.record.assert_called_once_with(90, {"action": "posted", "source": "deferred"})


def test_record_game_posted_normalizes_aware_scheduled_at() -> None:
    """A timezone-aware scheduled_at (e.g. a directly-constructed model in a test)
    doesn't crash the naive-UTC subtraction against utc_now()."""
    mock_counter = MagicMock()
    scheduled_at = datetime(2026, 7, 17, 20, 30, tzinfo=UTC)

    with (
        patch("shared.services.game_metrics._game_lifecycle_counter", mock_counter),
        patch("shared.services.game_metrics._game_lead_time_histogram", MagicMock()),
        patch("shared.services.game_metrics._game_length_histogram", MagicMock()),
    ):
        record_game_posted("immediate", scheduled_at, None)

    mock_counter.add.assert_called_once_with(
        1,
        {"action": "posted", "source": "immediate", "hour_of_day": 20, "day_of_week": "Fri"},
    )


def test_record_game_posted_skips_length_when_none() -> None:
    """record_game_posted skips the length histogram when duration is unset."""
    mock_histogram = MagicMock()

    with (
        patch("shared.services.game_metrics._game_lifecycle_counter", MagicMock()),
        patch("shared.services.game_metrics._game_lead_time_histogram", MagicMock()),
        patch("shared.services.game_metrics._game_length_histogram", mock_histogram),
    ):
        record_game_posted("deferred", datetime(2026, 7, 17, 20, 0), None)

    mock_histogram.record.assert_not_called()


def test_record_game_cancelled_labels_action_and_source() -> None:
    """record_game_cancelled labels the counter with action='cancelled' and the given source."""
    mock_counter = MagicMock()

    with (
        patch("shared.services.game_metrics._game_lifecycle_counter", mock_counter),
        patch("shared.services.game_metrics._game_lead_time_histogram", MagicMock()),
        patch("shared.services.game_metrics._game_length_histogram", MagicMock()),
    ):
        record_game_cancelled("api", datetime(2026, 7, 18, 9, 0), 60)  # Saturday

    mock_counter.add.assert_called_once_with(
        1,
        {"action": "cancelled", "source": "api", "hour_of_day": 9, "day_of_week": "Sat"},
    )


def test_record_game_completed_uses_scheduler_source() -> None:
    """record_game_completed always labels source='scheduler' — it's never bot/api-initiated."""
    mock_counter = MagicMock()

    with (
        patch("shared.services.game_metrics._game_lifecycle_counter", mock_counter),
        patch("shared.services.game_metrics._game_lead_time_histogram", MagicMock()),
        patch("shared.services.game_metrics._game_length_histogram", MagicMock()),
    ):
        record_game_completed(datetime(2026, 7, 17, 20, 0), 45)

    mock_counter.add.assert_called_once_with(
        1,
        {"action": "completed", "source": "scheduler", "hour_of_day": 20, "day_of_week": "Fri"},
    )
