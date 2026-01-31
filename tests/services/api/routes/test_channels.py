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


"""Unit tests for channel configuration endpoints."""

import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.api.routes import channels
from shared.schemas import channel as channel_schemas


@pytest.fixture
def mock_db():
    """Create mock database session."""
    return AsyncMock()


@pytest.fixture
def mock_channel_config():
    """Create mock channel configuration."""
    config = MagicMock()
    config.id = str(uuid.uuid4())
    config.guild_id = str(uuid.uuid4())
    config.channel_id = "987654321"
    config.is_active = True
    config.created_at = datetime(2024, 1, 1, 12, 0, 0)
    config.updated_at = datetime(2024, 1, 1, 12, 0, 0)

    # Mock guild relationship
    mock_guild = MagicMock()
    mock_guild.guild_id = "111222333"
    config.guild = mock_guild

    return config


class TestBuildChannelConfigResponse:
    """Test _build_channel_config_response helper function."""

    @pytest.mark.asyncio
    async def test_build_response_with_all_fields(self, mock_channel_config):
        """Test building response with all fields populated."""
        with patch("shared.discord.client.fetch_channel_name_safe") as mock_fetch_name:
            mock_fetch_name.return_value = "test-channel"

            result = await channels._build_channel_config_response(mock_channel_config)

            assert result.id == mock_channel_config.id
            assert result.guild_id == mock_channel_config.guild_id
            assert result.guild_discord_id == mock_channel_config.guild.guild_id
            assert result.channel_id == mock_channel_config.channel_id
            assert result.channel_name == "test-channel"
            assert result.is_active is True
            assert result.created_at == "2024-01-01T12:00:00"
            assert result.updated_at == "2024-01-01T12:00:00"

            mock_fetch_name.assert_called_once_with(mock_channel_config.channel_id)

    @pytest.mark.asyncio
    async def test_build_response_with_inactive_channel(self, mock_channel_config):
        """Test building response when channel is inactive."""
        mock_channel_config.is_active = False

        with patch("shared.discord.client.fetch_channel_name_safe") as mock_fetch_name:
            mock_fetch_name.return_value = "inactive-channel"

            result = await channels._build_channel_config_response(mock_channel_config)

            assert result.is_active is False

    @pytest.mark.asyncio
    async def test_build_response_timestamp_formatting(self, mock_channel_config):
        """Test that timestamps are properly formatted using isoformat()."""
        mock_channel_config.created_at = datetime(2025, 12, 25, 15, 30, 45)
        mock_channel_config.updated_at = datetime(2025, 12, 26, 16, 31, 46)

        with patch("shared.discord.client.fetch_channel_name_safe") as mock_fetch_name:
            mock_fetch_name.return_value = "test-channel"

            result = await channels._build_channel_config_response(mock_channel_config)

            assert result.created_at == "2025-12-25T15:30:45"
            assert result.updated_at == "2025-12-26T16:31:46"

    @pytest.mark.asyncio
    async def test_build_response_channel_name_resolution(self, mock_channel_config):
        """Test that channel_name is fetched using fetch_channel_name_safe()."""
        expected_channel_name = "my-custom-channel"

        with patch("shared.discord.client.fetch_channel_name_safe") as mock_fetch_name:
            mock_fetch_name.return_value = expected_channel_name

            result = await channels._build_channel_config_response(mock_channel_config)

            assert result.channel_name == expected_channel_name
            mock_fetch_name.assert_called_once_with(mock_channel_config.channel_id)

    @pytest.mark.asyncio
    async def test_build_response_guild_relationship(self, mock_channel_config):
        """Test that guild_discord_id is correctly extracted from guild relationship."""
        expected_guild_discord_id = "444555666"
        mock_channel_config.guild.guild_id = expected_guild_discord_id

        with patch("shared.discord.client.fetch_channel_name_safe") as mock_fetch_name:
            mock_fetch_name.return_value = "test-channel"

            result = await channels._build_channel_config_response(mock_channel_config)

            assert result.guild_discord_id == expected_guild_discord_id

    @pytest.mark.asyncio
    async def test_build_response_returns_correct_schema_type(self, mock_channel_config):
        """Test that response is of correct schema type."""
        with patch("shared.discord.client.fetch_channel_name_safe") as mock_fetch_name:
            mock_fetch_name.return_value = "test-channel"

            result = await channels._build_channel_config_response(mock_channel_config)

            assert isinstance(result, channel_schemas.ChannelConfigResponse)


class TestUpdateChannelConfig:
    """Test update_channel_config endpoint."""

    @pytest.mark.asyncio
    async def test_update_channel_config_success(self, mock_db, mock_channel_config):
        """Test successful channel configuration update."""
        mock_current_user = MagicMock()

        with (
            patch("services.api.routes.channels.queries.get_channel_by_id") as mock_get_channel,
            patch(
                "services.api.routes.channels.channel_service.update_channel_config"
            ) as mock_update,
            patch(
                "services.api.routes.channels._build_channel_config_response"
            ) as mock_build_response,
        ):
            mock_get_channel.return_value = mock_channel_config
            mock_update.return_value = mock_channel_config
            mock_build_response.return_value = channel_schemas.ChannelConfigResponse(
                id=mock_channel_config.id,
                guild_id=mock_channel_config.guild_id,
                guild_discord_id=mock_channel_config.guild.guild_id,
                channel_id=mock_channel_config.channel_id,
                channel_name="test-channel",
                is_active=False,
                created_at="2024-01-01T12:00:00",
                updated_at="2024-01-01T12:00:00",
            )

            request = channel_schemas.ChannelConfigUpdateRequest(is_active=False)
            result = await channels.update_channel_config(
                mock_channel_config.id, request, mock_current_user, mock_db
            )

            mock_get_channel.assert_called_once_with(mock_db, mock_channel_config.id)
            mock_update.assert_called_once_with(mock_channel_config, is_active=False)
            assert result.is_active is False
