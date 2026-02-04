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


"""Discord bot entry point."""

import asyncio
import contextlib
import logging
import sys

from services.bot.bot import create_bot
from services.bot.config import get_config
from shared.telemetry import flush_telemetry, init_telemetry


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

    # Initialize OpenTelemetry
    init_telemetry("bot-service")

    try:
        # Check if running in test environment without Discord credentials
        if not config.discord_bot_token or not config.discord_bot_client_id:
            logger.warning(
                "Discord credentials not configured. Bot will not start (integration test mode)."
            )
            return

        logger.info("Starting Discord Game Scheduler Bot")
        logger.info("Environment: %s", config.environment)

        try:
            bot = await create_bot(config)

            async with bot:
                await bot.start(config.discord_bot_token)

        except KeyboardInterrupt:
            logger.info("Received interrupt signal, shutting down")
        except Exception as e:
            logger.exception("Fatal error: %s", e)
            sys.exit(1)
    finally:
        flush_telemetry()


if __name__ == "__main__":
    with contextlib.suppress(KeyboardInterrupt):
        asyncio.run(main())
