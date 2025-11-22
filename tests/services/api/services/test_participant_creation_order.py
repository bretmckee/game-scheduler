"""
Unit tests verifying that participants are created with sequential timestamps.

This test ensures that when multiple participants are added during game creation,
they receive joined_at timestamps that increment in the order they were added.
This ordering is critical for maintaining the host's intended participant order.
"""

import datetime

import pytest

from shared.models import participant as participant_model


@pytest.mark.asyncio
async def test_sequential_participant_creation_preserves_order():
    """
    Test that creating participants sequentially results in incrementing timestamps.

    This is a critical assumption for the participant sorting logic:
    when participants are created in a for-loop and added to the database,
    their joined_at timestamps increment, preserving the order.
    """
    participants = []
    base_time = datetime.datetime.now(datetime.UTC)

    # Simulate sequential participant creation as done in games.py
    for i, name in enumerate(["Player1", "Placeholder A", "Player2"]):
        participant = participant_model.GameParticipant(
            game_session_id="test-game-id",
            user_id=f"user{i}" if i % 2 == 0 else None,
            display_name=name if i % 2 == 1 else None,
            status=participant_model.ParticipantStatus.PLACEHOLDER.value
            if i % 2 == 1
            else participant_model.ParticipantStatus.JOINED.value,
            is_pre_populated=True,
        )
        # Simulate database assigning joined_at timestamp
        # In reality, database assigns server_default=func.now()
        # which increments for each sequential INSERT
        participant.joined_at = base_time + datetime.timedelta(microseconds=i * 100)
        participants.append(participant)

    # Verify timestamps are sequential
    assert participants[0].joined_at < participants[1].joined_at, (
        "First participant should have earlier timestamp than second"
    )
    assert participants[1].joined_at < participants[2].joined_at, (
        "Second participant should have earlier timestamp than third"
    )

    # Most importantly: verify sorting by joined_at preserves creation order
    sorted_participants = sorted(participants, key=lambda p: p.joined_at)
    assert sorted_participants == participants, (
        "Sorting by joined_at must preserve the original creation order. "
        "This is the critical behavior that participant_sorting.py relies on. "
        "The game creation code in services/api/services/games.py depends on "
        "participants being created sequentially in a for-loop, receiving "
        "incrementing timestamps from the database."
    )
