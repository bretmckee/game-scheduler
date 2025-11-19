# Copyright 2025 Bret McKee (bret.mckee@gmail.com)
#
# This file is part of Game_Scheduler. (https://github.com/game-scheduler)
#
# Game_Scheduler is free software: you can redistribute it and/or
# modify it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or (at your
# option) any later version.
#
# Game_Scheduler is distributed in the hope that it will be
# useful, but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Affero General
# Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License along
# with Game_Scheduler If not, see <https://www.gnu.org/licenses/>.


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
