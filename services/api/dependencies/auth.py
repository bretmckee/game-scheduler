"""
Authentication dependencies for FastAPI routes.

Provides dependency injection for current user retrieval.
"""

import logging

from fastapi import Header, HTTPException

from services.api.auth import tokens
from shared.schemas import auth as auth_schemas

logger = logging.getLogger(__name__)


async def get_current_user(
    x_user_id: str = Header(..., description="Discord user ID from session"),
) -> auth_schemas.CurrentUser:
    """
    Get current authenticated user from header.

    Args:
        x_user_id: Discord user ID from X-User-Id header

    Returns:
        Current user information

    Raises:
        HTTPException: If user is not authenticated
    """
    if not x_user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    token_data = await tokens.get_user_tokens(x_user_id)
    if not token_data:
        raise HTTPException(status_code=401, detail="Session not found")

    if await tokens.is_token_expired(token_data["expires_at"]):
        raise HTTPException(status_code=401, detail="Token expired")

    return auth_schemas.CurrentUser(discord_id=x_user_id)
