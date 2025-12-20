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
Unit tests for API service Discord client integration.

Note: Core DiscordAPIClient functionality is comprehensively tested in
tests/shared/discord/test_client.py. This file focuses on API-specific
integration, particularly the singleton pattern.
"""

from unittest.mock import MagicMock, patch

from services.api.dependencies.discord import get_discord_client


def test_get_discord_client_singleton():
    """Test Discord client singleton pattern for API service."""
    with patch("services.api.dependencies.discord.config.get_api_config") as mock_config:
        mock_config.return_value = MagicMock(
            discord_client_id="test_id",
            discord_client_secret="test_secret",
            discord_bot_token="test_token",
        )

        client1 = get_discord_client()
        client2 = get_discord_client()

        assert client1 is client2
