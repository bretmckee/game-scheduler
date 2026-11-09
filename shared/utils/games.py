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


"""Game-related utilities and constants."""

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from shared.models.game import GameSession

logger = logging.getLogger(__name__)

DEFAULT_MAX_PLAYERS = 10
"""Default maximum number of players when max_players is not specified."""


def resolve_max_players(max_players_value: int | None) -> int:
    """
    Resolve max_players value, defaulting to DEFAULT_MAX_PLAYERS if None.

    This utility function provides a single place to handle the common pattern
    of: max_players = value or DEFAULT_MAX_PLAYERS

    Args:
        max_players_value: The max_players value to resolve (may be None)

    Returns:
        The max_players value if provided, otherwise DEFAULT_MAX_PLAYERS

    Example:
        >>> resolve_max_players(5)
        5
        >>> resolve_max_players(None)
        10
    """
    return max_players_value or DEFAULT_MAX_PLAYERS


def build_jump_url(game: "GameSession") -> str | None:
    """
    Build the Discord jump URL to a game's announcement message.

    Args:
        game: Game session with guild and channel relationships loaded

    Returns:
        Jump URL, or None when the game has no announcement message yet
    """
    if game.message_id and game.guild and game.channel:
        return (
            f"https://discord.com/channels/"
            f"{game.guild.guild_id}/{game.channel.channel_id}/{game.message_id}"
        )
    logger.warning("Cannot build jump URL for game %s", game.id)
    return None
