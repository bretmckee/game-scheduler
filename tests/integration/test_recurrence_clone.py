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


"""Integration tests for recurring game clone lifecycle.

Tests already-implemented behaviour (retrofitting — no xfail markers needed).

Covered scenarios:
1. recur_rule is stored and returned in GET response
2. recur_rule is propagated through the clone endpoint
3. A clone with post_at=NULL is visible to both host and player via GET
4. PUT with clear_post_at=true on a post_at=NULL recurrence clone sets post_at
   and publishes GAME_CREATED to RabbitMQ
"""

import uuid
from datetime import UTC, datetime, timedelta

import httpx
import pytest
from sqlalchemy import text

from shared.utils.discord_tokens import extract_bot_discord_id
from tests.shared.auth_helpers import cleanup_test_session, create_test_session

pytestmark = pytest.mark.integration

HOST_DISCORD_TOKEN = "MTQ0NDA3ODM4NjM4MDAxMzY0OA.GvmbbW.fake_token_for_integration_tests"
HOST_DISCORD_ID = extract_bot_discord_id(HOST_DISCORD_TOKEN)

PLAYER_DISCORD_TOKEN = "MjAwMTAwMDAwMDAwMDAwMDAy.GvmbbW.fake_token_for_joiner_integration"
PLAYER_DISCORD_ID = extract_bot_discord_id(PLAYER_DISCORD_TOKEN)

BOT_MANAGER_ROLE_ID = "610999000000000001"
RECUR_RULE = "FREQ=WEEKLY;BYDAY=SA"


def _insert_game_with_recur_rule(
    admin_db_sync,
    guild_id: str,
    channel_id: str,
    host_id: str,
    recur_rule: str,
    post_at: datetime | None = None,
    message_id: str | None = None,
) -> str:
    """Insert a game row directly via admin session with recur_rule set."""
    game_id = str(uuid.uuid4())
    admin_db_sync.execute(
        text(
            "INSERT INTO game_sessions "
            "(id, guild_id, channel_id, host_id, title, description, "
            "scheduled_at, max_players, status, recur_rule, post_at, message_id, "
            "created_at, updated_at) "
            "VALUES (:id, :guild_id, :channel_id, :host_id, :title, :description, "
            ":scheduled_at, :max_players, :status, :recur_rule, :post_at, :message_id, "
            ":created_at, :updated_at)"
        ),
        {
            "id": game_id,
            "guild_id": guild_id,
            "channel_id": channel_id,
            "host_id": host_id,
            "title": "Recurrence Integration Test Game",
            "description": "Integration test game for recurrence lifecycle",
            "scheduled_at": datetime.now(UTC) + timedelta(hours=2),
            "max_players": 4,
            "status": "SCHEDULED",
            "recur_rule": recur_rule,
            "post_at": post_at,
            "message_id": message_id,
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
        },
    )
    admin_db_sync.commit()
    return game_id


@pytest.mark.asyncio
async def test_recur_rule_stored_and_returned(
    admin_db_sync,
    create_user,
    create_guild,
    create_channel,
    seed_redis_cache,
    api_base_url,
):
    """recur_rule inserted in DB is returned verbatim in GET /api/v1/games/{id}."""
    guild = create_guild(
        discord_guild_id="610111111111111101",
        bot_manager_roles=[BOT_MANAGER_ROLE_ID],
    )
    channel = create_channel(guild_id=guild["id"], discord_channel_id="610222222222222201")
    host = create_user(discord_user_id=HOST_DISCORD_ID)

    game_id = _insert_game_with_recur_rule(
        admin_db_sync,
        guild_id=guild["id"],
        channel_id=channel["id"],
        host_id=host["id"],
        recur_rule=RECUR_RULE,
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
            response = await client.get(f"/api/v1/games/{game_id}")

        assert response.status_code == 200, (
            f"Expected 200, got {response.status_code}: {response.text}"
        )
        data = response.json()
        assert data["recur_rule"] == RECUR_RULE, (
            f"Expected recur_rule={RECUR_RULE!r}, got {data.get('recur_rule')!r}"
        )
    finally:
        await cleanup_test_session(session_token)


@pytest.mark.asyncio
async def test_recur_rule_propagated_through_clone_endpoint(
    admin_db_sync,
    create_user,
    create_guild,
    create_channel,
    seed_redis_cache,
    api_base_url,
):
    """POST /api/v1/games/{id}/clone on a game with recur_rule returns clone with recur_rule set."""
    guild = create_guild(
        discord_guild_id="610111111111111102",
        bot_manager_roles=[BOT_MANAGER_ROLE_ID],
    )
    channel = create_channel(guild_id=guild["id"], discord_channel_id="610222222222222202")
    host = create_user(discord_user_id=HOST_DISCORD_ID)

    source_id = _insert_game_with_recur_rule(
        admin_db_sync,
        guild_id=guild["id"],
        channel_id=channel["id"],
        host_id=host["id"],
        recur_rule=RECUR_RULE,
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
            clone_at = (datetime.now(UTC) + timedelta(days=7)).isoformat()
            response = await client.post(
                f"/api/v1/games/{source_id}/clone",
                json={
                    "scheduled_at": clone_at,
                    "player_carryover": "NO",
                    "waitlist_carryover": "NO",
                },
            )

        assert response.status_code == 201, (
            f"Expected 201, got {response.status_code}: {response.text}"
        )
        data = response.json()
        assert data["recur_rule"] == RECUR_RULE, (
            f"Clone recur_rule must match source; got {data.get('recur_rule')!r}"
        )
    finally:
        await cleanup_test_session(session_token)


@pytest.mark.asyncio
async def test_recurrence_clone_with_null_post_at_is_visible(
    admin_db_sync,
    create_user,
    create_guild,
    create_channel,
    seed_redis_cache,
    api_base_url,
):
    """A clone with post_at=NULL is visible to both host and regular player via GET /api/v1/games.

    post_at=NULL clones are NOT pending-announcement games (which require post_at > now).
    They are regular SCHEDULED games visible to all guild members.
    """
    guild = create_guild(
        discord_guild_id="610111111111111103",
        bot_manager_roles=[BOT_MANAGER_ROLE_ID],
    )
    channel = create_channel(guild_id=guild["id"], discord_channel_id="610222222222222203")
    host = create_user(discord_user_id=HOST_DISCORD_ID)
    create_user(discord_user_id=PLAYER_DISCORD_ID)

    clone_id = _insert_game_with_recur_rule(
        admin_db_sync,
        guild_id=guild["id"],
        channel_id=channel["id"],
        host_id=host["id"],
        recur_rule=RECUR_RULE,
        post_at=None,
        message_id=None,
    )

    # Seed Redis for host (bot manager)
    await seed_redis_cache(
        user_discord_id=HOST_DISCORD_ID,
        guild_discord_id=guild["guild_id"],
        channel_discord_id=channel["channel_id"],
        user_roles=[BOT_MANAGER_ROLE_ID],
    )
    host_token, _ = await create_test_session(HOST_DISCORD_TOKEN, HOST_DISCORD_ID)

    # Seed Redis for regular player (no bot manager role)
    await seed_redis_cache(
        user_discord_id=PLAYER_DISCORD_ID,
        guild_discord_id=guild["guild_id"],
        channel_discord_id=channel["channel_id"],
        user_roles=[],
    )
    player_token, _ = await create_test_session(PLAYER_DISCORD_TOKEN, PLAYER_DISCORD_ID)

    try:
        async with httpx.AsyncClient(
            base_url=api_base_url,
            timeout=10.0,
            cookies={"session_token": host_token},
        ) as client:
            host_response = await client.get(
                "/api/v1/games",
                params={"guild_id": guild["id"]},
            )

        assert host_response.status_code == 200, (
            f"Host GET failed: {host_response.status_code}: {host_response.text}"
        )
        host_game_ids = [g["id"] for g in host_response.json().get("games", [])]
        assert clone_id in host_game_ids, "post_at=NULL clone must be visible to host"

        async with httpx.AsyncClient(
            base_url=api_base_url,
            timeout=10.0,
            cookies={"session_token": player_token},
        ) as client:
            player_response = await client.get(
                "/api/v1/games",
                params={"guild_id": guild["id"]},
            )

        assert player_response.status_code == 200, (
            f"Player GET failed: {player_response.status_code}: {player_response.text}"
        )
        player_game_ids = [g["id"] for g in player_response.json().get("games", [])]
        assert clone_id in player_game_ids, (
            "post_at=NULL clone must be visible to regular player (not a pending-announcement game)"
        )
    finally:
        await cleanup_test_session(host_token)
        await cleanup_test_session(player_token)


@pytest.mark.asyncio
async def test_clear_post_at_announces_recurrence_clone(
    admin_db_sync,
    create_user,
    create_guild,
    create_channel,
    seed_redis_cache,
    api_base_url,
):
    """PUT /{clone_id} with clear_post_at=true on a post_at=NULL recurrence clone sets post_at
    and enqueues a game_created row in bot_action_queue."""
    guild = create_guild(
        discord_guild_id="610111111111111104",
        bot_manager_roles=[BOT_MANAGER_ROLE_ID],
    )
    channel = create_channel(guild_id=guild["id"], discord_channel_id="610222222222222204")
    host = create_user(discord_user_id=HOST_DISCORD_ID)

    clone_id = _insert_game_with_recur_rule(
        admin_db_sync,
        guild_id=guild["id"],
        channel_id=channel["id"],
        host_id=host["id"],
        recur_rule=RECUR_RULE,
        post_at=None,
        message_id=None,
    )

    await seed_redis_cache(
        user_discord_id=HOST_DISCORD_ID,
        guild_discord_id=guild["guild_id"],
        channel_discord_id=channel["channel_id"],
        user_roles=[BOT_MANAGER_ROLE_ID],
    )
    session_token, _ = await create_test_session(HOST_DISCORD_TOKEN, HOST_DISCORD_ID)

    before = datetime.now(UTC).replace(tzinfo=None)

    try:
        async with httpx.AsyncClient(
            base_url=api_base_url,
            timeout=10.0,
            cookies={"session_token": session_token},
        ) as client:
            response = await client.put(
                f"/api/v1/games/{clone_id}",
                data={"clear_post_at": "true"},
            )

        after = datetime.now(UTC).replace(tzinfo=None)

        assert response.status_code == 200, (
            f"Expected 200, got {response.status_code}: {response.text}"
        )
        data = response.json()
        assert data["post_at"] is not None, (
            "post_at must be set after clear_post_at=true on recurrence clone"
        )
        post_at_dt = datetime.fromisoformat(data["post_at"].replace("Z", "+00:00")).replace(
            tzinfo=None
        )
        assert before <= post_at_dt <= after + timedelta(seconds=5), (
            f"post_at={data['post_at']!r} must be approximately now"
        )

        bot_row = admin_db_sync.execute(
            text(
                "SELECT action_type, game_id FROM bot_action_queue "
                "WHERE action_type = 'game_created' AND game_id = :game_id"
            ),
            {"game_id": clone_id},
        ).fetchone()

        assert bot_row is not None, "GAME_CREATED must be enqueued in bot_action_queue"
        assert bot_row[1] == clone_id, (
            "bot_action_queue must reference the recurrence clone game ID"
        )
    finally:
        await cleanup_test_session(session_token)
