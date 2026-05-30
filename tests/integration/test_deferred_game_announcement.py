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


"""Integration tests for join_game and list_games guards on pre-announced games.

Tests that the API-level guards added in Phase 3 (Tasks 3.3 and 3.4) behave
correctly end-to-end: pending-announcement games are hidden from non-managers
in list and blocked from join until the bot posts the announcement message.
"""

import uuid
from datetime import UTC, datetime, timedelta

import httpx
import pytest
from sqlalchemy import text

from shared.utils.discord_tokens import extract_bot_discord_id
from tests.shared.auth_helpers import cleanup_test_session, create_test_session

pytestmark = pytest.mark.integration

# Bot Manager user — has the Bot Manager role and therefore can see pending games
HOST_DISCORD_TOKEN = "MTQ0NDA3ODM4NjM4MDAxMzY0OA.GvmbbW.fake_token_for_integration_tests"
HOST_DISCORD_ID = extract_bot_discord_id(HOST_DISCORD_TOKEN)

# Non-manager user — guild member but no Bot Manager role
JOINER_DISCORD_ID = "600100000000000002"
JOINER_DISCORD_TOKEN = "MjAwMTAwMDAwMDAwMDAwMDAy.GvmbbW.fake_token_for_joiner_integration"

BOT_MANAGER_ROLE_ID = "600999000000000001"


def _insert_game_with_post_at(
    admin_db_sync,
    guild_id: str,
    channel_id: str,
    host_id: str,
    post_at: datetime,
    message_id: str | None = None,
) -> str:
    """Insert a game row directly via admin session with post_at and optional message_id."""
    game_id = str(uuid.uuid4())
    admin_db_sync.execute(
        text(
            "INSERT INTO game_sessions "
            "(id, guild_id, channel_id, host_id, title, description, "
            "scheduled_at, max_players, status, post_at, message_id, created_at, updated_at) "
            "VALUES (:id, :guild_id, :channel_id, :host_id, :title, :description, "
            ":scheduled_at, :max_players, :status, :post_at, :message_id, :created_at, :updated_at)"
        ),
        {
            "id": game_id,
            "guild_id": guild_id,
            "channel_id": channel_id,
            "host_id": host_id,
            "title": "Deferred Announcement Test Game",
            "description": "Test game for deferred announcement integration tests",
            "scheduled_at": datetime.now(UTC) + timedelta(hours=2),
            "max_players": 4,
            "status": "SCHEDULED",
            "post_at": post_at,
            "message_id": message_id,
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
        },
    )
    admin_db_sync.commit()
    return game_id


@pytest.mark.asyncio
async def test_join_game_returns_404_for_pending_announcement(
    admin_db_sync,
    create_user,
    create_guild,
    create_channel,
    seed_redis_cache,
    api_base_url,
):
    """POST /api/v1/games/{id}/join returns 404 when game has future post_at and no message_id."""
    guild = create_guild(
        discord_guild_id="600111111111111111",
        bot_manager_roles=[BOT_MANAGER_ROLE_ID],
    )
    channel = create_channel(guild_id=guild["id"], discord_channel_id="600222222222222221")
    host = create_user(discord_user_id=HOST_DISCORD_ID)
    create_user(discord_user_id=JOINER_DISCORD_ID)

    game_id = _insert_game_with_post_at(
        admin_db_sync,
        guild_id=guild["id"],
        channel_id=channel["id"],
        host_id=host["id"],
        post_at=datetime.now(UTC) + timedelta(hours=1),
        message_id=None,
    )

    await seed_redis_cache(
        user_discord_id=JOINER_DISCORD_ID,
        guild_discord_id=guild["guild_id"],
        channel_discord_id=channel["channel_id"],
        user_roles=[],
    )
    session_token, _ = await create_test_session(JOINER_DISCORD_TOKEN, JOINER_DISCORD_ID)

    try:
        async with httpx.AsyncClient(
            base_url=api_base_url,
            timeout=10.0,
            cookies={"session_token": session_token},
        ) as client:
            response = await client.post(f"/api/v1/games/{game_id}/join")

        assert response.status_code == 404, (
            f"Expected 404 for pending-announcement game, "
            f"got {response.status_code}: {response.text}"
        )
    finally:
        await cleanup_test_session(session_token)


@pytest.mark.asyncio
async def test_join_game_succeeds_after_announcement_posted(
    admin_db_sync,
    create_user,
    create_guild,
    create_channel,
    seed_redis_cache,
    api_base_url,
):
    """POST /api/v1/games/{id}/join succeeds when game has message_id set (already announced)."""
    guild = create_guild(
        discord_guild_id="600111111111111112",
        bot_manager_roles=[BOT_MANAGER_ROLE_ID],
    )
    channel = create_channel(guild_id=guild["id"], discord_channel_id="600222222222222222")
    host = create_user(discord_user_id=HOST_DISCORD_ID)
    create_user(discord_user_id=JOINER_DISCORD_ID)

    game_id = _insert_game_with_post_at(
        admin_db_sync,
        guild_id=guild["id"],
        channel_id=channel["id"],
        host_id=host["id"],
        post_at=datetime.now(UTC) + timedelta(hours=1),
        message_id="123456789012345678",
    )

    await seed_redis_cache(
        user_discord_id=JOINER_DISCORD_ID,
        guild_discord_id=guild["guild_id"],
        channel_discord_id=channel["channel_id"],
        user_roles=[],
    )
    session_token, _ = await create_test_session(JOINER_DISCORD_TOKEN, JOINER_DISCORD_ID)

    try:
        async with httpx.AsyncClient(
            base_url=api_base_url,
            timeout=10.0,
            cookies={"session_token": session_token},
        ) as client:
            response = await client.post(f"/api/v1/games/{game_id}/join")

        assert response.status_code == 200, (
            f"Expected 200 for announced game join, got {response.status_code}: {response.text}"
        )
        data = response.json()
        assert data["discord_id"] == JOINER_DISCORD_ID
    finally:
        await cleanup_test_session(session_token)


@pytest.mark.asyncio
async def test_list_games_hides_pending_from_non_manager(
    admin_db_sync,
    create_user,
    create_guild,
    create_channel,
    seed_redis_cache,
    api_base_url,
):
    """GET /api/v1/games excludes pending-announcement games for non-managers."""
    guild = create_guild(
        discord_guild_id="600111111111111113",
        bot_manager_roles=[BOT_MANAGER_ROLE_ID],
    )
    channel = create_channel(guild_id=guild["id"], discord_channel_id="600222222222222223")
    host = create_user(discord_user_id=HOST_DISCORD_ID)
    create_user(discord_user_id=JOINER_DISCORD_ID)

    game_id = _insert_game_with_post_at(
        admin_db_sync,
        guild_id=guild["id"],
        channel_id=channel["id"],
        host_id=host["id"],
        post_at=datetime.now(UTC) + timedelta(hours=1),
        message_id=None,
    )

    await seed_redis_cache(
        user_discord_id=JOINER_DISCORD_ID,
        guild_discord_id=guild["guild_id"],
        channel_discord_id=channel["channel_id"],
        user_roles=[],
    )
    session_token, _ = await create_test_session(JOINER_DISCORD_TOKEN, JOINER_DISCORD_ID)

    try:
        async with httpx.AsyncClient(
            base_url=api_base_url,
            timeout=10.0,
            cookies={"session_token": session_token},
        ) as client:
            response = await client.get(
                "/api/v1/games",
                params={"guild_id": guild["id"]},
            )

        assert response.status_code == 200, (
            f"Expected 200, got {response.status_code}: {response.text}"
        )
        data = response.json()
        game_ids = [g["id"] for g in data.get("games", [])]
        assert game_id not in game_ids, (
            "Pending-announcement game should not appear for non-manager"
        )
    finally:
        await cleanup_test_session(session_token)


@pytest.mark.asyncio
async def test_list_games_shows_pending_to_host(
    admin_db_sync,
    create_user,
    create_guild,
    create_channel,
    seed_redis_cache,
    api_base_url,
):
    """GET /api/v1/games includes pending-announcement games for the game host."""
    guild = create_guild(
        discord_guild_id="600111111111111114",
        bot_manager_roles=[BOT_MANAGER_ROLE_ID],
    )
    channel = create_channel(guild_id=guild["id"], discord_channel_id="600222222222222224")
    host = create_user(discord_user_id=HOST_DISCORD_ID)

    game_id = _insert_game_with_post_at(
        admin_db_sync,
        guild_id=guild["id"],
        channel_id=channel["id"],
        host_id=host["id"],
        post_at=datetime.now(UTC) + timedelta(hours=1),
        message_id=None,
    )

    await seed_redis_cache(
        user_discord_id=HOST_DISCORD_ID,
        guild_discord_id=guild["guild_id"],
        channel_discord_id=channel["channel_id"],
        user_roles=[BOT_MANAGER_ROLE_ID],
    )
    session_token, _ = await create_test_session(HOST_DISCORD_TOKEN, HOST_DISCORD_ID)

    try:
        async with httpx.AsyncClient(
            base_url=api_base_url,
            timeout=10.0,
            cookies={"session_token": session_token},
        ) as client:
            response = await client.get(
                "/api/v1/games",
                params={"guild_id": guild["id"]},
            )

        assert response.status_code == 200, (
            f"Expected 200, got {response.status_code}: {response.text}"
        )
        data = response.json()
        game_ids = [g["id"] for g in data.get("games", [])]
        assert game_id in game_ids, "Pending-announcement game should appear for the game host"
    finally:
        await cleanup_test_session(session_token)
