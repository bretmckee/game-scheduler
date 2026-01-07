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


"""Integration tests for API RLS enforcement using gamebot_app user.

Validates that API service queries are properly filtered by RLS policies when
using the gamebot_app database user (no BYPASSRLS privilege).

Test Strategy:
1. Create game sessions in two different guilds (A and B)
2. Set RLS context to guild A only
3. Query game_sessions table using gamebot_app user
4. Verify only games from guild A are returned (RLS filtering active)
5. Verify guild B games are NOT returned (filtered by RLS)

CRITICAL: These tests require:
- RLS policies ENABLED on game_sessions table
- API service using DATABASE_URL with gamebot_app user (no BYPASSRLS)
"""

import pytest
from sqlalchemy import select, text

from shared.models.game import GameSession

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_api_queries_filtered_by_rls_with_guild_context(
    admin_db, app_db, create_guild, create_channel, create_user, create_game
):
    """API queries with RLS context set should only return games from authorized guilds."""
    guild_a = create_guild()
    channel_a = create_channel(guild_id=guild_a["id"])
    user_a = create_user()
    game_a = create_game(guild_id=guild_a["id"], channel_id=channel_a["id"], host_id=user_a["id"])

    guild_b = create_guild()
    channel_b = create_channel(guild_id=guild_b["id"])
    user_b = create_user()
    game_b = create_game(guild_id=guild_b["id"], channel_id=channel_b["id"], host_id=user_b["id"])

    # Set RLS context on this session's connection
    await app_db.execute(
        text("SELECT set_config('app.current_guild_ids', :guild_ids, false)"),
        {"guild_ids": guild_a["id"]},
    )

    result = await app_db.execute(
        select(GameSession).where(GameSession.id.in_([game_a["id"], game_b["id"]]))
    )
    games = result.scalars().all()

    guild_ids_returned = [game.guild_id for game in games]
    assert game_a["id"] in [g.id for g in games], "Guild A game should be visible"
    assert game_b["id"] not in [g.id for g in games], "Guild B game should be filtered"
    assert guild_a["id"] in guild_ids_returned, "Only guild A games should be returned"


@pytest.mark.asyncio
async def test_api_queries_return_empty_without_guild_context(
    admin_db, app_db, create_guild, create_channel, create_user, create_game
):
    """API queries without RLS context should return no results (RLS blocks all)."""
    guild_a = create_guild()
    channel_a = create_channel(guild_id=guild_a["id"])
    user_a = create_user()
    game_a = create_game(guild_id=guild_a["id"], channel_id=channel_a["id"], host_id=user_a["id"])

    guild_b = create_guild()
    channel_b = create_channel(guild_id=guild_b["id"])
    user_b = create_user()
    game_b = create_game(guild_id=guild_b["id"], channel_id=channel_b["id"], host_id=user_b["id"])

    result = await app_db.execute(
        select(GameSession).where(GameSession.id.in_([game_a["id"], game_b["id"]]))
    )
    games = result.scalars().all()

    assert len(games) == 0, "No games should be returned without guild context (RLS enforced)"


@pytest.mark.asyncio
async def test_api_queries_with_multiple_guild_context(
    admin_db, app_db, create_guild, create_channel, create_user, create_game
):
    """API queries with multiple guilds in context should return games from all specified guilds."""
    guild_a = create_guild()
    channel_a = create_channel(guild_id=guild_a["id"])
    user_a = create_user()
    game_a = create_game(guild_id=guild_a["id"], channel_id=channel_a["id"], host_id=user_a["id"])

    guild_b = create_guild()
    channel_b = create_channel(guild_id=guild_b["id"])
    user_b = create_user()
    game_b = create_game(guild_id=guild_b["id"], channel_id=channel_b["id"], host_id=user_b["id"])

    # Set RLS context with both guild IDs
    guild_ids_str = f"{guild_a['id']},{guild_b['id']}"
    await app_db.execute(
        text("SELECT set_config('app.current_guild_ids', :guild_ids, false)"),
        {"guild_ids": guild_ids_str},
    )

    result = await app_db.execute(
        select(GameSession).where(GameSession.id.in_([game_a["id"], game_b["id"]]))
    )
    games = result.scalars().all()

    assert len(games) == 2, "Should see games from both guilds when both are in context"
    game_ids = [g.id for g in games]
    assert game_a["id"] in game_ids, "Guild A game should be visible"
    assert game_b["id"] in game_ids, "Guild B game should be visible"


@pytest.mark.asyncio
async def test_rls_policies_enabled_on_game_sessions(app_db):
    """Verify RLS is enabled on game_sessions table for gamebot_app user."""
    result = await app_db.execute(
        text(
            """
            SELECT relrowsecurity, relforcerowsecurity
            FROM pg_class
            WHERE relname = 'game_sessions'
            """
        )
    )
    row = result.fetchone()

    assert row is not None, "game_sessions table should exist"
    rls_enabled, force_rls = row
    assert rls_enabled, "RLS should be enabled on game_sessions table"
