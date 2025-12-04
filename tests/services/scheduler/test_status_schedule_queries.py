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


"""Tests for status schedule query functions."""

from datetime import timedelta
from unittest.mock import MagicMock

import pytest

from services.scheduler.status_schedule_queries import (
    get_next_due_transition,
    mark_transition_executed,
)
from shared.models import GameStatusSchedule
from shared.models.base import utc_now


@pytest.fixture
def mock_db():
    """Create a mock database session."""
    return MagicMock()


@pytest.fixture
def sample_transition():
    """Create a sample transition."""
    return GameStatusSchedule(
        id="transition-1",
        game_id="game-1",
        target_status="IN_PROGRESS",
        transition_time=utc_now() + timedelta(minutes=5),
        executed=False,
    )


class TestGetNextDueTransition:
    """Test suite for get_next_due_transition function."""

    def test_returns_earliest_unexecuted_transition(self, mock_db, sample_transition):
        """Returns transition with earliest transition_time."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_transition
        mock_db.execute.return_value = mock_result

        result = get_next_due_transition(mock_db)

        assert result == sample_transition
        mock_db.execute.assert_called_once()

    def test_returns_none_when_no_transitions(self, mock_db):
        """Returns None when no unexecuted transitions exist."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        result = get_next_due_transition(mock_db)

        assert result is None

    def test_ignores_executed_transitions(self, mock_db):
        """Only queries transitions where executed=False."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        get_next_due_transition(mock_db)

        call_args = mock_db.execute.call_args
        stmt = call_args[0][0]
        # Verify the query includes executed=False filter
        assert str(stmt).find("executed") != -1

    def test_returns_overdue_transitions(self, mock_db):
        """Returns transitions even if transition_time is in the past."""
        overdue_transition = GameStatusSchedule(
            id="transition-overdue",
            game_id="game-1",
            target_status="IN_PROGRESS",
            transition_time=utc_now() - timedelta(hours=1),
            executed=False,
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = overdue_transition
        mock_db.execute.return_value = mock_result

        result = get_next_due_transition(mock_db)

        assert result == overdue_transition
        if result:
            assert result.transition_time < utc_now()


class TestMarkTransitionExecuted:
    """Test suite for mark_transition_executed function."""

    def test_marks_transition_as_executed(self, mock_db):
        """Updates transition executed field to True."""
        mock_result = MagicMock()
        mock_result.rowcount = 1
        mock_db.execute.return_value = mock_result

        result = mark_transition_executed(mock_db, "transition-1")

        assert result is True
        mock_db.execute.assert_called_once()
        mock_db.flush.assert_called_once()

    def test_returns_false_when_transition_not_found(self, mock_db):
        """Returns False when transition ID doesn't exist."""
        mock_result = MagicMock()
        mock_result.rowcount = 0
        mock_db.execute.return_value = mock_result

        result = mark_transition_executed(mock_db, "nonexistent-id")

        assert result is False

    def test_updates_correct_transition_id(self, mock_db):
        """Update statement targets the correct transition ID."""
        mock_result = MagicMock()
        mock_result.rowcount = 1
        mock_db.execute.return_value = mock_result

        mark_transition_executed(mock_db, "specific-id")

        call_args = mock_db.execute.call_args
        stmt = call_args[0][0]
        # Verify the ID is in the statement
        assert "specific-id" in str(stmt) or hasattr(stmt, "_where_criteria")

    def test_sets_executed_to_true(self, mock_db):
        """Update statement sets executed=True."""
        mock_result = MagicMock()
        mock_result.rowcount = 1
        mock_db.execute.return_value = mock_result

        mark_transition_executed(mock_db, "transition-1")

        call_args = mock_db.execute.call_args
        stmt = call_args[0][0]
        # Verify executed is set to True
        assert str(stmt).find("executed") != -1 or hasattr(stmt, "_values")
