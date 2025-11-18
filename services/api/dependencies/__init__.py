"""
Dependencies module initialization.

Exports authentication and other FastAPI dependencies.
"""

from services.api.dependencies import auth, permissions

__all__ = ["auth", "permissions"]
