"""Discord bot entry point."""

import asyncio
import logging
import sys

from services.bot.bot import create_bot
from services.bot.config import get_config


def setup_logging(log_level: str) -> None:
    """
    Configure logging for the bot application.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    logging.getLogger("discord").setLevel(logging.WARNING)
    logging.getLogger("discord.http").setLevel(logging.WARNING)


async def main() -> None:
    """Main bot application entry point."""
    config = get_config()

    setup_logging(config.log_level)
    logger = logging.getLogger(__name__)

    logger.info("Starting Discord Game Scheduler Bot")
    logger.info(f"Environment: {config.environment}")

    try:
        bot = await create_bot(config)

        async with bot:
            await bot.start(config.discord_bot_token)

    except KeyboardInterrupt:
        logger.info("Received interrupt signal, shutting down")
    except Exception as e:
        logger.exception(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
