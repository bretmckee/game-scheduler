"""Tests for bot configuration management."""

import os
from unittest.mock import patch

import pytest

from services.bot.config import BotConfig, get_config


class TestBotConfig:
    """Test suite for BotConfig class."""

    def test_config_with_required_fields(self) -> None:
        """Test configuration creation with all required fields."""
        config = BotConfig(
            discord_bot_token="test_token",
            discord_client_id="123456789",
        )

        assert config.discord_bot_token == "test_token"
        assert config.discord_client_id == "123456789"

    def test_config_with_defaults(self) -> None:
        """Test that optional fields have correct default values."""
        with patch.dict(os.environ, {}, clear=True):
            config = BotConfig(
                discord_bot_token="test_token",
                discord_client_id="123456789",
                _env_file=None,
            )

            assert (
                config.database_url
                == "postgresql+asyncpg://postgres:postgres@localhost:5432/game_scheduler"
            )
            assert config.rabbitmq_url == "amqp://guest:guest@localhost:5672/"
            assert config.redis_url == "redis://localhost:6379/0"
            assert config.log_level == "INFO"
            assert config.environment == "development"

    def test_config_with_custom_values(self) -> None:
        """Test configuration with custom values for optional fields."""
        config = BotConfig(
            discord_bot_token="test_token",
            discord_client_id="123456789",
            database_url="postgresql+asyncpg://custom:pass@db:5432/custom_db",
            rabbitmq_url="amqp://user:pass@rabbitmq:5672/",
            redis_url="redis://redis:6379/1",
            log_level="DEBUG",
            environment="production",
        )

        assert config.database_url == "postgresql+asyncpg://custom:pass@db:5432/custom_db"
        assert config.rabbitmq_url == "amqp://user:pass@rabbitmq:5672/"
        assert config.redis_url == "redis://redis:6379/1"
        assert config.log_level == "DEBUG"
        assert config.environment == "production"

    def test_config_missing_required_field(self) -> None:
        """Test that missing required fields raise validation error."""
        from pydantic import ValidationError

        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValidationError):
                BotConfig(discord_bot_token="test_token", _env_file=None)

    def test_config_from_environment(self) -> None:
        """Test configuration loading from environment variables."""
        env_vars = {
            "DISCORD_BOT_TOKEN": "env_token",
            "DISCORD_CLIENT_ID": "987654321",
            "LOG_LEVEL": "WARNING",
            "ENVIRONMENT": "staging",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            config = BotConfig()

            assert config.discord_bot_token == "env_token"
            assert config.discord_client_id == "987654321"
            assert config.log_level == "WARNING"
            assert config.environment == "staging"

    def test_config_case_insensitive(self) -> None:
        """Test that environment variable names are case-insensitive."""
        env_vars = {
            "discord_bot_token": "lower_token",
            "DISCORD_CLIENT_ID": "123456789",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            config = BotConfig()

            assert config.discord_bot_token == "lower_token"
            assert config.discord_client_id == "123456789"


class TestGetConfig:
    """Test suite for get_config function."""

    def test_get_config_returns_singleton(self) -> None:
        """Test that get_config returns the same instance on multiple calls."""
        with patch.dict(os.environ, {"DISCORD_BOT_TOKEN": "token", "DISCORD_CLIENT_ID": "123"}):
            from services.bot import config as config_module

            config_module._config = None

            config1 = get_config()
            config2 = get_config()

            assert config1 is config2

    def test_get_config_creates_instance(self) -> None:
        """Test that get_config creates a valid BotConfig instance."""
        with patch.dict(os.environ, {"DISCORD_BOT_TOKEN": "token", "DISCORD_CLIENT_ID": "123"}):
            from services.bot import config as config_module

            config_module._config = None

            config = get_config()

            assert isinstance(config, BotConfig)
            assert config.discord_bot_token == "token"
            assert config.discord_client_id == "123"
