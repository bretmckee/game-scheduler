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


"""Shared game-participation and game-lifecycle metrics.

Both the Discord bot (button interactions) and the API (frontend requests) let
users join and leave games, and post/cancel games, through independent code
paths. This module gives each concern a single metric name and label taxonomy
to record against, so the independent paths roll up to one queryable signal
instead of drifting apart.
"""

from datetime import UTC, datetime

from opentelemetry import metrics

from shared.models.base import utc_now

_meter = metrics.get_meter(__name__)

_game_participation_counter = _meter.create_counter(
    name="game.participant.change",
    description="Number of game join/leave actions, labeled by action and source",
    unit="1",
)

_game_lifecycle_counter = _meter.create_counter(
    name="game.lifecycle.change",
    description=(
        "Number of game lifecycle transitions (posted/cancelled/completed), "
        "labeled by action, source, and the scheduled start time's hour_of_day "
        "(UTC, 0-23) and day_of_week"
    ),
    unit="1",
)
_game_lead_time_histogram = _meter.create_histogram(
    name="game.lifecycle.lead_time_hours",
    description=(
        "Hours between a lifecycle event and the game's scheduled start time. "
        "Positive means the event happened before the scheduled start (e.g. "
        "cancelled 3 days ahead); negative means after (e.g. completed 2 hours "
        "past its scheduled start)."
    ),
    unit="h",
)
_game_length_histogram = _meter.create_histogram(
    name="game.lifecycle.length_minutes",
    description="Expected game length in minutes, recorded at each lifecycle event",
    unit="min",
)


def record_game_joined(source: str) -> None:
    """Record a successful game join.

    Args:
        source: Where the join originated — "bot" (Discord button) or "api"
            (frontend/direct API request).
    """
    _game_participation_counter.add(1, {"action": "join", "source": source})


def record_game_left(source: str) -> None:
    """Record a successful game leave.

    Args:
        source: Where the leave originated — "bot" (Discord button) or "api"
            (frontend/direct API request).
    """
    _game_participation_counter.add(1, {"action": "leave", "source": source})


def _record_lifecycle_event(
    action: str,
    source: str,
    scheduled_at: datetime,
    expected_duration_minutes: int | None,
) -> None:
    # scheduled_at is naive UTC when loaded from the DB (matching utc_now()), but
    # callers may pass an aware datetime (e.g. constructed directly in tests) —
    # normalize so the subtraction below never raises.
    if scheduled_at.tzinfo is not None:
        scheduled_at = scheduled_at.astimezone(UTC).replace(tzinfo=None)

    _game_lifecycle_counter.add(
        1,
        {
            "action": action,
            "source": source,
            "hour_of_day": scheduled_at.hour,
            "day_of_week": scheduled_at.strftime("%a"),
        },
    )

    lead_time_hours = (scheduled_at - utc_now()).total_seconds() / 3600
    _game_lead_time_histogram.record(lead_time_hours, {"action": action, "source": source})

    if expected_duration_minutes is not None:
        _game_length_histogram.record(
            expected_duration_minutes, {"action": action, "source": source}
        )


def record_game_posted(
    source: str, scheduled_at: datetime, expected_duration_minutes: int | None
) -> None:
    """Record a game announcement being posted to Discord.

    Args:
        source: "immediate" (posted right after creation) or "deferred"
            (posted later by the announcement loop once its post_at time
            arrived).
        scheduled_at: The game's scheduled start time (UTC).
        expected_duration_minutes: The game's expected length in minutes, if set.
    """
    _record_lifecycle_event("posted", source, scheduled_at, expected_duration_minutes)


def record_game_cancelled(
    source: str, scheduled_at: datetime, expected_duration_minutes: int | None
) -> None:
    """Record a game being cancelled.

    Args:
        source: "api" (user-initiated cancel via the web UI) or "bot" (bot
            detected the Discord announcement was deleted and cleaned up the
            orphaned game row).
        scheduled_at: The game's scheduled start time (UTC).
        expected_duration_minutes: The game's expected length in minutes, if set.
    """
    _record_lifecycle_event("cancelled", source, scheduled_at, expected_duration_minutes)


def record_game_completed(scheduled_at: datetime, expected_duration_minutes: int | None) -> None:
    """Record a game transitioning to COMPLETED.

    Always scheduler-driven (see shared/services/game_schedules.py), so there's
    no separate bot/api source to distinguish.

    Args:
        scheduled_at: The game's scheduled start time (UTC).
        expected_duration_minutes: The game's expected length in minutes, if set.
    """
    _record_lifecycle_event("completed", "scheduler", scheduled_at, expected_duration_minutes)
