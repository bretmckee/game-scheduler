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


"""Tests for API service configuration."""

import os
from unittest.mock import patch

import pytest

from services.api import config


@pytest.fixture(autouse=True)
def reset_config_singleton():
    """Reset the configuration singleton between tests."""
    config._config_instance = None
    yield
    config._config_instance = None


def test_api_config_loads_defaults():
    """Test that APIConfig loads default values when env vars not set."""
    with patch.dict(os.environ, {}, clear=True):
        cfg = config.APIConfig()

        assert cfg.discord_client_id == ""
        assert cfg.discord_client_secret == ""
        assert cfg.discord_bot_token == ""
        assert "postgresql+asyncpg://" in cfg.database_url
        assert cfg.redis_url == "redis://localhost:6379/0"
        assert cfg.api_host == "0.0.0.0"
        assert cfg.api_port == 8000
        assert cfg.frontend_url == "http://localhost:3000"
        assert cfg.jwt_algorithm == "HS256"
        assert cfg.jwt_expiration_hours == 24
        assert cfg.environment == "development"
        assert cfg.debug is True
        assert cfg.log_level == "INFO"


def test_api_config_loads_from_environment():
    """Test that APIConfig loads values from environment variables."""
    env_vars = {
        "DISCORD_BOT_CLIENT_ID": "test_client_id",
        "DISCORD_BOT_CLIENT_SECRET": "test_secret",
        "DISCORD_BOT_TOKEN": "test_token",
        "DATABASE_URL": "postgresql+asyncpg://test:test@testhost:5432/testdb",
        "REDIS_URL": "redis://testhost:6379/1",
        "RABBITMQ_URL": "amqp://test:test@testhost:5672/",
        "API_HOST": "127.0.0.1",
        "API_PORT": "9000",
        "FRONTEND_URL": "http://example.com:3000",
        "JWT_SECRET": "test_jwt_secret",
        "JWT_EXPIRATION_HOURS": "48",
        "ENVIRONMENT": "production",
        "LOG_LEVEL": "DEBUG",
    }

    with patch.dict(os.environ, env_vars, clear=True):
        cfg = config.APIConfig()

        assert cfg.discord_client_id == "test_client_id"
        assert cfg.discord_client_secret == "test_secret"
        assert cfg.discord_bot_token == "test_token"
        assert cfg.database_url == "postgresql+asyncpg://test:test@testhost:5432/testdb"
        assert cfg.redis_url == "redis://testhost:6379/1"
        assert cfg.rabbitmq_url == "amqp://test:test@testhost:5672/"
        assert cfg.api_host == "127.0.0.1"
        assert cfg.api_port == 9000
        assert cfg.frontend_url == "http://example.com:3000"
        assert cfg.jwt_secret == "test_jwt_secret"
        assert cfg.jwt_expiration_hours == 48
        assert cfg.environment == "production"
        assert cfg.debug is False
        assert cfg.log_level == "DEBUG"


def test_get_api_config_returns_singleton():
    """Test that get_api_config returns the same instance on multiple calls."""
    cfg1 = config.get_api_config()
    cfg2 = config.get_api_config()

    assert cfg1 is cfg2


def test_api_config_debug_mode_in_development():
    """Test that debug mode is enabled in development environment."""
    with patch.dict(os.environ, {"ENVIRONMENT": "development"}, clear=True):
        cfg = config.APIConfig()
        assert cfg.debug is True


def test_api_config_debug_mode_in_production():
    """Test that debug mode is disabled in production environment."""
    with patch.dict(os.environ, {"ENVIRONMENT": "production"}, clear=True):
        cfg = config.APIConfig()
        assert cfg.debug is False
