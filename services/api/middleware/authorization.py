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
                f"Request {request_id}: {request.method} {request.url.path} from user {user_id}"
            )

        try:
            response = await call_next(request)

            duration = time.time() - start_time

            if response.status_code == status.HTTP_403_FORBIDDEN:
                logger.warning(
                    f"Authorization denied: {request.method} {request.url.path} "
                    f"for user {user_id or 'anonymous'} (request_id={request_id})"
                )
            elif response.status_code == status.HTTP_401_UNAUTHORIZED:
                logger.info(
                    f"Authentication required: {request.method} {request.url.path} "
                    f"(request_id={request_id})"
                )

            logger.debug(
                f"Request {request_id} completed in {duration:.3f}s "
                f"with status {response.status_code}"
            )

            return response

        except Exception as e:
            duration = time.time() - start_time
            logger.error(
                f"Request {request_id} failed after {duration:.3f}s: {e}",
                exc_info=True,
            )
            raise
