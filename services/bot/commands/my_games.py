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


"""My games slash command implementation."""

import logging
from typing import TYPE_CHECKING

import discord
from discord import Interaction
from opentelemetry import trace
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database import get_db_session
from shared.discord.game_embeds import build_game_list_embed
from shared.models import GameParticipant, GameSession, User

if TYPE_CHECKING:
    from services.bot.bot import GameSchedulerBot

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)


async def my_games_command(interaction: Interaction) -> None:
    """
    List games that the user is hosting or participating in.

    Args:
        interaction: Discord interaction object
    """
    with tracer.start_as_current_span(
        "discord.command.my_games",
        attributes={
            "discord.command": "my-games",
            "discord.user_id": str(interaction.user.id),
            "discord.guild_id": (str(interaction.guild.id) if interaction.guild else None),
            "discord.channel_id": (str(interaction.channel_id) if interaction.channel_id else None),
        },
    ):
        await interaction.response.defer(ephemeral=True)

        try:
            async with get_db_session() as db:
                user = await _get_or_create_user(db, str(interaction.user.id))

                hosted_games = await _get_hosted_games(db, str(user.id))
                participating_games = await _get_participating_games(db, str(user.id))

                if not hosted_games and not participating_games:
                    await interaction.followup.send(
                        "You are not hosting or participating in any scheduled games.",
                        ephemeral=True,
                    )
                    return

                embeds = []

                if hosted_games:
                    embed = build_game_list_embed(
                        hosted_games,
                        "🎮 Games You're Hosting",
                        discord.Color.green(),
                    )
                    embeds.append(embed)

                if participating_games:
                    embed = build_game_list_embed(
                        participating_games,
                        "👥 Games You've Joined",
                        discord.Color.blue(),
                    )
                    embeds.append(embed)

                await interaction.followup.send(embeds=embeds, ephemeral=True)

        except Exception as e:
            logger.exception("Error fetching user's games")
            await interaction.followup.send(
                f"❌ An error occurred: {e!s}",
                ephemeral=True,
            )


async def _get_or_create_user(db: AsyncSession, discord_id: str) -> User:
    """
    Get existing user or create new user record.

    Args:
        db: Database session
        discord_id: Discord user ID

    Returns:
        User record
    """
    result = await db.execute(select(User).where(User.discord_id == discord_id))
    user = result.scalar_one_or_none()

    if not user:
        user = User(discord_id=discord_id)
        db.add(user)
        await db.commit()
        await db.refresh(user)

    return user


async def _get_hosted_games(db: AsyncSession, user_id: str) -> list[GameSession]:
    """
    Fetch games hosted by user.

    Args:
        db: Database session
        user_id: Internal user ID

    Returns:
        List of game sessions
    """
    result = await db.execute(
        select(GameSession)
        .where(GameSession.host_id == user_id)
        .where(GameSession.status == "SCHEDULED")
        .order_by(GameSession.scheduled_at)
    )
    return list(result.scalars().all())


async def _get_participating_games(db: AsyncSession, user_id: str) -> list[GameSession]:
    """
    Fetch games user is participating in (excluding hosted games).

    Args:
        db: Database session
        user_id: Internal user ID

    Returns:
        List of game sessions
    """
    result = await db.execute(
        select(GameSession)
        .join(GameParticipant)
        .where(GameParticipant.user_id == user_id)
        .where(GameSession.host_id != user_id)
        .where(GameSession.status == "SCHEDULED")
        .order_by(GameSession.scheduled_at)
    )
    return list(result.scalars().all())


async def setup(bot: "GameSchedulerBot") -> None:
    """
    Register my_games command with the bot.

    Args:
        bot: Bot instance to register command with
    """

    @bot.tree.command(name="my-games", description="Show your hosted and joined games")
    async def my_games_slash(interaction: Interaction) -> None:
        await my_games_command(interaction)

    logger.info("Registered /my-games command")


__all__ = ["my_games_command", "setup"]
