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


"""Tests for API main entry point."""

import logging
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.api import main


def test_setup_logging_configures_level():
    """Test that setup_logging configures the correct log level."""
    with patch("logging.basicConfig") as mock_basic_config:
        main.setup_logging("WARNING")

        mock_basic_config.assert_called_once()
        call_kwargs = mock_basic_config.call_args[1]
        assert call_kwargs["level"] == logging.WARNING


def test_setup_logging_with_debug_level():
    """Test that setup_logging handles DEBUG level correctly."""
    with patch("logging.basicConfig") as mock_basic_config:
        main.setup_logging("DEBUG")

        call_kwargs = mock_basic_config.call_args[1]
        assert call_kwargs["level"] == logging.DEBUG


def test_setup_logging_with_lowercase_level():
    """Test that setup_logging handles lowercase log level strings."""
    with patch("logging.basicConfig") as mock_basic_config:
        main.setup_logging("info")

        call_kwargs = mock_basic_config.call_args[1]
        assert call_kwargs["level"] == logging.INFO


@pytest.mark.asyncio
async def test_main_starts_uvicorn_server():
    """Test that main function starts Uvicorn server with correct configuration."""
    mock_server = MagicMock()
    mock_server.serve = AsyncMock()

    with patch("services.api.main.get_api_config") as mock_config:
        mock_config.return_value.api_host = "127.0.0.1"
        mock_config.return_value.api_port = 9000
        mock_config.return_value.log_level = "INFO"
        mock_config.return_value.debug = True

        with patch("services.api.main.uvicorn.Server", return_value=mock_server):
            with patch("services.api.main.create_app"):
                with patch("services.api.main.setup_logging"):
                    await main.main()

                    mock_server.serve.assert_called_once()


@pytest.mark.asyncio
async def test_main_uses_config_values():
    """Test that main function uses configuration values correctly."""
    with patch("services.api.main.get_api_config") as mock_config:
        mock_config.return_value.api_host = "0.0.0.0"
        mock_config.return_value.api_port = 8080
        mock_config.return_value.log_level = "DEBUG"
        mock_config.return_value.debug = False

        with patch("services.api.main.uvicorn.Config") as mock_uvicorn_config:
            with patch("services.api.main.uvicorn.Server") as mock_server:
                mock_server.return_value.serve = AsyncMock()

                with patch("services.api.main.create_app"):
                    with patch("services.api.main.setup_logging"):
                        await main.main()

                        # Verify uvicorn.Config was called with correct values
                        call_kwargs = mock_uvicorn_config.call_args[1]
                        assert call_kwargs["host"] == "0.0.0.0"
                        assert call_kwargs["port"] == 8080
                        assert call_kwargs["log_level"] == "debug"
                        assert call_kwargs["access_log"] is False
