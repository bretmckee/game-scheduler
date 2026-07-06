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
    """Test that APIConfig raises when required env vars are not set."""
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(ValueError):
            config.APIConfig()


def test_api_config_loads_optional_defaults():
    """Test that optional fields have correct defaults when required fields are set."""
    required = {
        "DISCORD_BOT_CLIENT_ID": "id",
        "DISCORD_BOT_CLIENT_SECRET": "secret",
        "DISCORD_BOT_TOKEN": "token",
        "JWT_SECRET": "a-valid-jwt-secret",
    }
    with patch.dict(os.environ, required, clear=True):
        cfg = config.APIConfig()

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
    required = {
        "DISCORD_BOT_CLIENT_ID": "id",
        "DISCORD_BOT_CLIENT_SECRET": "secret",
        "DISCORD_BOT_TOKEN": "token",
        "JWT_SECRET": "a-valid-jwt-secret",
    }
    with patch.dict(os.environ, required, clear=True):
        cfg1 = config.get_api_config()
        cfg2 = config.get_api_config()

    assert cfg1 is cfg2


def test_api_config_debug_mode_in_development():
    """Test that debug mode is enabled in development environment."""
    required = {
        "DISCORD_BOT_CLIENT_ID": "id",
        "DISCORD_BOT_CLIENT_SECRET": "secret",
        "DISCORD_BOT_TOKEN": "token",
        "JWT_SECRET": "a-valid-jwt-secret",
        "ENVIRONMENT": "development",
    }
    with patch.dict(os.environ, required, clear=True):
        cfg = config.APIConfig()
        assert cfg.debug is True


def test_api_config_debug_mode_in_production():
    """Test that debug mode is disabled in production environment."""
    required = {
        "DISCORD_BOT_CLIENT_ID": "id",
        "DISCORD_BOT_CLIENT_SECRET": "secret",
        "DISCORD_BOT_TOKEN": "token",
        "JWT_SECRET": "a-valid-jwt-secret",
        "ENVIRONMENT": "production",
    }
    with patch.dict(os.environ, required, clear=True):
        cfg = config.APIConfig()
        assert cfg.debug is False


def test_get_cookie_domain_same_hostname():
    """Test that _get_cookie_domain returns None for same hostname."""
    result = config._get_cookie_domain("http://localhost:3000", "http://localhost:8000")
    assert result is None


def test_get_cookie_domain_different_subdomains():
    """Test that _get_cookie_domain returns common parent domain."""
    result = config._get_cookie_domain("https://app.example.com", "https://api.example.com")
    assert result == ".example.com"


def test_get_cookie_domain_staging_subdomains():
    """Test cookie domain for staging deployment subdomains."""
    result = config._get_cookie_domain(
        "https://staging.game-scheduler.daddog.com",
        "https://api.staging.game-scheduler.daddog.com",
    )
    assert result == ".staging.game-scheduler.daddog.com"


def test_get_cookie_domain_no_common_parent():
    """Test that _get_cookie_domain returns None for unrelated domains."""
    result = config._get_cookie_domain("https://example.com", "https://other.org")
    assert result is None


def test_get_cookie_domain_invalid_url():
    """Test that _get_cookie_domain handles invalid URLs."""
    result = config._get_cookie_domain("not-a-url", "https://example.com")
    assert result is None


def test_api_config_cookie_domain_derived():
    """Test that APIConfig derives cookie_domain from URLs."""
    env_vars = {
        "DISCORD_BOT_CLIENT_ID": "id",
        "DISCORD_BOT_CLIENT_SECRET": "secret",
        "DISCORD_BOT_TOKEN": "token",
        "JWT_SECRET": "a-valid-jwt-secret",
        "FRONTEND_URL": "https://app.example.com",
        "BACKEND_URL": "https://api.example.com",
    }
    with patch.dict(os.environ, env_vars, clear=True):
        cfg = config.APIConfig()
        assert cfg.cookie_domain == ".example.com"


def test_api_config_cookie_domain_localhost():
    """Test that APIConfig sets cookie_domain to None for localhost."""
    env_vars = {
        "DISCORD_BOT_CLIENT_ID": "id",
        "DISCORD_BOT_CLIENT_SECRET": "secret",
        "DISCORD_BOT_TOKEN": "token",
        "JWT_SECRET": "a-valid-jwt-secret",
        "FRONTEND_URL": "http://localhost:3000",
        "BACKEND_URL": "http://localhost:8000",
    }
    with patch.dict(os.environ, env_vars, clear=True):
        cfg = config.APIConfig()
        assert cfg.cookie_domain is None


def test_api_config_raises_on_missing_discord_client_id():
    """Test that APIConfig raises ValueError when DISCORD_BOT_CLIENT_ID is not set."""
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(ValueError, match="DISCORD_BOT_CLIENT_ID"):
            config.APIConfig()


def test_api_config_raises_on_missing_discord_client_secret():
    """Test that APIConfig raises ValueError when DISCORD_BOT_CLIENT_SECRET is not set."""
    with patch.dict(os.environ, {"DISCORD_BOT_CLIENT_ID": "set"}, clear=True):
        with pytest.raises(ValueError, match="DISCORD_BOT_CLIENT_SECRET"):
            config.APIConfig()


def test_api_config_raises_on_missing_discord_bot_token():
    """Test that APIConfig raises ValueError when DISCORD_BOT_TOKEN is not set."""
    with patch.dict(
        os.environ,
        {"DISCORD_BOT_CLIENT_ID": "set", "DISCORD_BOT_CLIENT_SECRET": "set"},
        clear=True,
    ):
        with pytest.raises(ValueError, match="DISCORD_BOT_TOKEN"):
            config.APIConfig()


def test_api_config_raises_on_insecure_jwt_secret():
    """Test that APIConfig raises ValueError when JWT_SECRET is the known insecure default."""
    insecure_env = {
        "DISCORD_BOT_CLIENT_ID": "set",
        "DISCORD_BOT_CLIENT_SECRET": "set",
        "DISCORD_BOT_TOKEN": "set",
        "JWT_SECRET": "change-me-in-production",
    }
    with patch.dict(os.environ, insecure_env, clear=True):
        with pytest.raises(ValueError, match="JWT_SECRET"):
            config.APIConfig()
