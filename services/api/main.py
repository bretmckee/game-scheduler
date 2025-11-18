"""
Main entry point for the API service.

Starts the FastAPI application with Uvicorn server.
"""

import logging
import sys

import uvicorn

from services.api.app import create_app
from services.api.config import get_api_config

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


async def main() -> None:
    """Start the FastAPI application with Uvicorn."""
    config = get_api_config()
    setup_logging(config.log_level)

    logger = logging.getLogger(__name__)
    logger.info("Starting Discord Game Scheduler API service")

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


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
