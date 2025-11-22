"""Tests for participant sorting utilities."""

from datetime import UTC, datetime
from unittest.mock import Mock

import pytest

from shared.utils.participant_sorting import sort_participants


@pytest.fixture
def mock_participant():
    """Create a mock participant with configurable attributes."""

    def _create(
        participant_id: str,
        is_pre_populated: bool = False,
        status: str = "JOINED",
        joined_at: datetime | None = None,
    ):
        participant = Mock()
        participant.id = participant_id
        participant.is_pre_populated = is_pre_populated
        participant.status = status
        participant.joined_at = joined_at or datetime.now(UTC)
        return participant

    return _create


class TestSortParticipants:
    """Tests for sort_participants function."""

    def test_empty_list_returns_empty(self, mock_participant):
        """Test that empty list returns empty list."""
        result = sort_participants([])
        assert result == []

    def test_single_participant_returns_unchanged(self, mock_participant):
        """Test that single participant list returns unchanged."""
        p1 = mock_participant("1")
        result = sort_participants([p1])
        assert result == [p1]

    def test_pre_populated_comes_before_regular(self, mock_participant):
        """Test that pre-populated participants come before regular participants."""
        base_time = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)
        p1 = mock_participant("1", joined_at=base_time)
        p2 = mock_participant("2", is_pre_populated=True, joined_at=base_time)

        result = sort_participants([p1, p2])
        assert result == [p2, p1]

    def test_placeholders_come_before_regular(self, mock_participant):
        """Test that placeholder participants come before regular participants."""
        base_time = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)
        p1 = mock_participant("1", joined_at=base_time)
        p2 = mock_participant("2", status="PLACEHOLDER", joined_at=base_time)

        result = sort_participants([p1, p2])
        assert result == [p2, p1]

    def test_pre_populated_order_preserved(self, mock_participant):
        """Test that pre-populated participants maintain creation order."""
        base_time = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)
        p1 = mock_participant("1", is_pre_populated=True, joined_at=base_time)
        p2 = mock_participant("2", is_pre_populated=True, joined_at=base_time)
        p3 = mock_participant("3", is_pre_populated=True, joined_at=base_time)

        # All have same timestamp, should maintain input order
        result = sort_participants([p1, p2, p3])
        assert result == [p1, p2, p3]

        # Reverse input order
        result = sort_participants([p3, p2, p1])
        assert result == [p3, p2, p1]

    def test_placeholder_order_preserved(self, mock_participant):
        """Test that placeholder participants maintain creation order."""
        base_time = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)
        p1 = mock_participant("1", status="PLACEHOLDER", joined_at=base_time)
        p2 = mock_participant("2", status="PLACEHOLDER", joined_at=base_time)
        p3 = mock_participant("3", status="PLACEHOLDER", joined_at=base_time)

        # All have same timestamp, should maintain input order
        result = sort_participants([p1, p2, p3])
        assert result == [p1, p2, p3]

        # Reverse input order
        result = sort_participants([p3, p2, p1])
        assert result == [p3, p2, p1]

    def test_regular_sorted_by_join_time(self, mock_participant):
        """Test that regular participants are sorted by joined_at timestamp."""
        t1 = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)
        t2 = datetime(2025, 1, 1, 12, 1, 0, tzinfo=UTC)
        t3 = datetime(2025, 1, 1, 12, 2, 0, tzinfo=UTC)

        p1 = mock_participant("1", joined_at=t2)
        p2 = mock_participant("2", joined_at=t3)
        p3 = mock_participant("3", joined_at=t1)

        result = sort_participants([p1, p2, p3])
        assert result == [p3, p1, p2]

    def test_mixed_participants_correct_order(self, mock_participant):
        """Test complex scenario with all participant types."""
        t1 = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)
        t2 = datetime(2025, 1, 1, 12, 1, 0, tzinfo=UTC)
        t3 = datetime(2025, 1, 1, 12, 2, 0, tzinfo=UTC)

        pre1 = mock_participant("pre1", is_pre_populated=True, joined_at=t1)
        pre2 = mock_participant("pre2", is_pre_populated=True, joined_at=t1)
        placeholder = mock_participant("placeholder", status="PLACEHOLDER", joined_at=t1)
        regular1 = mock_participant("reg1", joined_at=t3)
        regular2 = mock_participant("reg2", joined_at=t2)

        result = sort_participants([regular1, pre2, placeholder, regular2, pre1])

        # Expected order: priority participants in input order, then regular by join time
        assert result == [pre2, placeholder, pre1, regular2, regular1]

    def test_pre_populated_placeholder_order_preserved(self, mock_participant):
        """Test that pre-populated and placeholder participants maintain relative order."""
        base_time = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)
        pre = mock_participant("pre", is_pre_populated=True, joined_at=base_time)
        ph = mock_participant("ph", status="PLACEHOLDER", joined_at=base_time)

        # Pre-populated first
        result = sort_participants([pre, ph])
        assert result == [pre, ph]

        # Placeholder first
        result = sort_participants([ph, pre])
        assert result == [ph, pre]

    def test_dropped_status_included(self, mock_participant):
        """Test that dropped participants are included in sorting."""
        t1 = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)
        t2 = datetime(2025, 1, 1, 12, 1, 0, tzinfo=UTC)

        dropped = mock_participant("dropped", status="DROPPED", joined_at=t1)
        joined = mock_participant("joined", status="JOINED", joined_at=t2)

        result = sort_participants([joined, dropped])
        # Both treated as regular, sorted by time
        assert result == [dropped, joined]

    def test_large_list_maintains_order(self, mock_participant):
        """Test that sorting works correctly with larger lists."""
        base_time = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)

        # Create 5 priority and 10 regular participants
        priority = [
            mock_participant(f"priority{i}", is_pre_populated=True, joined_at=base_time)
            for i in range(5)
        ]
        regular = [
            mock_participant(f"regular{i}", joined_at=base_time.replace(minute=i))
            for i in range(10)
        ]

        # Mix them up
        mixed = regular[5:] + priority[2:] + regular[:5] + priority[:2]

        result = sort_participants(mixed)

        # First 5 should be priority in mixed order
        assert result[:5] == priority[2:] + priority[:2]
        # Next 10 should be regular sorted by time
        assert result[5:] == regular
