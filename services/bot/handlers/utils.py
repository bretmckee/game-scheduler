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
