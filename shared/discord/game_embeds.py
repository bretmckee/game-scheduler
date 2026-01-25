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
