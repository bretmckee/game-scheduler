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


"""Unit tests for RabbitMQ messaging configuration."""

from shared.messaging.config import RabbitMQConfig


class TestRabbitMQConfig:
    """Test RabbitMQ configuration."""

    def test_default_config(self):
        """Test default configuration values."""
        config = RabbitMQConfig(password="test-password")

        assert config.host == "localhost"
        assert config.port == 5672
        assert config.username == "guest"
        assert config.password == "test-password"
        assert config.virtual_host == "/"
        assert config.connection_timeout == 60
        assert config.heartbeat == 60

    def test_custom_config(self):
        """Test custom configuration values."""
        config = RabbitMQConfig(
            host="rabbitmq.example.com",
            port=5673,
            username="admin",
            password="secret",
            virtual_host="/custom",
            connection_timeout=30,
            heartbeat=30,
        )

        assert config.host == "rabbitmq.example.com"
        assert config.port == 5673
        assert config.username == "admin"
        assert config.password == "secret"
        assert config.virtual_host == "/custom"
        assert config.connection_timeout == 30
        assert config.heartbeat == 30

    def test_url_generation_default(self):
        """Test URL generation with default values."""
        config = RabbitMQConfig(password="guest")
        expected_url = "amqp://guest:guest@localhost:5672/"

        assert config.url == expected_url

    def test_url_generation_custom(self):
        """Test URL generation with custom values."""
        config = RabbitMQConfig(
            password="secret",
            host="rabbitmq.example.com",
            port=5673,
            username="admin",
            virtual_host="/custom",
        )
        expected_url = "amqp://admin:secret@rabbitmq.example.com:5673/custom"

        assert config.url == expected_url

    def test_url_generation_special_chars(self):
        """Test URL generation handles special characters."""
        config = RabbitMQConfig(
            password="p@ssw0rd!",
            username="user@domain",
        )

        assert "user@domain" in config.url
        assert "p@ssw0rd!" in config.url
