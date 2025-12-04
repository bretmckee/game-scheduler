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


"""
Database queries for game status schedule management.

Provides synchronous query functions for the status transition daemon to
retrieve and update game status schedule records.
"""

import logging

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from shared.models import GameStatusSchedule

logger = logging.getLogger(__name__)


def get_next_due_transition(db: Session) -> GameStatusSchedule | None:
    """
    Get the next status transition due to be executed.

    Queries MIN(transition_time) using optimized partial index for O(1)
    performance regardless of total scheduled transitions.

    Returns unexecuted transitions regardless of whether transition_time is
    in the past, allowing recovery from daemon downtime. The consumer decides
    whether to act on overdue transitions.

    Args:
        db: Synchronous database session

    Returns:
        GameStatusSchedule record with earliest transition_time, or None
    """
    stmt = (
        select(GameStatusSchedule)
        .where(GameStatusSchedule.executed == False)  # noqa: E712
        .order_by(GameStatusSchedule.transition_time.asc())
        .limit(1)
    )

    result = db.execute(stmt)
    transition = result.scalar_one_or_none()

    if transition:
        logger.debug(
            f"Next transition due at {transition.transition_time} "
            f"for game {transition.game_id} to {transition.target_status}"
        )

    return transition


def mark_transition_executed(db: Session, transition_id: str) -> bool:
    """
    Mark transition as executed.

    Args:
        db: Synchronous database session
        transition_id: ID of transition to mark as executed

    Returns:
        True if transition was updated, False otherwise
    """
    stmt = (
        update(GameStatusSchedule)
        .where(GameStatusSchedule.id == transition_id)
        .values(executed=True)
    )

    result = db.execute(stmt)
    db.flush()
    updated = result.rowcount > 0  # type: ignore[attr-defined]

    if updated:
        logger.debug(f"Marked transition {transition_id} as executed")
    else:
        logger.warning(f"Failed to mark transition {transition_id} as executed")

    return updated
