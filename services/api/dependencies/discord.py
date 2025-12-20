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
Discord API client dependency for API service.

Provides singleton instance configured with API service credentials.
"""

from services.api import config
from shared.discord.client import DiscordAPIClient

_discord_client_instance: DiscordAPIClient | None = None


def get_discord_client() -> DiscordAPIClient:
    """
    Get Discord API client singleton for API service.

    Returns:
        Configured DiscordAPIClient instance using API service credentials
    """
    global _discord_client_instance
    if _discord_client_instance is None:
        api_config = config.get_api_config()
        _discord_client_instance = DiscordAPIClient(
            client_id=api_config.discord_client_id,
            client_secret=api_config.discord_client_secret,
            bot_token=api_config.discord_bot_token,
        )
    return _discord_client_instance
