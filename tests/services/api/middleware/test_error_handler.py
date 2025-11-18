"""Tests for error handler middleware."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError

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
    return request


@pytest.mark.asyncio
async def test_validation_exception_handler_returns_422(mock_request):
    """Test that validation errors return 422 status code."""
    mock_exc = MagicMock(spec=RequestValidationError)
    mock_exc.errors.return_value = [
        {"loc": ("body", "name"), "msg": "field required", "type": "value_error.missing"}
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
        {"loc": ("body", "name"), "msg": "field required", "type": "value_error.missing"},
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


@pytest.mark.asyncio
async def test_database_exception_handler_returns_generic_message(mock_request):
    """Test that database errors return generic message to user."""
    mock_exc = MagicMock(spec=SQLAlchemyError)

    with patch("services.api.middleware.error_handler.logger"):
        response = await error_handler.database_exception_handler(mock_request, mock_exc)

    body = response.body.decode()
    assert "database_error" in body
    assert "database error occurred" in body


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

        mock_logger.error.assert_called_once()


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

    assert mock_app.add_exception_handler.call_count == 4


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
