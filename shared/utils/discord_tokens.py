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


"""Discord token utilities."""

import base64

DISCORD_TOKEN_PARTS = 3
DISCORD_BOT_TOKEN_DOT_COUNT = 2


def extract_bot_discord_id(bot_token: str) -> str:
    """
    Extract Discord bot user ID from bot token.

    Discord bot tokens have format: {bot_id_base64}.{timestamp}.{hmac}
    First segment is base64-encoded bot user ID.

    Args:
        bot_token: Discord bot authentication token

    Returns:
        Discord bot user ID (snowflake)

    Raises:
        ValueError: If token format is invalid
    """
    parts = bot_token.split(".")
    if len(parts) != DISCORD_TOKEN_PARTS:
        msg = f"Invalid bot token format: expected {DISCORD_TOKEN_PARTS} parts, got {len(parts)}"
        raise ValueError(msg)

    try:
        bot_id_base64 = parts[0]
        # Add padding if needed for proper base64 decoding
        missing_padding = len(bot_id_base64) % 4
        if missing_padding:
            bot_id_base64 += "=" * (4 - missing_padding)

        bot_id_bytes = base64.b64decode(bot_id_base64)
        return bot_id_bytes.decode("utf-8")
    except Exception as e:
        msg = f"Failed to decode bot ID from token: {e}"
        raise ValueError(msg) from e
