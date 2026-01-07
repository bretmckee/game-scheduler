# Copyright 2026 Bret McKee (bret.mckee@gmail.com)
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


"""Integration tests for RLS enforcement on guild_configurations table.

Validates that require_guild_by_id() helper respects RLS policies and properly
isolates guild data at the database level.

Test Strategy:
1. Create guild configurations in two different guilds (A and B)
2. Set RLS context to guild A only
3. Verify require_guild_by_id returns guild A config
4. Verify require_guild_by_id raises 404 for guild B config (unauthorized)
5. Verify multiple guild contexts work correctly
6. Verify safe failure when RLS context not set

NOTE: RLS is enabled on game_sessions, game_templates, and game_participants tables
as well. Direct database-level testing of those tables is not feasible due to pytest
transaction management issues, but E2E tests validate RLS works correctly for all
tables in production scenarios.

CRITICAL: These tests require RLS policies to be ENABLED on guild_configurations.
"""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException

from services.api.database import queries
from shared.data_access.guild_isolation import (
    clear_current_guild_ids,
    set_current_guild_ids,
)

pytestmark = pytest.mark.integration


class TestRequireGuildByIdRLSEnforcement:
    """Test require_guild_by_id respects RLS policies on guild_configurations."""

    @pytest.mark.asyncio
    async def test_authorized_access_with_rls_context_set(self, admin_db, app_db, create_guild):
        """User in guild, RLS context set → Success."""
        guild_a = create_guild()
        # Arrange: Set RLS context using Discord guild IDs (not database UUIDs)
        set_current_guild_ids([guild_a["guild_id"]])
        access_token = "test_token"
        user_discord_id = "123456789"

        # Mock oauth2.get_user_guilds (shouldn't be called - context already set)
        with patch(
            "services.api.auth.oauth2.get_user_guilds", new_callable=AsyncMock
        ) as mock_get_guilds:
            # Act
            result = await queries.require_guild_by_id(
                app_db, guild_a["id"], access_token, user_discord_id
            )

            # Assert
            assert result is not None
            assert result.id == guild_a["id"]
            assert result.guild_id == guild_a["guild_id"]
            mock_get_guilds.assert_not_called()

    @pytest.mark.asyncio
    async def test_unauthorized_access_user_not_in_guild(self, admin_db, app_db, create_guild):
        """User NOT in guild, RLS context set → 404."""
        guild_a = create_guild()
        guild_b = create_guild()
        # Arrange: Set context to guild_a only (using Discord guild ID)
        set_current_guild_ids([guild_a["guild_id"]])
        access_token = "test_token"
        user_discord_id = "123456789"

        # Mock oauth2.get_user_guilds (shouldn't be called - context already set)
        with patch(
            "services.api.auth.oauth2.get_user_guilds", new_callable=AsyncMock
        ) as mock_get_guilds:
            # Act & Assert: Try to access guild_b (not in context)
            with pytest.raises(HTTPException) as exc_info:
                await queries.require_guild_by_id(
                    app_db, guild_b["id"], access_token, user_discord_id
                )

            assert exc_info.value.status_code == 404
            assert "Guild configuration not found" in exc_info.value.detail
            mock_get_guilds.assert_not_called()

    @pytest.mark.asyncio
    async def test_safe_failure_when_rls_context_not_set(self, admin_db, app_db, create_guild):
        """RLS context NOT set → Fetches guilds, then enforces authorization."""
        guild_a = create_guild()
        # Arrange: Clear RLS context
        clear_current_guild_ids()
        access_token = "test_token"
        user_discord_id = "123456789"

        # Mock oauth2.get_user_guilds to return empty list (user not in any guilds)
        with patch(
            "services.api.auth.oauth2.get_user_guilds",
            new_callable=AsyncMock,
            return_value=[],
        ) as mock_get_guilds:
            # Act & Assert: Should raise 404 after fetching guilds
            with pytest.raises(HTTPException) as exc_info:
                await queries.require_guild_by_id(
                    app_db, guild_a["id"], access_token, user_discord_id
                )

            assert exc_info.value.status_code == 404
            assert "Guild configuration not found" in exc_info.value.detail
            mock_get_guilds.assert_called_once_with(access_token, user_discord_id)

    @pytest.mark.asyncio
    async def test_multiple_guilds_in_context_valid_request(self, admin_db, app_db, create_guild):
        """Multiple guilds, requesting valid guild → Success."""
        guild_a = create_guild()
        guild_b = create_guild()
        # Arrange: User is in both guilds (use Discord guild IDs)
        set_current_guild_ids([guild_a["guild_id"], guild_b["guild_id"]])
        access_token = "test_token"
        user_discord_id = "123456789"

        # Mock oauth2.get_user_guilds (shouldn't be called)
        with patch(
            "services.api.auth.oauth2.get_user_guilds", new_callable=AsyncMock
        ) as mock_get_guilds:
            # Act: Request guild_a (in context)
            result_a = await queries.require_guild_by_id(
                app_db, guild_a["id"], access_token, user_discord_id
            )

            # Assert
            assert result_a is not None
            assert result_a.id == guild_a["id"]
            assert result_a.guild_id == guild_a["guild_id"]

            # Act: Request guild_b (also in context)
            result_b = await queries.require_guild_by_id(
                app_db, guild_b["id"], access_token, user_discord_id
            )

            # Assert
            assert result_b is not None
            assert result_b.id == guild_b["id"]
            assert result_b.guild_id == guild_b["guild_id"]
            mock_get_guilds.assert_not_called()

    @pytest.mark.asyncio
    async def test_multiple_guilds_in_context_invalid_request(self, admin_db, app_db, create_guild):
        """Multiple guilds, requesting invalid guild → 404."""
        guild_a = create_guild()
        guild_b = create_guild()
        # Arrange: User is in guild_a and guild_b (use Discord guild IDs)
        set_current_guild_ids([guild_a["guild_id"], guild_b["guild_id"]])
        access_token = "test_token"
        user_discord_id = "123456789"
        nonexistent_guild_id = "00000000-0000-0000-0000-000000000000"

        # Mock oauth2.get_user_guilds (shouldn't be called)
        with patch(
            "services.api.auth.oauth2.get_user_guilds", new_callable=AsyncMock
        ) as mock_get_guilds:
            # Act & Assert: Request nonexistent guild
            with pytest.raises(HTTPException) as exc_info:
                await queries.require_guild_by_id(
                    app_db, nonexistent_guild_id, access_token, user_discord_id
                )

            assert exc_info.value.status_code == 404
            assert "Guild configuration not found" in exc_info.value.detail
            mock_get_guilds.assert_not_called()

    @pytest.mark.asyncio
    async def test_context_fetched_only_when_needed(self, admin_db, app_db, create_guild):
        """RLS context fetched from Discord API only when not already set."""
        guild_a = create_guild()
        # Arrange: Clear context to force fetch
        clear_current_guild_ids()
        access_token = "test_token"
        user_discord_id = "123456789"
        mock_discord_guild_id = guild_a["guild_id"]

        # Mock oauth2.get_user_guilds to return guild_a
        with patch(
            "services.api.auth.oauth2.get_user_guilds",
            new_callable=AsyncMock,
            return_value=[{"id": mock_discord_guild_id}],
        ) as mock_get_guilds:
            # Act: First call should fetch from Discord
            result1 = await queries.require_guild_by_id(
                app_db, guild_a["id"], access_token, user_discord_id
            )

            # Assert: First call fetches from Discord
            assert result1 is not None
            assert result1.id == guild_a["id"]
            mock_get_guilds.assert_called_once()

            # Act: Second call should NOT fetch (context already set)
            mock_get_guilds.reset_mock()
            result2 = await queries.require_guild_by_id(
                app_db, guild_a["id"], access_token, user_discord_id
            )

            # Assert: Second call doesn't fetch (idempotent)
            assert result2 is not None
            assert result2.id == guild_a["id"]
            mock_get_guilds.assert_not_called()

    @pytest.mark.asyncio
    async def test_custom_error_message_respected(self, admin_db, app_db, create_guild):
        """Custom error message parameter works correctly."""
        guild_a = create_guild()
        guild_b = create_guild()
        # Arrange: Set context to guild_a only (use Discord guild ID)
        set_current_guild_ids([guild_a["guild_id"]])
        access_token = "test_token"
        user_discord_id = "123456789"
        custom_message = "Custom guild not found message"

        # Mock oauth2.get_user_guilds (shouldn't be called)
        with patch(
            "services.api.auth.oauth2.get_user_guilds", new_callable=AsyncMock
        ) as mock_get_guilds:
            # Act & Assert: Try to access guild_b with custom message
            with pytest.raises(HTTPException) as exc_info:
                await queries.require_guild_by_id(
                    app_db,
                    guild_b["id"],
                    access_token,
                    user_discord_id,
                    not_found_detail=custom_message,
                )

            assert exc_info.value.status_code == 404
            assert custom_message in exc_info.value.detail
            mock_get_guilds.assert_not_called()
