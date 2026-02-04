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


"""
Main entry point for the API service.

Starts the FastAPI application with Uvicorn server.
"""

import logging
import sys

import uvicorn

from services.api.app import create_app
from services.api.config import get_api_config
from shared.telemetry import flush_telemetry, init_telemetry

app = create_app()


def setup_logging(log_level: str) -> None:
    """
    Configure logging for the application.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("fastapi").setLevel(logging.INFO)
    logging.getLogger("services.api").setLevel(logging.INFO)


async def main() -> None:
    """Start the FastAPI application with Uvicorn."""
    config = get_api_config()
    setup_logging(config.log_level)

    logger = logging.getLogger(__name__)
    logger.info("Starting Discord Game Scheduler API service")

    init_telemetry("api-service")

    try:
        app = create_app()

        uvicorn_config = uvicorn.Config(
            app,
            host=config.api_host,
            port=config.api_port,
            log_level=config.log_level.lower(),
            access_log=config.debug,
        )

        server = uvicorn.Server(uvicorn_config)
        await server.serve()
    finally:
        flush_telemetry()


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
