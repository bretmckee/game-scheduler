# Copyright 2025-2026 Bret McKee
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.


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
