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


"""Integration tests for bot/daemon RLS bypass using gamebot_bot user.

Validates that bot and daemon services bypass RLS policies when using the
gamebot_bot database user (has BYPASSRLS privilege).

Test Strategy:
1. Create game sessions in two different guilds (A and B)
2. Query game_sessions table using gamebot_bot user WITHOUT setting guild context
3. Verify games from ALL guilds are returned (RLS bypassed)
4. Verify no guild filtering occurs (system service behavior)

CRITICAL: These tests require:
- gamebot_bot user created with BYPASSRLS privilege (non-superuser)
- BOT_DATABASE_URL configured for bot/daemon services
- RLS policies ENABLED on game_sessions table (but bypassed by gamebot_bot)
"""

import os

import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from shared.data_access.guild_isolation import set_current_guild_ids
from shared.models.game import GameSession

pytestmark = pytest.mark.integration


@pytest.fixture
async def bot_db_session():
    """Create database session using gamebot_bot user (bot/daemon user with BYPASSRLS)."""
    raw_url = os.getenv("BOT_DATABASE_URL")
    if not raw_url:
        pytest.skip("BOT_DATABASE_URL not set")

    bot_url = raw_url.replace("postgresql://", "postgresql+asyncpg://")
    bot_engine = create_async_engine(bot_url, echo=False)
    bot_session_factory = async_sessionmaker(
        bot_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )

    async with bot_session_factory() as session:
        yield session
        await session.rollback()

    await bot_engine.dispose()


@pytest.mark.asyncio
async def test_bot_queries_bypass_rls_see_all_guilds(bot_db_session, game_a, game_b):
    """Bot queries without guild context should see games from ALL guilds (RLS bypassed)."""
    result = await bot_db_session.execute(
        select(GameSession).where(GameSession.id.in_([game_a.id, game_b.id]))
    )
    games = result.scalars().all()

    assert len(games) == 2, "Bot should see games from ALL guilds (BYPASSRLS privilege)"
    game_ids = [g.id for g in games]
    assert game_a.id in game_ids, "Guild A game should be visible to bot"
    assert game_b.id in game_ids, "Guild B game should be visible to bot"


@pytest.mark.asyncio
async def test_bot_queries_ignore_guild_context_if_set(
    bot_db_session, game_a, game_b, guild_a_config
):
    """Bot queries should see all guilds even if guild context is set (BYPASSRLS active)."""
    set_current_guild_ids([guild_a_config.guild_id])

    result = await bot_db_session.execute(
        select(GameSession).where(GameSession.id.in_([game_a.id, game_b.id]))
    )
    games = result.scalars().all()

    assert len(games) == 2, "Bot should still see ALL guilds (BYPASSRLS ignores context)"
    game_ids = [g.id for g in games]
    assert game_a.id in game_ids, "Guild A game visible"
    assert game_b.id in game_ids, "Guild B game visible (not filtered)"


@pytest.mark.asyncio
async def test_bot_user_has_bypassrls_privilege(bot_db_session):
    """Verify gamebot_bot user has BYPASSRLS privilege (not superuser)."""
    result = await bot_db_session.execute(
        text(
            """
            SELECT rolsuper, rolbypassrls
            FROM pg_roles
            WHERE rolname = 'gamebot_bot'
            """
        )
    )
    row = result.fetchone()

    assert row is not None, "gamebot_bot user should exist"
    is_superuser, has_bypassrls = row
    assert not is_superuser, "Bot user should NOT be superuser (security principle)"
    assert has_bypassrls, "Bot user MUST have BYPASSRLS privilege"


@pytest.mark.asyncio
async def test_bot_connection_uses_correct_database_user(bot_db_session):
    """Verify bot session is actually using gamebot_bot user."""
    result = await bot_db_session.execute(text("SELECT current_user"))
    current_user = result.scalar()

    assert current_user == "gamebot_bot", "Bot session should use gamebot_bot user"
