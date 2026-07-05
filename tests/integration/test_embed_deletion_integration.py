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


"""Integration test for Flow 9: bot-initiated embed deletion calls cancel_game directly.

Calls cancel_game(db, game, enqueue_cancellation=False) against a real async DB
session and verifies that the game row is deleted and no bot_action_queue row is
created. Pattern mirrors test_participant_drop_event.py (direct-handler style).
"""

import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import selectinload

from shared.database import bot_engine
from shared.models.game import GameSession
from shared.services.game_cancellation import cancel_game

pytestmark = pytest.mark.integration


@pytest.fixture(autouse=True)
async def _cleanup_engines():
    """Dispose engine pools after each test for clean event loop state."""
    yield
    await bot_engine.dispose()


@pytest.mark.asyncio
async def test_cancel_game_no_enqueue_deletes_game_and_leaves_queue_empty(
    admin_db_sync,
    create_guild,
    create_channel,
    create_user,
    create_game,
):
    """
    cancel_game with enqueue_cancellation=False deletes the game row and
    does not create any bot_action_queue row.
    """
    guild = create_guild(discord_guild_id="801111111111111111")
    channel = create_channel(guild_id=guild["id"], discord_channel_id="801111111111111112")
    host = create_user(discord_user_id="801111111111111113")
    game = create_game(
        guild_id=guild["id"],
        channel_id=channel["id"],
        host_id=host["id"],
        title="Embed Deletion Integration Test Game",
    )
    game_id = game["id"]

    game_row_before = admin_db_sync.execute(
        text("SELECT id FROM game_sessions WHERE id = :id"),
        {"id": game_id},
    ).fetchone()
    assert game_row_before is not None, "Game must exist before cancel_game is called"

    session_factory = async_sessionmaker(bot_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as db:
        result = await db.execute(
            text("SELECT * FROM game_sessions WHERE id = :id"),
            {"id": game_id},
        )
        row = result.mappings().fetchone()
        assert row is not None, "Game not visible to bot session"

        game_obj_result = await db.execute(
            select(GameSession)
            .where(GameSession.id == game_id)
            .options(selectinload(GameSession.channel))
        )
        game_obj = game_obj_result.scalar_one()

        await cancel_game(db, game_obj, enqueue_cancellation=False)
        await db.commit()

    game_row_after = admin_db_sync.execute(
        text("SELECT id FROM game_sessions WHERE id = :id"),
        {"id": game_id},
    ).fetchone()
    assert game_row_after is None, "Game row must be deleted after cancel_game"

    queue_row = admin_db_sync.execute(
        text(
            "SELECT id FROM bot_action_queue "
            "WHERE action_type = 'game_cancelled' AND game_id = :game_id"
        ),
        {"game_id": game_id},
    ).fetchone()
    assert queue_row is None, "No game_cancelled row should exist when enqueue_cancellation=False"
