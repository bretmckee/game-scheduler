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


"""Integration test for Flow 10 SSE: handle_join_game fires pg_notify('game_updated_sse').

Calls handle_join_game with a patched DB session (BYPASSRLS) and verifies
that a pg_notify on the 'game_updated_sse' channel is received by an asyncpg
LISTEN connection. Pattern reuses machinery from test_join_game.py and
test_sse_bridge_integration.py.
"""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import asyncpg
import discord
import pytest

from services.bot.handlers.join_game import handle_join_game
from shared.database import BASE_DATABASE_URL, BotAsyncSessionLocal, bot_engine
from shared.utils.status_transitions import GameStatus

pytestmark = pytest.mark.integration

JOINER_DISCORD_ID_SSE = "811111111111111101"


def _make_interaction(discord_user_id: str) -> MagicMock:
    interaction = MagicMock()
    interaction.user = MagicMock()
    interaction.user.id = int(discord_user_id)
    interaction.user.global_name = None
    interaction.user.name = f"TestUserSSE{discord_user_id[-4:]}"
    interaction.user.display_avatar = None
    interaction.user.send = AsyncMock()
    interaction.client = MagicMock(spec=discord.Client)
    interaction.response = MagicMock()
    interaction.response.is_done = MagicMock(return_value=False)
    interaction.response.defer = AsyncMock()
    return interaction


def _patch_db():
    def _bypass():
        return BotAsyncSessionLocal()

    return patch("services.bot.handlers.join_game.get_db_session", side_effect=_bypass)


@pytest.fixture(autouse=True)
async def _cleanup_engines():
    yield
    await bot_engine.dispose()


@pytest.fixture
def game_sse(create_guild, create_channel, create_user, create_game):
    """Game fixture for SSE pg_notify tests."""
    guild = create_guild(discord_guild_id="811000000000000001")
    channel = create_channel(guild_id=guild["id"], discord_channel_id="811000000000000002")
    host = create_user(discord_user_id="811000000000000003")
    game = create_game(
        guild_id=guild["id"],
        channel_id=channel["id"],
        host_id=host["id"],
        title="SSE Bot Notify Integration Test Game",
        status=GameStatus.SCHEDULED,
    )
    return {"guild": guild, "channel": channel, "host": host, "game": game}


@pytest.mark.asyncio
async def test_handle_join_game_fires_game_updated_sse_notify(
    game_sse,
    create_user,
    admin_db_sync,
):
    """handle_join_game emits pg_notify('game_updated_sse', ...) after a successful join."""
    game_id = game_sse["game"]["id"]
    guild_id = game_sse["guild"]["id"]

    create_user(discord_user_id=JOINER_DISCORD_ID_SSE)
    interaction = _make_interaction(JOINER_DISCORD_ID_SSE)

    received: list[dict] = []
    ready = asyncio.Event()

    pg_conn = await asyncpg.connect(BASE_DATABASE_URL)

    def _on_notify(_conn, _pid, _channel, payload: str) -> None:
        received.append(json.loads(payload))
        ready.set()

    await pg_conn.add_listener("game_updated_sse", _on_notify)

    try:
        with _patch_db():
            await handle_join_game(interaction, game_id)

        await asyncio.wait_for(ready.wait(), timeout=5.0)
    finally:
        await pg_conn.remove_listener("game_updated_sse", _on_notify)
        await pg_conn.close()

    assert len(received) >= 1, "No game_updated_sse notification received after join"
    game_notify = next(
        (n for n in received if n.get("game_id") == game_id),
        None,
    )
    assert game_notify is not None, (
        f"Expected game_updated_sse notify for game_id={game_id}, got: {received}"
    )
    assert game_notify["guild_id"] == guild_id
