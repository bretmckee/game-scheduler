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


"""Participant sorting utilities for consistent ordering across services."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from shared.models.participant import GameParticipant


def sort_participants(participants: list["GameParticipant"]) -> list["GameParticipant"]:
    """Sort participants by priority and join time.

    Priority order:
    1. Pre-populated participants (sorted by joined_at/creation time)
    2. Placeholder participants (sorted by joined_at/creation time)
    3. Regular participants (sorted by joined_at)

    Note: All participants are ultimately sorted by joined_at within their priority group.
    For pre-populated/placeholder participants, joined_at represents creation time,
    which preserves the order the host specified them.

    Args:
        participants: List of GameParticipant models to sort

    Returns:
        Sorted list of participants with priority participants first,
        sorted by joined_at within each priority level
    """
    priority_participants = sorted(
        [p for p in participants if p.is_pre_populated or p.status == "PLACEHOLDER"],
        key=lambda p: p.joined_at,
    )

    regular_participants = sorted(
        [p for p in participants if not (p.is_pre_populated or p.status == "PLACEHOLDER")],
        key=lambda p: p.joined_at,
    )

    return priority_participants + regular_participants
