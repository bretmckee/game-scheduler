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
Event payload schemas for scheduler system.

Defines Pydantic models for event payloads published by scheduler daemons.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class GameStatusTransitionDueEvent(BaseModel):
    """
    Payload for game.status_transition_due event.

    Published by status transition daemon when a scheduled status change
    is due. The bot receives this event and updates the game status.
    """

    game_id: UUID
    target_status: str
    transition_time: datetime
