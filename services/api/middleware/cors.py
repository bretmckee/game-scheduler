"""
CORS middleware configuration for the API service.

Configures Cross-Origin Resource Sharing to allow frontend access.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from services.api.config import APIConfig


def configure_cors(app: FastAPI, config: APIConfig) -> None:
    """
    Configure CORS middleware for the FastAPI application.

    Args:
        app: FastAPI application instance
        config: API configuration with frontend URL
    """
    origins = [
        config.frontend_url,
        "http://localhost:3000",
        "http://localhost:3001",
    ]

    if config.debug:
        origins.append("*")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["*"],
    )
