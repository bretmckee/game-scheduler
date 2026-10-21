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


"""Tests for error handler middleware."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError
from starlette.exceptions import HTTPException as StarletteHTTPException

from services.api.middleware import error_handler


@pytest.fixture
def mock_app():
    """Mock FastAPI application."""
    app = MagicMock(spec=FastAPI)
    app.add_exception_handler = MagicMock()
    return app


@pytest.fixture
def mock_request():
    """Mock HTTP request."""
    request = MagicMock(spec=Request)
    request.method = "POST"
    request.url.path = "/api/v1/games"
    return request


def _logged_message(log_method) -> str:
    """Render the single %-style log call on a patched logger method."""
    log_method.assert_called_once()
    template, *args = log_method.call_args.args
    return template % tuple(args)


@pytest.mark.asyncio
async def test_validation_exception_handler_returns_422(mock_request):
    """Test that validation errors return 422 status code."""
    mock_exc = MagicMock(spec=RequestValidationError)
    mock_exc.errors.return_value = [
        {
            "loc": ("body", "name"),
            "msg": "field required",
            "type": "value_error.missing",
        }
    ]

    response = await error_handler.validation_exception_handler(mock_request, mock_exc)

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_validation_exception_handler_formats_errors(mock_request):
    """Test that validation errors are formatted with field details."""
    mock_exc = MagicMock(spec=RequestValidationError)
    mock_exc.errors.return_value = [
        {"loc": ("body", "email"), "msg": "invalid email", "type": "value_error.email"}
    ]

    response = await error_handler.validation_exception_handler(mock_request, mock_exc)

    body = response.body.decode()
    assert "body.email" in body
    assert "invalid email" in body
    assert "validation_error" in body


@pytest.mark.asyncio
async def test_validation_exception_handler_includes_multiple_errors(mock_request):
    """Test that multiple validation errors are all included."""
    mock_exc = MagicMock(spec=RequestValidationError)
    mock_exc.errors.return_value = [
        {
            "loc": ("body", "name"),
            "msg": "field required",
            "type": "value_error.missing",
        },
        {"loc": ("body", "age"), "msg": "must be positive", "type": "value_error"},
    ]

    response = await error_handler.validation_exception_handler(mock_request, mock_exc)

    body = response.body.decode()
    assert "body.name" in body
    assert "body.age" in body
    assert "field required" in body
    assert "must be positive" in body


@pytest.mark.asyncio
async def test_database_exception_handler_returns_500(mock_request):
    """Test that database errors return 500 status code."""
    mock_exc = MagicMock(spec=SQLAlchemyError)

    with patch("services.api.middleware.error_handler.logger"):
        response = await error_handler.database_exception_handler(mock_request, mock_exc)

    assert response.status_code == 500


@pytest.mark.asyncio
async def test_database_exception_handler_logs_error(mock_request):
    """Test that database errors are logged."""
    mock_exc = MagicMock(spec=SQLAlchemyError)

    with patch("services.api.middleware.error_handler.logger") as mock_logger:
        await error_handler.database_exception_handler(mock_request, mock_exc)

        mock_logger.error.assert_called_once()
        error_args = mock_logger.error.call_args.args
        assert error_args[0] == "Database error at %s: %s"
        assert error_args[2] is mock_exc


@pytest.mark.asyncio
async def test_database_exception_handler_returns_generic_message(mock_request):
    """Test that database errors return generic message to user."""
    mock_exc = MagicMock(spec=SQLAlchemyError)

    with (
        patch("services.api.middleware.error_handler.logger"),
        patch("services.api.middleware.error_handler.get_api_config") as mock_config,
    ):
        mock_config.return_value.debug = False
        response = await error_handler.database_exception_handler(mock_request, mock_exc)

    body = response.body.decode()
    assert "database_error" in body
    assert "An internal error has occurred" in body
    assert "Please create an issue" in body
    assert "UTC" in body
    assert "detail" not in body
    mock_config.assert_called_once_with()


@pytest.mark.asyncio
async def test_database_exception_handler_includes_details_in_debug_mode(mock_request):
    """Test that database errors include details in debug mode."""
    mock_exc = MagicMock(spec=SQLAlchemyError)
    mock_exc.__str__ = MagicMock(return_value="Test database error")

    with (
        patch("services.api.middleware.error_handler.logger"),
        patch("services.api.middleware.error_handler.get_api_config") as mock_config,
    ):
        mock_config.return_value.debug = True
        response = await error_handler.database_exception_handler(mock_request, mock_exc)

    body = response.body.decode()
    assert "database_error" in body
    assert "An internal error has occurred" in body
    assert "detail" in body
    assert "Test database error" in body
    mock_config.assert_called_once_with()


@pytest.mark.asyncio
async def test_general_exception_handler_returns_500(mock_request):
    """Test that general exceptions return 500 status code."""
    mock_exc = Exception("Something went wrong")

    with patch("services.api.middleware.error_handler.logger"):
        response = await error_handler.general_exception_handler(mock_request, mock_exc)

    assert response.status_code == 500


@pytest.mark.asyncio
async def test_general_exception_handler_logs_error(mock_request):
    """Test that general exceptions are logged."""
    mock_exc = Exception("Test error")

    with patch("services.api.middleware.error_handler.logger") as mock_logger:
        await error_handler.general_exception_handler(mock_request, mock_exc)

        mock_logger.error.assert_called_once_with("Unhandled exception: %s", mock_exc)


@pytest.mark.asyncio
async def test_general_exception_handler_returns_generic_message(mock_request):
    """Test that general exceptions return generic message."""
    mock_exc = Exception("Internal error")

    with patch("services.api.middleware.error_handler.logger"):
        response = await error_handler.general_exception_handler(mock_request, mock_exc)

    body = response.body.decode()
    assert "internal_error" in body
    assert "unexpected error occurred" in body


def test_configure_error_handlers_registers_all_handlers(mock_app):
    """Test that configure_error_handlers registers all exception handlers."""
    error_handler.configure_error_handlers(mock_app)

    assert mock_app.add_exception_handler.call_count == 5


def test_configure_error_handlers_registers_validation_errors(mock_app):
    """Test that RequestValidationError handler is registered."""
    error_handler.configure_error_handlers(mock_app)

    calls = [call[0][0] for call in mock_app.add_exception_handler.call_args_list]
    assert RequestValidationError in calls


def test_configure_error_handlers_registers_pydantic_errors(mock_app):
    """Test that Pydantic ValidationError handler is registered."""
    error_handler.configure_error_handlers(mock_app)

    calls = [call[0][0] for call in mock_app.add_exception_handler.call_args_list]
    assert ValidationError in calls


def test_configure_error_handlers_registers_database_errors(mock_app):
    """Test that SQLAlchemyError handler is registered."""
    error_handler.configure_error_handlers(mock_app)

    calls = [call[0][0] for call in mock_app.add_exception_handler.call_args_list]
    assert SQLAlchemyError in calls


def test_configure_error_handlers_registers_general_errors(mock_app):
    """Test that general Exception handler is registered."""
    error_handler.configure_error_handlers(mock_app)

    calls = [call[0][0] for call in mock_app.add_exception_handler.call_args_list]
    assert Exception in calls


@pytest.mark.asyncio
async def test_http_exception_handler_logs_4xx_as_warning(mock_request):
    """Client errors are logged at warning with status, method, path and detail."""
    exc = HTTPException(status_code=403, detail="User does not have permission")

    with patch("services.api.middleware.error_handler.logger") as mock_logger:
        await error_handler.http_exception_handler(mock_request, exc)

    message = _logged_message(mock_logger.warning)
    assert "403" in message
    assert "POST" in message
    assert "/api/v1/games" in message
    assert "User does not have permission" in message
    mock_logger.error.assert_not_called()


@pytest.mark.asyncio
async def test_http_exception_handler_logs_5xx_as_error(mock_request):
    """Server errors are logged at error level."""
    exc = HTTPException(status_code=503, detail="Guild channels not cached")

    with patch("services.api.middleware.error_handler.logger") as mock_logger:
        await error_handler.http_exception_handler(mock_request, exc)

    message = _logged_message(mock_logger.error)
    assert "503" in message
    assert "Guild channels not cached" in message
    mock_logger.warning.assert_not_called()


@pytest.mark.asyncio
async def test_http_exception_handler_logs_structured_detail_without_form_data(mock_request):
    """Dict details log error/message only; echoed form_data (user text) is excluded."""
    exc = HTTPException(
        status_code=422,
        detail={
            "error": "invalid_mentions",
            "message": "Some @mentions could not be resolved",
            "invalid_mentions": [{"input": "<#123>"}],
            "form_data": {"description": "PRIVATE-USER-TEXT"},
        },
    )

    with patch("services.api.middleware.error_handler.logger") as mock_logger:
        await error_handler.http_exception_handler(mock_request, exc)

    mock_logger.warning.assert_called_once_with(
        "HTTP %s on %s %s: %s",
        422,
        "POST",
        "/api/v1/games",
        "invalid_mentions: Some @mentions could not be resolved",
    )


@pytest.mark.asyncio
async def test_http_exception_handler_preserves_response(mock_request):
    """The client still receives FastAPI's standard status, body and headers."""
    exc = HTTPException(status_code=401, detail="Not authenticated", headers={"X-Test": "1"})

    with patch("services.api.middleware.error_handler.logger"):
        response = await error_handler.http_exception_handler(mock_request, exc)

    assert response.status_code == 401
    assert response.body == b'{"detail":"Not authenticated"}'
    assert response.headers["x-test"] == "1"


@pytest.mark.asyncio
async def test_validation_exception_handler_logs_fields_without_input(mock_request):
    """Validation failures are logged with field locations and types, not submitted values."""
    mock_exc = MagicMock(spec=RequestValidationError)
    mock_exc.errors.return_value = [
        {
            "loc": ("body", "max_players"),
            "msg": "value is not a valid integer",
            "type": "int_parsing",
            "input": "PRIVATE-USER-TEXT",
        }
    ]

    with patch("services.api.middleware.error_handler.logger") as mock_logger:
        await error_handler.validation_exception_handler(mock_request, mock_exc)

    mock_logger.warning.assert_called_once_with(
        "Request validation failed on %s %s: %s",
        "POST",
        "/api/v1/games",
        "body.max_players (int_parsing)",
    )


def test_configure_error_handlers_registers_http_exceptions(mock_app):
    """Test that the Starlette HTTPException handler is registered."""
    error_handler.configure_error_handlers(mock_app)

    registered = {call[0][0]: call[0][1] for call in mock_app.add_exception_handler.call_args_list}
    assert registered[StarletteHTTPException] is error_handler.http_exception_handler
