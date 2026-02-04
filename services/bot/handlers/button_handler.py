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


"""Button interaction dispatcher for Discord bot."""

import logging

import discord

from services.bot.events.publisher import BotEventPublisher
from services.bot.handlers.join_game import handle_join_game
from services.bot.handlers.leave_game import handle_leave_game

logger = logging.getLogger(__name__)


class ButtonHandler:
    """Handles button interaction routing."""

    def __init__(self, publisher: BotEventPublisher) -> None:
        """Initialize button handler.

        Args:
            publisher: Bot event publisher for RabbitMQ
        """
        self.publisher = publisher

    async def handle_interaction(self, interaction: discord.Interaction) -> None:
        """Route button interaction to appropriate handler.

        Args:
            interaction: Discord button interaction

        Parses custom_id to determine handler and game ID.
        Format: {action}_{game_id}
        """
        if not interaction.data or "custom_id" not in interaction.data:
            logger.warning("Interaction missing custom_id")
            return

        custom_id = str(interaction.data.get("custom_id", ""))

        if not custom_id.startswith(("join_game_", "leave_game_")):
            logger.debug("Ignoring non-game button: %s", custom_id)
            return

        try:
            if custom_id.startswith("join_game_"):
                game_id = custom_id.replace("join_game_", "")
                await handle_join_game(interaction, game_id, self.publisher)
            elif custom_id.startswith("leave_game_"):
                game_id = custom_id.replace("leave_game_", "")
                await handle_leave_game(interaction, game_id, self.publisher)
            else:
                logger.warning("Unknown button action: %s", custom_id)

        except Exception as e:
            logger.exception("Error handling button interaction %s: %s", custom_id, e)
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    "❌ An error occurred. Please try again.", ephemeral=True
                )
