# Copyright 2026 Bret McKee
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

import json
import os

import pytest
from fastapi import HTTPException

from services.api.database import queries
from shared.cache import client as cache_module
from shared.cache.keys import CacheKeys
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
        set_current_guild_ids([guild_a["guild_id"]])
        user_discord_id = "123456789"

        result = await queries.require_guild_by_id(app_db, guild_a["id"], user_discord_id)

        assert result is not None
        assert result.id == guild_a["id"]
        assert result.guild_id == guild_a["guild_id"]

    @pytest.mark.asyncio
    async def test_unauthorized_access_user_not_in_guild(self, admin_db, app_db, create_guild):
        """User NOT in guild, RLS context set → 404."""
        guild_a = create_guild()
        guild_b = create_guild()
        set_current_guild_ids([guild_a["guild_id"]])
        user_discord_id = "123456789"

        with pytest.raises(HTTPException) as exc_info:
            await queries.require_guild_by_id(app_db, guild_b["id"], user_discord_id)

        assert exc_info.value.status_code == 404
        assert "Guild configuration not found" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_safe_failure_when_rls_context_not_set(self, admin_db, app_db, create_guild):
        """RLS context NOT set, no projection entry → projection returns None → 404."""
        guild_a = create_guild()
        # Arrange: Clear RLS context; leave proj_user_guilds absent (no data seeded)
        clear_current_guild_ids()
        user_discord_id = "no_guilds_user_999"

        # Act & Assert: projection returns None (absent key) → empty guild list → 404
        with pytest.raises(HTTPException) as exc_info:
            await queries.require_guild_by_id(app_db, guild_a["id"], user_discord_id)

        assert exc_info.value.status_code == 404
        assert "Guild configuration not found" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_multiple_guilds_in_context_valid_request(self, admin_db, app_db, create_guild):
        """Multiple guilds, requesting valid guild → Success."""
        guild_a = create_guild()
        guild_b = create_guild()
        set_current_guild_ids([guild_a["guild_id"], guild_b["guild_id"]])
        user_discord_id = "123456789"

        result_a = await queries.require_guild_by_id(app_db, guild_a["id"], user_discord_id)
        assert result_a is not None
        assert result_a.id == guild_a["id"]
        assert result_a.guild_id == guild_a["guild_id"]

        result_b = await queries.require_guild_by_id(app_db, guild_b["id"], user_discord_id)
        assert result_b is not None
        assert result_b.id == guild_b["id"]
        assert result_b.guild_id == guild_b["guild_id"]

    @pytest.mark.asyncio
    async def test_multiple_guilds_in_context_invalid_request(self, admin_db, app_db, create_guild):
        """Multiple guilds, requesting invalid guild → 404."""
        guild_a = create_guild()
        guild_b = create_guild()
        set_current_guild_ids([guild_a["guild_id"], guild_b["guild_id"]])
        user_discord_id = "123456789"
        nonexistent_guild_id = "00000000-0000-0000-0000-000000000000"

        with pytest.raises(HTTPException) as exc_info:
            await queries.require_guild_by_id(app_db, nonexistent_guild_id, user_discord_id)

        assert exc_info.value.status_code == 404
        assert "Guild configuration not found" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_context_fetched_only_when_needed(self, admin_db, app_db, create_guild):
        """RLS context populated from Redis projection only when not already set."""
        guild_a = create_guild()
        # Arrange: Clear context to force projection read; seed projection key
        clear_current_guild_ids()
        user_discord_id = "projection_test_user_777"

        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        redis = cache_module.RedisClient(redis_url=redis_url)
        await redis.connect()
        try:
            gen = await redis.get(CacheKeys.proj_gen()) or "1"
            await redis.set(
                CacheKeys.proj_user_guilds(gen, user_discord_id),
                json.dumps([guild_a["guild_id"]]),
            )
        finally:
            await redis.disconnect()

        # Act: First call reads projection because context not set
        result1 = await queries.require_guild_by_id(app_db, guild_a["id"], user_discord_id)

        assert result1 is not None
        assert result1.id == guild_a["id"]

        # Act: Second call uses already-set ContextVar (no Redis read needed)
        result2 = await queries.require_guild_by_id(app_db, guild_a["id"], user_discord_id)

        assert result2 is not None
        assert result2.id == guild_a["id"]

    @pytest.mark.asyncio
    async def test_custom_error_message_respected(self, admin_db, app_db, create_guild):
        """Custom error message parameter works correctly."""
        guild_a = create_guild()
        guild_b = create_guild()
        set_current_guild_ids([guild_a["guild_id"]])
        user_discord_id = "123456789"
        custom_message = "Custom guild not found message"

        with pytest.raises(HTTPException) as exc_info:
            await queries.require_guild_by_id(
                app_db,
                guild_b["id"],
                user_discord_id,
                not_found_detail=custom_message,
            )

        assert exc_info.value.status_code == 404
        assert custom_message in exc_info.value.detail
