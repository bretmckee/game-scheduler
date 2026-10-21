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


"""Tests for API application factory."""

import logging
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from services.api import app


@pytest.fixture
def mock_redis_client():
    """Mock Redis client for testing."""
    mock_client = AsyncMock()
    mock_client.connect = AsyncMock()
    mock_client.disconnect = AsyncMock()
    return mock_client


@pytest.fixture
def mock_get_redis_client(mock_redis_client):
    """Mock get_redis_client function."""
    with patch("services.api.app.redis_client.get_redis_client") as mock:
        mock.return_value = mock_redis_client
        yield mock


def test_create_app_returns_fastapi_instance():
    """Test that create_app returns a FastAPI application instance."""
    with patch("services.api.app.redis_client.get_redis_client"):
        application = app.create_app()
        assert isinstance(application, FastAPI)


def test_create_app_configures_title_and_version():
    """Test that application has correct title and version."""
    with patch("services.api.app.redis_client.get_redis_client"):
        application = app.create_app()
        assert application.title == "Discord Game Scheduler API"
        assert application.version == "1.0.0"


def test_create_app_enables_docs_in_debug_mode():
    """Test that OpenAPI docs are enabled in debug mode."""
    with patch("services.api.app.get_api_config") as mock_config:
        mock_config.return_value.debug = True
        with patch("services.api.app.redis_client.get_redis_client"):
            application = app.create_app()
            assert application.docs_url == "/docs"
            assert application.redoc_url == "/redoc"
        mock_config.assert_called_once_with()


def test_create_app_disables_docs_in_production():
    """Test that OpenAPI docs are disabled in production mode."""
    with patch("services.api.app.get_api_config") as mock_config:
        mock_config.return_value.debug = False
        with patch("services.api.app.redis_client.get_redis_client"):
            application = app.create_app()
            assert application.docs_url is None
            assert application.redoc_url is None
        mock_config.assert_called_once_with()


def test_health_check_endpoint():
    """Test that health check endpoint returns correct response."""
    with patch("services.api.app.redis_client.get_redis_client"):
        application = app.create_app()
        client = TestClient(application)

        response = client.get("/health")

        assert response.status_code == 200
        response_data = response.json()
        assert response_data["status"] == "healthy"
        assert response_data["service"] == "api"
        assert "version" in response_data


@pytest.mark.asyncio
async def test_lifespan_initializes_redis(mock_redis_client):
    """Test that lifespan initializes Redis connection on startup."""
    with patch("services.api.app.redis_client.get_redis_client") as mock_get_redis_client:
        mock_get_redis_client.return_value = mock_redis_client
        application = app.create_app()

        async with app.lifespan(application):
            pass

        mock_get_redis_client.assert_called_once_with()


@pytest.mark.asyncio
async def test_lifespan_logs_git_version(mock_redis_client):
    """Test that lifespan logs the git version on startup."""
    with (
        patch("services.api.app.redis_client.get_redis_client", return_value=mock_redis_client),
        patch("services.api.app.get_git_version", return_value="0.0.1.post479+ge95e5f2"),
        patch("services.api.app.logger") as mock_logger,
    ):
        application = app.create_app()

        async with app.lifespan(application):
            pass

        mock_logger.info.assert_any_call("API version: %s", "0.0.1.post479+ge95e5f2")


@pytest.mark.asyncio
async def test_lifespan_disconnects_redis(mock_get_redis_client, mock_redis_client):
    """Test that lifespan disconnects Redis on shutdown."""
    application = app.create_app()

    async with app.lifespan(application):
        pass

    mock_redis_client.disconnect.assert_called_once_with()


def test_middleware_configured():
    """Test that CORS and error handler middleware are configured."""
    with (
        patch("services.api.app.middleware.cors.configure_cors") as mock_cors,
        patch("services.api.app.middleware.error_handler.configure_error_handlers") as mock_error,
        patch("services.api.app.redis_client.get_redis_client"),
    ):
        application = app.create_app()

        mock_cors.assert_called_once()
        mock_error.assert_called_once()

        # Verify the app was passed to both middleware configurers
        assert mock_cors.call_args[0][0] == application
        assert mock_error.call_args[0][0] == application


_ERROR_HANDLER_LOGGER = "services.api.middleware.error_handler"


@pytest.fixture
def client():
    """In-process client for the real app (lifespan is not started)."""
    with patch("services.api.app.redis_client.get_redis_client"):
        application = app.create_app()
    return application, TestClient(application, raise_server_exceptions=False)


def _warnings(caplog) -> list[str]:
    return [
        r.getMessage()
        for r in caplog.records
        if r.name == _ERROR_HANDLER_LOGGER and r.levelno == logging.WARNING
    ]


def test_unknown_route_404_is_logged(client, caplog):
    """A router-level 404 reaches the HTTPException handler registered by create_app."""
    _, test_client = client

    with caplog.at_level(logging.WARNING, logger=_ERROR_HANDLER_LOGGER):
        response = test_client.get("/api/v1/does-not-exist")

    assert response.status_code == 404
    assert _warnings(caplog) == ["HTTP 404 on GET /api/v1/does-not-exist: Not Found"]


def test_unauthenticated_request_401_is_logged(client, caplog):
    """A real route's auth failure (no session cookie) is logged with its status and path."""
    _, test_client = client

    with caplog.at_level(logging.WARNING, logger=_ERROR_HANDLER_LOGGER):
        response = test_client.get("/api/v1/games")

    assert response.status_code == 401
    assert _warnings(caplog) == ["HTTP 401 on GET /api/v1/games: Not authenticated"]


def test_request_validation_failure_is_logged_by_field(client, caplog):
    """A request failing FastAPI parameter validation is logged with field and error type."""
    application, test_client = client

    @application.get("/_validation_probe")
    async def probe(count: int) -> dict[str, int]:
        return {"count": count}

    with caplog.at_level(logging.WARNING, logger=_ERROR_HANDLER_LOGGER):
        response = test_client.get("/_validation_probe?count=not-a-number")

    assert response.status_code == 422
    assert _warnings(caplog) == [
        "Request validation failed on GET /_validation_probe: query.count (int_parsing)"
    ]


def test_rate_limited_request_is_logged_and_still_returns_429(client, caplog):
    """A throttled request is logged by the wrapped handler and keeps slowapi's response."""
    application, test_client = client

    @application.get("/_rate_limit_probe")
    @app.limiter.limit("1/minute")
    async def probe(request: Request) -> dict[str, int]:
        return {"ok": 1}

    try:
        assert test_client.get("/_rate_limit_probe").status_code == 200
        with caplog.at_level(logging.WARNING, logger=_ERROR_HANDLER_LOGGER):
            response = test_client.get("/_rate_limit_probe")
    finally:
        app.limiter.reset()

    assert response.status_code == 429
    assert response.json() == {"error": "Rate limit exceeded: 1 per 1 minute"}
    assert _warnings(caplog) == ["Rate limit exceeded on GET /_rate_limit_probe: 1 per 1 minute"]
