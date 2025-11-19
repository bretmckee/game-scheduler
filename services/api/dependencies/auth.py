"""Authentication dependencies for FastAPI routes.

Provides dependency injection for current user retrieval.
"""

import logging

from fastapi import Cookie, HTTPException

from services.api.auth import tokens
from shared.schemas import auth as auth_schemas

logger = logging.getLogger(__name__)


async def get_current_user(
    session_token: str = Cookie(..., description="Session token from HTTPOnly cookie"),
) -> auth_schemas.CurrentUser:
    """
    Get current authenticated user from cookie.

    Args:
        session_token: Session token from cookie

    Returns:
        Current user information

    Raises:
        HTTPException: If user is not authenticated
    """
    if not session_token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    token_data = await tokens.get_user_tokens(session_token)
    if not token_data:
        raise HTTPException(status_code=401, detail="Session not found")

    if await tokens.is_token_expired(token_data["expires_at"]):
        raise HTTPException(status_code=401, detail="Token expired")

    return auth_schemas.CurrentUser(
        discord_id=token_data["user_id"],
        access_token=token_data["access_token"],
        session_token=session_token,
    )
