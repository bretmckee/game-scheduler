"""Participant sorting utilities for consistent ordering across services."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from shared.models.participant import GameParticipant


def sort_participants(participants: list["GameParticipant"]) -> list["GameParticipant"]:
    """Sort participants by priority and join time.

    Two classes of participants:
    1. Priority participants (pre_filled_position set) - sorted by pre_filled_position
    2. Regular participants (pre_filled_position NULL) - sorted by joined_at

    Args:
        participants: List of GameParticipant models to sort

    Returns:
        Sorted list with priority participants first (by position),
        followed by regular participants (by join time)
    """
    priority_participants = sorted(
        [p for p in participants if p.pre_filled_position is not None],
        key=lambda p: p.pre_filled_position,
    )

    regular_participants = sorted(
        [p for p in participants if p.pre_filled_position is None],
        key=lambda p: p.joined_at,
    )

    return priority_participants + regular_participants
