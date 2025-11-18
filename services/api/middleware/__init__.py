"""
Middleware components for the API service.

Includes CORS configuration, error handling, logging, and authentication.
"""

from services.api.middleware import cors, error_handler

__all__ = ["cors", "error_handler"]
