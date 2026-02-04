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

import pytest
from sqlalchemy import select, text

from shared.data_access.guild_isolation import set_current_guild_ids
from shared.models.game import GameSession

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_bot_queries_bypass_rls_see_all_guilds(
    admin_db, bot_db, create_guild, create_channel, create_user, create_game
):
    """Bot queries without guild context should see games from ALL guilds (RLS bypassed)."""
    guild_a = create_guild()
    channel_a = create_channel(guild_id=guild_a["id"])
    user_a = create_user()
    game_a = create_game(guild_id=guild_a["id"], channel_id=channel_a["id"], host_id=user_a["id"])

    guild_b = create_guild()
    channel_b = create_channel(guild_id=guild_b["id"])
    user_b = create_user()
    game_b = create_game(guild_id=guild_b["id"], channel_id=channel_b["id"], host_id=user_b["id"])

    result = await bot_db.execute(
        select(GameSession).where(GameSession.id.in_([game_a["id"], game_b["id"]]))
    )
    games = result.scalars().all()

    assert len(games) == 2, "Bot should see games from ALL guilds (BYPASSRLS privilege)"
    game_ids = [g.id for g in games]
    assert game_a["id"] in game_ids, "Guild A game should be visible to bot"
    assert game_b["id"] in game_ids, "Guild B game should be visible to bot"


@pytest.mark.asyncio
async def test_bot_queries_ignore_guild_context_if_set(
    admin_db, bot_db, create_guild, create_channel, create_user, create_game
):
    """Bot queries should see all guilds even if guild context is set (BYPASSRLS active)."""
    guild_a = create_guild()
    channel_a = create_channel(guild_id=guild_a["id"])
    user_a = create_user()
    game_a = create_game(guild_id=guild_a["id"], channel_id=channel_a["id"], host_id=user_a["id"])

    guild_b = create_guild()
    channel_b = create_channel(guild_id=guild_b["id"])
    user_b = create_user()
    game_b = create_game(guild_id=guild_b["id"], channel_id=channel_b["id"], host_id=user_b["id"])

    set_current_guild_ids([guild_a["guild_id"]])

    result = await bot_db.execute(
        select(GameSession).where(GameSession.id.in_([game_a["id"], game_b["id"]]))
    )
    games = result.scalars().all()

    assert len(games) == 2, "Bot should still see ALL guilds (BYPASSRLS ignores context)"
    game_ids = [g.id for g in games]
    assert game_a["id"] in game_ids, "Guild A game visible"
    assert game_b["id"] in game_ids, "Guild B game visible (not filtered)"


@pytest.mark.asyncio
async def test_bot_user_has_bypassrls_privilege(bot_db):
    """Verify gamebot_bot user has BYPASSRLS privilege (not superuser)."""
    result = await bot_db.execute(
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
async def test_bot_connection_uses_correct_database_user(bot_db):
    """Verify bot session is actually using gamebot_bot user."""
    result = await bot_db.execute(text("SELECT current_user"))
    current_user = result.scalar()

    assert current_user == "gamebot_bot", "Bot session should use gamebot_bot user"
