# Copyright 2026 Bret McKee
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


"""Emoji resolver service for resolving custom emoji mentions in game text fields."""

import logging
import re

from shared.discord.client import DiscordAPIClient, DiscordAPIError

logger = logging.getLogger(__name__)

_EMOJI_PATTERN = re.compile(r":(\w+):")
_STORED_EMOJI_PATTERN = re.compile(r"<a?:(\w+):\d+>")


def render_emoji_for_display(text: str | None) -> str | None:
    """Convert stored <:name:id> and <a:name:id> tokens back to :name: for display."""
    if text is None:
        return None
    return _STORED_EMOJI_PATTERN.sub(r":\1:", text)


class EmojiResolver:
    """Resolves :emoji_name: patterns to Discord custom emoji format."""

    def __init__(self, discord_client: DiscordAPIClient) -> None:
        self._discord_client = discord_client

    async def resolve_emoji_mentions(self, text: str, guild_id: str) -> tuple[str, list[dict]]:
        """
        Resolve :emoji_name: patterns in text to Discord custom emoji format.

        Unknown emoji names pass through unchanged. If the emoji cache is cold
        (503), the original text is returned without error.
        """
        if ":" not in text:
            return text, []

        try:
            emoji_list = await self._discord_client.get_guild_emojis(guild_id)
        except DiscordAPIError as exc:
            logger.warning("Emoji cache unavailable for guild %s: %s", guild_id, exc)
            return text, []

        emoji_by_name = {e["name"]: e for e in emoji_list}

        def _replace(match: re.Match) -> str:
            name = match.group(1)
            emoji = emoji_by_name.get(name)
            if emoji is None:
                return match.group(0)
            prefix = "a" if emoji["animated"] else ""
            return f"<{prefix}:{name}:{emoji['id']}>"

        return _EMOJI_PATTERN.sub(_replace, text), []
