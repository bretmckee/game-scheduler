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


"""Tests for guild configuration service."""

from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from sqlalchemy import text

from services.api.services import guild_service
from shared.models.guild import GuildConfiguration


@pytest.mark.asyncio
async def test_create_guild_config():
    """Test creating a new guild configuration."""
    mock_db = AsyncMock()
    mock_db.add = Mock()
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()

    guild_discord_id = "123456789012345678"
    settings = {
        "bot_manager_role_ids": ["role1", "role2"],
        "require_host_role": True,
    }

    await guild_service.create_guild_config(mock_db, guild_discord_id, **settings)

    mock_db.add.assert_called_once()
    mock_db.commit.assert_awaited_once()
    mock_db.refresh.assert_awaited_once()

    added_guild = mock_db.add.call_args[0][0]
    assert isinstance(added_guild, GuildConfiguration)
    assert added_guild.guild_id == guild_discord_id
    assert added_guild.bot_manager_role_ids == ["role1", "role2"]
    assert added_guild.require_host_role is True


@pytest.mark.asyncio
async def test_update_guild_config():
    """Test updating a guild configuration."""
    mock_db = AsyncMock()
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()

    guild_config = GuildConfiguration(
        guild_id="123456789012345678",
        bot_manager_role_ids=["role1"],
        require_host_role=False,
    )

    updates = {
        "bot_manager_role_ids": ["role1", "role2", "role3"],
        "require_host_role": True,
    }

    await guild_service.update_guild_config(mock_db, guild_config, **updates)

    assert guild_config.bot_manager_role_ids == ["role1", "role2", "role3"]
    assert guild_config.require_host_role is True
    mock_db.commit.assert_awaited_once()
    mock_db.refresh.assert_awaited_once()


@pytest.mark.asyncio
async def test_update_guild_config_ignores_none_values():
    """Test that update ignores None values."""
    mock_db = AsyncMock()
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()

    guild_config = GuildConfiguration(
        guild_id="123456789012345678",
        bot_manager_role_ids=["role1"],
        require_host_role=False,
    )

    updates = {
        "bot_manager_role_ids": ["role2"],
        "require_host_role": None,  # Will be set to None
    }

    await guild_service.update_guild_config(mock_db, guild_config, **updates)

    assert guild_config.bot_manager_role_ids == ["role2"]
    assert guild_config.require_host_role is None  # Updated to None
    mock_db.commit.assert_awaited_once()
    mock_db.refresh.assert_awaited_once()


@pytest.mark.asyncio
@patch("services.api.services.guild_service.get_discord_client")
@patch("services.api.services.guild_service.get_current_guild_ids")
@patch("services.api.services.guild_service.channel_service.create_channel_config")
@patch("services.api.services.guild_service.queries.get_channel_by_discord_id")
@patch("services.api.services.guild_service.template_service_module.TemplateService")
async def test_sync_user_guilds_expands_rls_context_for_new_guilds(
    mock_template_service_class,
    mock_get_channel,
    mock_create_channel,
    mock_get_current_guild_ids,
    mock_get_discord_client,
):
    """Test that sync_user_guilds expands RLS context to include new guild IDs."""
    # Setup mocks
    mock_db = AsyncMock()
    mock_discord_client = AsyncMock()
    mock_get_discord_client.return_value = mock_discord_client

    # User has MANAGE_GUILD permission for guild A
    manage_guild_permission = 0x00000020
    mock_discord_client.get_guilds = AsyncMock(
        side_effect=[
            # First call: user guilds
            [
                {"id": "guild_a", "permissions": str(manage_guild_permission)},
            ],
            # Second call: bot guilds
            [
                {"id": "guild_a"},
            ],
        ]
    )

    # Guild A doesn't exist in database yet
    mock_execute_result = MagicMock()
    mock_execute_result.scalars.return_value.all.return_value = []
    mock_db.execute = AsyncMock(return_value=mock_execute_result)
    mock_db.add = Mock()
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()

    # Current RLS context has some existing guilds
    mock_get_current_guild_ids.return_value = ["existing_guild_1", "existing_guild_2"]

    # Guild has no channels (to keep test simple)
    mock_discord_client.get_guild_channels = AsyncMock(return_value=[])

    # Execute
    result = await guild_service.sync_user_guilds(mock_db, "access_token", "user_id")

    # Verify RLS context was expanded to include new guild
    execute_calls = mock_db.execute.call_args_list
    rls_set_call = [
        call for call in execute_calls if call[0] and isinstance(call[0][0], type(text("")))
    ]

    assert len(rls_set_call) > 0, "Expected SET LOCAL app.current_guild_ids to be called"

    # Verify the SQL contains all guild IDs (existing + new)
    sql_statement = str(rls_set_call[0][0][0])
    assert "SET LOCAL app.current_guild_ids" in sql_statement
    assert "guild_a" in sql_statement  # New guild included

    # Verify new guild was created
    assert result["new_guilds"] == 1
    assert result["new_channels"] == 0
    mock_db.add.assert_called_once()
    mock_db.commit.assert_awaited()
