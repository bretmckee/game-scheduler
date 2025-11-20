"""Utilities for interaction handling."""

import logging

import discord

logger = logging.getLogger(__name__)


async def send_deferred_response(interaction: discord.Interaction) -> None:
    """Send deferred response to Discord within 3-second timeout.

    Args:
        interaction: Discord interaction object
    """
    if not interaction.response.is_done():
        try:
            await interaction.response.defer(ephemeral=True)
        except discord.HTTPException:
            pass


async def send_error_message(interaction: discord.Interaction, message: str) -> None:
    """Send error message as DM to user.

    Args:
        interaction: Discord interaction object
        message: Error message to display to user
    """
    try:
        await interaction.user.send(content=f"❌ {message}")
    except (discord.Forbidden, discord.HTTPException) as e:
        logger.warning(f"Cannot send DM to user {interaction.user.id}: {e}")


async def send_success_message(interaction: discord.Interaction, message: str) -> None:
    """Send success message as DM to user.

    Args:
        interaction: Discord interaction object
        message: Success message to display to user
    """
    try:
        await interaction.user.send(content=message)
    except (discord.Forbidden, discord.HTTPException) as e:
        logger.warning(f"Cannot send DM to user {interaction.user.id}: {e}")
