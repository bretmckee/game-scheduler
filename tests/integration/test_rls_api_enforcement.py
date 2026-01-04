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

import os

import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from shared.models.game import GameSession

pytestmark = pytest.mark.integration


@pytest.fixture
async def app_db_session():
    """Create database session using gamebot_app user (API user with RLS enforced)."""
    raw_url = os.getenv("DATABASE_URL")
    if not raw_url:
        pytest.skip("DATABASE_URL not set")

    app_url = raw_url.replace("postgresql://", "postgresql+asyncpg://")
    app_engine = create_async_engine(app_url, echo=False)
    app_session_factory = async_sessionmaker(
        app_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )

    async with app_session_factory() as session:
        yield session
        await session.rollback()

    await app_engine.dispose()


@pytest.mark.asyncio
async def test_api_queries_filtered_by_rls_with_guild_context(
    app_db_session, game_a, game_b, guild_a_config
):
    """API queries with RLS context set should only return games from authorized guilds."""
    # Set RLS context on this session's connection
    await app_db_session.execute(
        text("SELECT set_config('app.current_guild_ids', :guild_ids, false)"),
        {"guild_ids": guild_a_config.id},
    )

    result = await app_db_session.execute(
        select(GameSession).where(GameSession.id.in_([game_a.id, game_b.id]))
    )
    games = result.scalars().all()

    guild_ids_returned = [game.guild_id for game in games]
    assert game_a.id in [g.id for g in games], "Guild A game should be visible"
    assert game_b.id not in [g.id for g in games], "Guild B game should be filtered"
    assert guild_a_config.id in guild_ids_returned, "Only guild A games should be returned"


@pytest.mark.asyncio
async def test_api_queries_return_empty_without_guild_context(app_db_session, game_a, game_b):
    """API queries without RLS context should return no results (RLS blocks all)."""
    result = await app_db_session.execute(
        select(GameSession).where(GameSession.id.in_([game_a.id, game_b.id]))
    )
    games = result.scalars().all()

    assert len(games) == 0, "No games should be returned without guild context (RLS enforced)"


@pytest.mark.asyncio
async def test_api_queries_with_multiple_guild_context(
    app_db_session, game_a, game_b, guild_a_config, guild_b_config
):
    """API queries with multiple guilds in context should return games from all specified guilds."""
    # Set RLS context with both guild IDs
    guild_ids_str = f"{guild_a_config.id},{guild_b_config.id}"
    await app_db_session.execute(
        text("SELECT set_config('app.current_guild_ids', :guild_ids, false)"),
        {"guild_ids": guild_ids_str},
    )

    result = await app_db_session.execute(
        select(GameSession).where(GameSession.id.in_([game_a.id, game_b.id]))
    )
    games = result.scalars().all()

    assert len(games) == 2, "Should see games from both guilds when both are in context"
    game_ids = [g.id for g in games]
    assert game_a.id in game_ids, "Guild A game should be visible"
    assert game_b.id in game_ids, "Guild B game should be visible"


@pytest.mark.asyncio
async def test_rls_policies_enabled_on_game_sessions(app_db_session):
    """Verify RLS is enabled on game_sessions table for gamebot_app user."""
    result = await app_db_session.execute(
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
