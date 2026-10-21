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
Global error handling middleware for the API service.

Catches and formats exceptions into consistent JSON responses.
"""

import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING, cast

from fastapi import FastAPI, Request, Response, status
from fastapi.exception_handlers import http_exception_handler as default_http_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError
from starlette.exceptions import HTTPException as StarletteHTTPException

from services.api.config import get_api_config

if TYPE_CHECKING:
    from starlette.types import HTTPExceptionHandler

logger = logging.getLogger(__name__)


def _summarize_http_detail(detail: object) -> str:
    """
    Reduce an HTTPException detail to a log-safe summary.

    Structured details (e.g. invalid_mentions) echo the submitted form back to the
    client; only the error code and message are logged so user-authored text never
    reaches the logs.
    """
    if isinstance(detail, dict):
        return f"{detail.get('error')}: {detail.get('message')}"
    return str(detail)


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> Response:
    """
    Log HTTPException responses, then return FastAPI's standard response.

    Without this, 4xx/5xx responses raised deliberately by routes leave no trace in
    the logs, making user-reported failures impossible to diagnose.

    Args:
        request: HTTP request that caused the error
        exc: HTTP exception raised by a route, dependency, or the router (e.g. 404)

    Returns:
        FastAPI's default response for the exception (status, body and headers unchanged)
    """
    log = (
        logger.error if exc.status_code >= status.HTTP_500_INTERNAL_SERVER_ERROR else logger.warning
    )
    log(
        "HTTP %s on %s %s: %s",
        exc.status_code,
        request.method,
        request.url.path,
        _summarize_http_detail(exc.detail),
    )
    return await default_http_exception_handler(request, exc)


async def validation_exception_handler(
    request: Request, exc: RequestValidationError | ValidationError
) -> JSONResponse:
    """
    Handle Pydantic validation errors with detailed error messages.

    Args:
        request: HTTP request that caused the error
        exc: Validation error with field-level details

    Returns:
        JSON response with 422 status and error details
    """
    errors = [
        {
            "field": ".".join(str(loc) for loc in error["loc"]),
            "message": error["msg"],
            "type": error["type"],
        }
        for error in exc.errors()
    ]

    logger.warning(
        "Request validation failed on %s %s: %s",
        request.method,
        request.url.path,
        "; ".join(f"{e['field']} ({e['type']})" for e in errors),
    )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "validation_error",
            "message": "Invalid request data",
            "details": errors,
        },
    )


async def database_exception_handler(_request: Request, exc: SQLAlchemyError) -> JSONResponse:
    """
    Handle database errors with appropriate error messages.

    Args:
        request: HTTP request that caused the error
        exc: SQLAlchemy database error

    Returns:
        JSON response with 500 status and error message
    """
    error_time = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")
    logger.error("Database error at %s: %s", error_time, exc)

    config = get_api_config()

    user_message = (
        "An internal error has occurred. "
        f"Please create an issue which includes the time: {error_time} UTC"
    )

    # In debug mode, append development details to help developers see both messages
    message = f"{user_message} -- development mode details: {exc}" if config.debug else user_message

    content = {
        "error": "database_error",
        "message": message,
    }

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=content,
    )


async def general_exception_handler(_request: Request, exc: Exception) -> JSONResponse:
    """
    Handle unexpected exceptions with generic error message.

    Args:
        _request: HTTP request that caused the error (unused, required by FastAPI)
        exc: Unhandled exception

    Returns:
        JSON response with 500 status and error message
    """
    logger.error("Unhandled exception: %s", exc)

    config = get_api_config()

    user_message = "An unexpected error occurred"

    # In debug mode, append development details to help developers
    message = f"{user_message} -- development mode details: {exc}" if config.debug else user_message

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "internal_error",
            "message": message,
        },
    )


def configure_error_handlers(app: FastAPI) -> None:
    """
    Configure global exception handlers for the FastAPI application.

    Args:
        app: FastAPI application instance
    """
    app.add_exception_handler(
        StarletteHTTPException, cast("HTTPExceptionHandler", http_exception_handler)
    )
    app.add_exception_handler(RequestValidationError, validation_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(ValidationError, validation_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(SQLAlchemyError, database_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(Exception, general_exception_handler)
