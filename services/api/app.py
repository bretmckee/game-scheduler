"""
FastAPI application factory.

Creates and configures the FastAPI application with middleware,
error handlers, and route registration.
"""

import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI

from services.api import middleware
from services.api.config import get_api_config
from services.api.routes import auth, channels, games, guilds
from shared.cache import client as redis_client

# Configure logging at module level before anything else
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
    force=True,  # Override any existing configuration
)

# Set log levels for various loggers
logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
logging.getLogger("uvicorn.error").setLevel(logging.INFO)
logging.getLogger("services.api").setLevel(logging.INFO)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan context manager.

    Initializes connections on startup and closes them on shutdown.

    Args:
        app: FastAPI application instance
    """
    logger.info("Starting API service...")

    redis_instance = await redis_client.get_redis_client()
    logger.info("Redis connection initialized")

    yield

    logger.info("Shutting down API service...")

    await redis_instance.disconnect()
    logger.info("Redis connection closed")


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.

    Returns:
        Configured FastAPI application instance
    """
    config = get_api_config()

    app = FastAPI(
        title="Discord Game Scheduler API",
        description="REST API for Discord game scheduling web dashboard",
        version="1.0.0",
        docs_url="/docs" if config.debug else None,
        redoc_url="/redoc" if config.debug else None,
        lifespan=lifespan,
    )

    middleware.cors.configure_cors(app, config)
    middleware.error_handler.configure_error_handlers(app)

    app.include_router(auth.router)
    app.include_router(guilds.router)
    app.include_router(channels.router)
    app.include_router(games.router)

    @app.get("/health")
    async def health_check():
        """Health check endpoint for monitoring."""
        return {"status": "healthy", "service": "api"}

    logger.info(f"FastAPI application created (environment: {config.environment})")

    return app
