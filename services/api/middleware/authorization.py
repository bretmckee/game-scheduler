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
Authorization middleware for API requests.

Provides request logging and authorization context management.
Note: Actual authorization checks are performed via FastAPI dependencies.
"""

import logging
import time
from collections.abc import Awaitable, Callable

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

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
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
            logger.exception(
                "Request %s failed after %.3fs: %s",
                request_id,
                duration,
                e,
            )
            raise
