"""Button interaction dispatcher for Discord bot."""

import logging

import discord

from services.bot.events.publisher import BotEventPublisher
from services.bot.handlers.join_game import handle_join_game
from services.bot.handlers.leave_game import handle_leave_game

logger = logging.getLogger(__name__)


class ButtonHandler:
    """Handles button interaction routing."""

    def __init__(self, publisher: BotEventPublisher):
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

        custom_id = interaction.data["custom_id"]

        if not custom_id.startswith(("join_game_", "leave_game_")):
            logger.debug(f"Ignoring non-game button: {custom_id}")
            return

        try:
            if custom_id.startswith("join_game_"):
                game_id = custom_id.replace("join_game_", "")
                await handle_join_game(interaction, game_id, self.publisher)
            elif custom_id.startswith("leave_game_"):
                game_id = custom_id.replace("leave_game_", "")
                await handle_leave_game(interaction, game_id, self.publisher)
            else:
                logger.warning(f"Unknown button action: {custom_id}")

        except Exception as e:
            logger.error(f"Error handling button interaction {custom_id}: {e}", exc_info=True)
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    "❌ An error occurred. Please try again.", ephemeral=True
                )
