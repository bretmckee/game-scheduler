"""Status transition utilities for game lifecycle management."""

from enum import Enum


class GameStatus(str, Enum):
    """Valid game status values."""

    SCHEDULED = "SCHEDULED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class StatusTransitionError(Exception):
    """Raised when invalid status transition is attempted."""

    pass


def is_valid_transition(current_status: str, new_status: str) -> bool:
    """
    Check if status transition is valid.

    Valid transitions:
    - SCHEDULED -> IN_PROGRESS (game starts)
    - SCHEDULED -> CANCELLED (game cancelled before start)
    - IN_PROGRESS -> COMPLETED (game ends)
    - IN_PROGRESS -> CANCELLED (game cancelled during play)

    Args:
        current_status: Current game status
        new_status: Proposed new status

    Returns:
        True if transition is valid
    """
    valid_transitions = {
        GameStatus.SCHEDULED: [GameStatus.IN_PROGRESS, GameStatus.CANCELLED],
        GameStatus.IN_PROGRESS: [GameStatus.COMPLETED, GameStatus.CANCELLED],
        GameStatus.COMPLETED: [],
        GameStatus.CANCELLED: [],
    }

    try:
        current = GameStatus(current_status)
        new = GameStatus(new_status)
        return new in valid_transitions[current]
    except (ValueError, KeyError):
        return False


def get_next_status(current_status: str) -> str | None:
    """
    Get next automatic status in game lifecycle.

    Args:
        current_status: Current game status

    Returns:
        Next status or None if no automatic transition
    """
    if current_status == GameStatus.SCHEDULED:
        return GameStatus.IN_PROGRESS
    elif current_status == GameStatus.IN_PROGRESS:
        return GameStatus.COMPLETED
    return None
