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


"""
Authorization middleware for API requests.

Provides request logging and authorization context management.
Note: Actual authorization checks are performed via FastAPI dependencies.
"""

import logging
import time

from fastapi import Request, Response
from starlette import status
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class AuthorizationMiddleware(BaseHTTPMiddleware):
    """
    Middleware for authorization context and logging.

    Logs authorization events and provides request context for authorization.
    Actual permission checks are performed via FastAPI dependencies.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        """
        Process request with authorization logging.

        Args:
            request: Incoming HTTP request
            call_next: Next middleware or route handler

        Returns:
            HTTP response
        """
        start_time = time.time()

        user_id = request.headers.get("X-User-Id")
        request_id = request.headers.get("X-Request-Id", "unknown")

        if user_id:
            logger.debug(
                "Request %s: %s %s from user %s",
                request_id,
                request.method,
                request.url.path,
                user_id,
            )

        try:
            response = await call_next(request)

            duration = time.time() - start_time

            if response.status_code == status.HTTP_403_FORBIDDEN:
                logger.warning(
                    "Authorization denied: %s %s for user %s (request_id=%s)",
                    request.method,
                    request.url.path,
                    user_id or "anonymous",
                    request_id,
                )
            elif response.status_code == status.HTTP_401_UNAUTHORIZED:
                logger.info(
                    "Authentication required: %s %s (request_id=%s)",
                    request.method,
                    request.url.path,
                    request_id,
                )

            logger.debug(
                "Request %s completed in %.3fs with status %s",
                request_id,
                duration,
                response.status_code,
            )

            return response

        except Exception as e:
            duration = time.time() - start_time
            logger.error(
                "Request %s failed after %.3fs: %s",
                request_id,
                duration,
                e,
                exc_info=True,
            )
            raise
