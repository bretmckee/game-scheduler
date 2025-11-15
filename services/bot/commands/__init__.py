"""Discord slash commands for game scheduling bot."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from services.bot.bot import GameSchedulerBot


async def setup_commands(bot: "GameSchedulerBot") -> None:
    """
    Register all slash commands with the bot.

    Args:
        bot: Bot instance to register commands with
    """
    from services.bot.commands import (
        config_channel,
        config_guild,
        list_games,
        my_games,
    )

    await list_games.setup(bot)
    await my_games.setup(bot)
    await config_guild.setup(bot)
    await config_channel.setup(bot)


__all__ = ["setup_commands"]
