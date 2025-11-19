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

    # Note: Cannot use "*" wildcard when allow_credentials=True
    # In debug mode, be more permissive but still specific
    if config.debug:
        origins.extend(
            [
                "http://localhost:5173",  # Vite default dev port
                "http://127.0.0.1:3000",
                "http://127.0.0.1:8000",
            ]
        )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["*"],
    )
