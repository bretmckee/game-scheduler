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
        origins.extend([
            "http://localhost:5173",  # Vite default dev port
            "http://127.0.0.1:3000",
            "http://127.0.0.1:8000",
        ])

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["*"],
    )
