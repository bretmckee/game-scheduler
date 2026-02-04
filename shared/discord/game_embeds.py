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


"""Shared Discord embed building utilities for game displays."""

from datetime import UTC, datetime

import discord

from shared.utils.limits import DEFAULT_PAGE_SIZE


def build_game_list_embed(
    games: list,
    title: str,
    color: discord.Color | None = None,
) -> discord.Embed:
    """
    Build Discord embed for game list display.

    Args:
        games: List of games to display
        title: Embed title
        color: Embed color (default: blue)

    Returns:
        Formatted Discord embed with game list
    """
    if color is None:
        color = discord.Color.blue()

    embed = discord.Embed(
        title=title,
        color=color,
        timestamp=datetime.now(UTC),
    )

    for game in games[:DEFAULT_PAGE_SIZE]:
        unix_timestamp = int(game.scheduled_at.timestamp())
        value = f"🕒 <t:{unix_timestamp}:F> (<t:{unix_timestamp}:R>)\n"
        if game.description:
            value += f"{game.description[:100]}\n"
        value += f"ID: `{game.id}`"

        embed.add_field(
            name=game.title,
            value=value,
            inline=False,
        )

    if len(games) > DEFAULT_PAGE_SIZE:
        embed.set_footer(text=f"Showing {DEFAULT_PAGE_SIZE} of {len(games)} games")
    else:
        embed.set_footer(text=f"{len(games)} game(s) found")

    return embed


__all__ = ["build_game_list_embed"]
