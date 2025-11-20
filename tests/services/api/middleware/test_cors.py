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


"""Tests for CORS middleware configuration."""

from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI

from services.api.config import APIConfig
from services.api.middleware import cors


@pytest.fixture
def mock_app():
    """Mock FastAPI application."""
    app = MagicMock(spec=FastAPI)
    app.add_middleware = MagicMock()
    return app


@pytest.fixture
def mock_config():
    """Mock API configuration."""
    config = MagicMock(spec=APIConfig)
    config.frontend_url = "http://localhost:3000"
    config.debug = False
    return config


def test_configure_cors_adds_middleware(mock_app, mock_config):
    """Test that configure_cors adds CORS middleware to the app."""
    cors.configure_cors(mock_app, mock_config)

    mock_app.add_middleware.assert_called_once()


def test_configure_cors_includes_frontend_url(mock_app, mock_config):
    """Test that CORS configuration includes the frontend URL."""
    mock_config.frontend_url = "http://example.com:3000"

    cors.configure_cors(mock_app, mock_config)

    call_kwargs = mock_app.add_middleware.call_args[1]
    origins = call_kwargs["allow_origins"]
    assert "http://example.com:3000" in origins


def test_configure_cors_includes_localhost_urls(mock_app, mock_config):
    """Test that CORS configuration includes localhost URLs."""
    cors.configure_cors(mock_app, mock_config)

    call_kwargs = mock_app.add_middleware.call_args[1]
    origins = call_kwargs["allow_origins"]
    assert "http://localhost:3000" in origins
    assert "http://localhost:3001" in origins


def test_configure_cors_allows_all_origins_in_debug(mock_app, mock_config):
    """Test that CORS includes additional dev origins in debug mode."""
    mock_config.debug = True

    cors.configure_cors(mock_app, mock_config)

    call_kwargs = mock_app.add_middleware.call_args[1]
    origins = call_kwargs["allow_origins"]
    # Debug mode adds more localhost variants but not "*" due to allow_credentials=True
    assert "http://localhost:5173" in origins
    assert "http://127.0.0.1:3000" in origins


def test_configure_cors_restricts_origins_in_production(mock_app, mock_config):
    """Test that CORS restricts origins in production mode."""
    mock_config.debug = False

    cors.configure_cors(mock_app, mock_config)

    call_kwargs = mock_app.add_middleware.call_args[1]
    origins = call_kwargs["allow_origins"]
    assert "*" not in origins


def test_configure_cors_allows_credentials(mock_app, mock_config):
    """Test that CORS configuration allows credentials."""
    cors.configure_cors(mock_app, mock_config)

    call_kwargs = mock_app.add_middleware.call_args[1]
    assert call_kwargs["allow_credentials"] is True


def test_configure_cors_allows_all_methods(mock_app, mock_config):
    """Test that CORS configuration allows all HTTP methods."""
    cors.configure_cors(mock_app, mock_config)

    call_kwargs = mock_app.add_middleware.call_args[1]
    assert call_kwargs["allow_methods"] == ["*"]


def test_configure_cors_allows_all_headers(mock_app, mock_config):
    """Test that CORS configuration allows all headers."""
    cors.configure_cors(mock_app, mock_config)

    call_kwargs = mock_app.add_middleware.call_args[1]
    assert call_kwargs["allow_headers"] == ["*"]
    assert call_kwargs["expose_headers"] == ["*"]
