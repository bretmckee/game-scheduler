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


"""Integration tests for Flow 2: game cancellation enqueues a bot_action_queue row.

Calls DELETE /api/v1/games/{id} via an authenticated HTTP client and asserts
that a 'game_cancelled' row appears in bot_action_queue with the correct game_id.
"""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import text

from shared.utils.discord_tokens import extract_bot_discord_id

pytestmark = pytest.mark.integration

TEST_DISCORD_TOKEN = "MTQ0NDA3ODM4NjM4MDAxMzY0OA.GvmbbW.fake_token_for_integration_tests"
TEST_BOT_DISCORD_ID = extract_bot_discord_id(TEST_DISCORD_TOKEN)
BOT_MANAGER_ROLE_ID = "919283746501928374"


def _make_context(create_guild, create_channel, create_user, create_template, seed_redis_cache):
    guild_discord_id = "651234567890123456"
    channel_discord_id = "651234567890123457"

    guild = create_guild(discord_guild_id=guild_discord_id, bot_manager_roles=[BOT_MANAGER_ROLE_ID])
    channel = create_channel(guild_id=guild["id"], discord_channel_id=channel_discord_id)
    create_user(discord_user_id=TEST_BOT_DISCORD_ID)
    template = create_template(guild_id=guild["id"], channel_id=channel["id"])

    seed_redis_cache(
        user_discord_id=TEST_BOT_DISCORD_ID,
        guild_discord_id=guild_discord_id,
        channel_discord_id=channel_discord_id,
        user_roles=[BOT_MANAGER_ROLE_ID, guild_discord_id],
        bot_manager_roles=[BOT_MANAGER_ROLE_ID],
    )

    return {"guild_discord_id": guild_discord_id, "template_id": template["id"]}


def test_delete_game_enqueues_game_cancelled_row(
    admin_db_sync,
    create_user,
    create_guild,
    create_channel,
    create_template,
    seed_redis_cache,
    create_authenticated_client,
):
    """DELETE /api/v1/games/{id} creates a game_cancelled row in bot_action_queue."""
    ctx = _make_context(
        create_guild, create_channel, create_user, create_template, seed_redis_cache
    )
    client = create_authenticated_client(TEST_DISCORD_TOKEN, TEST_BOT_DISCORD_ID)

    scheduled_at = (datetime.now(UTC) + timedelta(days=1)).isoformat()
    create_resp = client.post(
        "/api/v1/games",
        data={
            "template_id": ctx["template_id"],
            "title": "INT_TEST Cancel Queue Game",
            "scheduled_at": scheduled_at,
        },
    )
    assert create_resp.status_code in (200, 201), f"Create failed: {create_resp.text}"
    game_id = create_resp.json()["id"]

    delete_resp = client.delete(f"/api/v1/games/{game_id}")
    assert delete_resp.status_code == 204, f"Delete failed: {delete_resp.text}"

    game_row = admin_db_sync.execute(
        text("SELECT id FROM game_sessions WHERE id = :id"),
        {"id": game_id},
    ).fetchone()
    assert game_row is None, "Game row must be deleted after DELETE"

    queue_row = admin_db_sync.execute(
        text(
            "SELECT action_type, game_id FROM bot_action_queue "
            "WHERE action_type = 'game_cancelled' AND game_id = :game_id"
        ),
        {"game_id": game_id},
    ).fetchone()
    assert queue_row is not None, "No game_cancelled row found in bot_action_queue"
    assert queue_row[1] == game_id
