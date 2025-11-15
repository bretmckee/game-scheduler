"""Utilities for interaction handling."""

import discord


async def send_deferred_response(interaction: discord.Interaction) -> None:
    """Send deferred response to Discord within 3-second timeout.

    Args:
        interaction: Discord interaction object
    """
    await interaction.response.defer(ephemeral=True)


async def send_error_message(interaction: discord.Interaction, message: str) -> None:
    """Send error message as followup to interaction.

    Args:
        interaction: Discord interaction object
        message: Error message to display to user
    """
    await interaction.followup.send(content=f"❌ {message}", ephemeral=True)


async def send_success_message(interaction: discord.Interaction, message: str) -> None:
    """Send success message as followup to interaction.

    Args:
        interaction: Discord interaction object
        message: Success message to display to user
    """
    await interaction.followup.send(content=f"✅ {message}", ephemeral=True)
