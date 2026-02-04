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


"""List games slash command implementation."""

import logging
from typing import TYPE_CHECKING

import discord
from discord import Interaction, app_commands
from opentelemetry import trace
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database import get_db_session
from shared.discord.game_embeds import build_game_list_embed
from shared.models import ChannelConfiguration, GameSession, GuildConfiguration

if TYPE_CHECKING:
    from services.bot.bot import GameSchedulerBot

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)


def _determine_fetch_strategy(
    interaction: Interaction,
    channel: discord.TextChannel | None,
    show_all: bool,
) -> tuple[str, str, discord.TextChannel | None] | None:
    """
    Determine which games to fetch based on command parameters.

    Args:
        interaction: Discord interaction object
        channel: Specific channel to list games from (optional)
        show_all: Whether to show games from all channels in guild

    Returns:
        Tuple of (strategy, title, channel) or None if invalid
        Strategy can be: "guild", "specific_channel", "current_channel"
    """
    if not interaction.guild:
        return None

    if show_all:
        return (
            "guild",
            f"📅 All Scheduled Games in {interaction.guild.name}",
            None,
        )

    if channel:
        return (
            "specific_channel",
            f"📅 Scheduled Games in #{channel.name}",
            channel,
        )

    if not interaction.channel or not isinstance(interaction.channel, discord.TextChannel):
        return None

    return (
        "current_channel",
        f"📅 Scheduled Games in #{interaction.channel.name}",
        interaction.channel,
    )


async def _fetch_games_by_strategy(
    db: AsyncSession,
    strategy: str,
    guild_id: str,
    channel: discord.TextChannel | None,
) -> list[GameSession]:
    """
    Fetch games based on determined strategy.

    Args:
        db: Database session
        strategy: Fetch strategy ("guild", "specific_channel", "current_channel")
        guild_id: Discord guild ID
        channel: Channel to fetch from (if strategy requires it)

    Returns:
        List of game sessions
    """
    if strategy == "guild":
        return await _get_all_guild_games(db, guild_id)

    if strategy in ("specific_channel", "current_channel") and channel:
        return await _get_channel_games(db, str(channel.id))

    return []


async def list_games_command(
    interaction: Interaction,
    channel: discord.TextChannel | None = None,
    show_all: bool = False,
) -> None:
    """
    List scheduled games in the current channel or all channels.

    Args:
        interaction: Discord interaction object
        channel: Specific channel to list games from (optional)
        show_all: Whether to show games from all channels in guild
    """
    with tracer.start_as_current_span(
        "discord.command.list_games",
        attributes={
            "discord.command": "list-games",
            "discord.user_id": str(interaction.user.id),
            "discord.guild_id": (str(interaction.guild.id) if interaction.guild else None),
            "discord.channel_id": (str(interaction.channel_id) if interaction.channel_id else None),
            "command.show_all": show_all,
            "command.channel": str(channel.id) if channel else None,
        },
    ):
        await interaction.response.defer(ephemeral=True)

        try:
            strategy_result = _determine_fetch_strategy(interaction, channel, show_all)
            if not strategy_result:
                error_msg = (
                    "❌ This command can only be used in a server."
                    if not interaction.guild
                    else "❌ Could not determine the current channel."
                )
                await interaction.followup.send(error_msg, ephemeral=True)
                return

            strategy, title, target_channel = strategy_result

            async with get_db_session() as db:
                games = await _fetch_games_by_strategy(
                    db, strategy, str(interaction.guild.id), target_channel
                )

                if not games:
                    await interaction.followup.send(
                        "No scheduled games found.",
                        ephemeral=True,
                    )
                    return

                embed = build_game_list_embed(games, title)
                await interaction.followup.send(embed=embed, ephemeral=True)

        except Exception as e:
            logger.exception("Error listing games")
            await interaction.followup.send(
                f"❌ An error occurred: {e!s}",
                ephemeral=True,
            )


async def _get_channel_games(db: AsyncSession, channel_id: str) -> list[GameSession]:
    """
    Fetch scheduled games for a specific channel.

    Args:
        db: Database session
        channel_id: Discord channel ID

    Returns:
        List of game sessions
    """
    result = await db.execute(
        select(GameSession)
        .join(ChannelConfiguration)
        .where(ChannelConfiguration.channel_id == channel_id)
        .where(GameSession.status == "SCHEDULED")
        .order_by(GameSession.scheduled_at)
    )
    return list(result.scalars().all())


async def _get_all_guild_games(db: AsyncSession, guild_id: str) -> list[GameSession]:
    """
    Fetch all scheduled games for a guild.

    Args:
        db: Database session
        guild_id: Discord guild ID

    Returns:
        List of game sessions
    """
    result = await db.execute(
        select(GameSession)
        .join(GuildConfiguration)
        .where(GuildConfiguration.guild_id == guild_id)
        .where(GameSession.status == "SCHEDULED")
        .order_by(GameSession.scheduled_at)
    )
    return list(result.scalars().all())


async def setup(bot: "GameSchedulerBot") -> None:
    """
    Register list_games command with the bot.

    Args:
        bot: Bot instance to register command with
    """

    @bot.tree.command(name="list-games", description="List scheduled games")
    @app_commands.describe(
        channel="Specific channel to list games from (optional)",
        show_all="Show games from all channels in this server",
    )
    async def list_games_slash(
        interaction: Interaction,
        channel: discord.TextChannel | None = None,
        show_all: bool = False,
    ) -> None:
        await list_games_command(interaction, channel, show_all)

    logger.info("Registered /list-games command")


__all__ = ["list_games_command", "setup"]
