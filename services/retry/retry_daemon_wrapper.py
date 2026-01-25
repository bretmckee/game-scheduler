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


"""
Retry daemon wrapper for DLQ processing.

Entry point for containerized deployment of retry service.
"""

import logging
import os
import signal

from shared.telemetry import flush_telemetry, init_telemetry

from .retry_daemon import RetryDaemon

logger = logging.getLogger(__name__)

# Global flag for graceful shutdown
shutdown_requested = False


def signal_handler(signum: int, frame) -> None:
    """Handle shutdown signals gracefully."""
    global shutdown_requested  # noqa: PLW0603 - Required for signal handler communication
    logger.info(f"Received signal {signum}, initiating graceful shutdown")
    shutdown_requested = True


def main() -> None:
    """Entry point for retry daemon."""
    log_level = os.getenv("LOG_LEVEL", "INFO")
    logging.basicConfig(
        level=getattr(logging, log_level),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    init_telemetry("retry-daemon")

    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    rabbitmq_url = os.getenv("RABBITMQ_URL", "amqp://guest:guest@rabbitmq:5672/")
    retry_interval = int(os.getenv("RETRY_INTERVAL_SECONDS", "900"))

    try:
        daemon = RetryDaemon(
            rabbitmq_url=rabbitmq_url,
            retry_interval_seconds=retry_interval,
        )

        daemon.run(lambda: shutdown_requested)
    finally:
        flush_telemetry()


if __name__ == "__main__":
    main()
