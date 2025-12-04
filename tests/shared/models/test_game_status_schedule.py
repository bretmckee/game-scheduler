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


"""Tests for GameStatusSchedule model."""

from datetime import timedelta

from shared.models import GameStatusSchedule
from shared.models.base import utc_now


class TestGameStatusScheduleModel:
    """Test suite for GameStatusSchedule model."""

    def test_create_status_schedule(self):
        """Can create a GameStatusSchedule instance."""
        transition_time = utc_now() + timedelta(hours=1)
        schedule = GameStatusSchedule(
            game_id="game-123",
            target_status="IN_PROGRESS",
            transition_time=transition_time,
        )

        assert schedule.game_id == "game-123"
        assert schedule.target_status == "IN_PROGRESS"
        assert schedule.transition_time == transition_time

    def test_default_values(self):
        """Default values are set when explicitly provided or after persist."""
        schedule = GameStatusSchedule(
            game_id="game-123",
            target_status="IN_PROGRESS",
            transition_time=utc_now(),
            executed=False,
        )

        assert schedule.executed is False

    def test_id_generation(self):
        """ID can be generated using default function."""
        from shared.models.base import generate_uuid

        schedule = GameStatusSchedule(
            id=generate_uuid(),
            game_id="game-1",
            target_status="IN_PROGRESS",
            transition_time=utc_now(),
        )

        assert schedule.id is not None

    def test_executed_flag(self):
        """Executed flag can be set and retrieved."""
        schedule = GameStatusSchedule(
            game_id="game-123",
            target_status="IN_PROGRESS",
            transition_time=utc_now(),
            executed=False,
        )

        assert schedule.executed is False

        schedule.executed = True
        assert schedule.executed is True

    def test_transition_time_in_past(self):
        """Can create schedule with transition_time in the past."""
        past_time = utc_now() - timedelta(hours=1)
        schedule = GameStatusSchedule(
            game_id="game-123",
            target_status="IN_PROGRESS",
            transition_time=past_time,
        )

        assert schedule.transition_time < utc_now()

    def test_transition_time_in_future(self):
        """Can create schedule with transition_time in the future."""
        future_time = utc_now() + timedelta(hours=1)
        schedule = GameStatusSchedule(
            game_id="game-123",
            target_status="IN_PROGRESS",
            transition_time=future_time,
        )

        assert schedule.transition_time > utc_now()

    def test_target_status_values(self):
        """Can set various target status values."""
        statuses = ["IN_PROGRESS", "COMPLETED", "CANCELLED"]

        for status in statuses:
            schedule = GameStatusSchedule(
                game_id="game-123",
                target_status=status,
                transition_time=utc_now(),
            )
            assert schedule.target_status == status
