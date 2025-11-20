"""Utilities for interaction handling."""

import discord


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
    """Send error message as followup to interaction.

    Args:
        interaction: Discord interaction object
        message: Error message to display to user
    """
    try:
        if interaction.response.is_done():
            await interaction.followup.send(content=f"❌ {message}", ephemeral=True)
        else:
            await interaction.response.send_message(content=f"❌ {message}", ephemeral=True)
    except discord.HTTPException:
        pass


async def send_success_message(interaction: discord.Interaction, message: str) -> None:
    """Send success message as followup to interaction.

    Args:
        interaction: Discord interaction object
        message: Success message to display to user
    """
    try:
        if interaction.response.is_done():
            await interaction.followup.send(content=f"✅ {message}", ephemeral=True)
        else:
            await interaction.response.send_message(content=f"✅ {message}", ephemeral=True)
    except discord.HTTPException:
        pass
