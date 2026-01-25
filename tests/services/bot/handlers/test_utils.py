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


"""Unit tests for bot handler utilities."""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from services.bot.handlers.utils import get_participant_count
from shared.models.participant import GameParticipant


class TestGetParticipantCount:
    """Tests for get_participant_count function."""

    @pytest.mark.asyncio
    async def test_counts_non_placeholder_participants(self):
        """Test that function counts only participants with user IDs."""
        game_id = str(uuid4())
        user_id1 = str(uuid4())
        user_id2 = str(uuid4())

        # Mock database session
        mock_db = AsyncMock()
        mock_result = MagicMock()

        # Mock participants: 2 with users, 1 placeholder
        mock_participant1 = MagicMock(spec=GameParticipant)
        mock_participant1.user_id = user_id1

        mock_participant2 = MagicMock(spec=GameParticipant)
        mock_participant2.user_id = user_id2

        mock_result.scalars.return_value.all.return_value = [
            mock_participant1,
            mock_participant2,
        ]
        mock_db.execute.return_value = mock_result

        count = await get_participant_count(mock_db, game_id)
        assert count == 2

    @pytest.mark.asyncio
    async def test_returns_zero_for_empty_game(self):
        """Test that function returns 0 for game with no participants."""
        game_id = str(uuid4())

        # Mock database session with empty result
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        count = await get_participant_count(mock_db, game_id)
        assert count == 0

    @pytest.mark.asyncio
    async def test_excludes_all_placeholders(self):
        """Test that query filters out placeholder participants correctly."""
        game_id = str(uuid4())

        # Mock database session - empty result after filtering placeholders
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        count = await get_participant_count(mock_db, game_id)
        assert count == 0

    @pytest.mark.asyncio
    async def test_counts_only_specified_game(self):
        """Test that query filters by game_id correctly."""
        game_id = str(uuid4())
        user_id1 = str(uuid4())
        user_id2 = str(uuid4())

        # Mock database session
        mock_db = AsyncMock()
        mock_result = MagicMock()

        # Mock 2 participants for the specified game
        mock_participant1 = MagicMock(spec=GameParticipant)
        mock_participant1.user_id = user_id1

        mock_participant2 = MagicMock(spec=GameParticipant)
        mock_participant2.user_id = user_id2

        mock_result.scalars.return_value.all.return_value = [
            mock_participant1,
            mock_participant2,
        ]
        mock_db.execute.return_value = mock_result

        count = await get_participant_count(mock_db, game_id)
        assert count == 2

    @pytest.mark.asyncio
    async def test_non_existent_game_returns_zero(self):
        """Test that function returns 0 for non-existent game ID."""
        non_existent_game_id = str(uuid4())

        # Mock database session with empty result
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        count = await get_participant_count(mock_db, non_existent_game_id)
        assert count == 0
