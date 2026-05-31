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


"""End-to-end tests for HOST_ADDED dropout host DM notification.

Tests the complete flow via the API leave path:
1. Admin creates game with discord_user_id as host and Player A as HOST_ADDED participant
2. Player A calls POST /api/v1/games/{id}/leave
3. NOTIFICATION_SEND_DM event published to RabbitMQ
4. Main bot processes event and sends DM to host (discord_user_id)
5. main_bot_helper verifies host received HOST_ADDED_DROPOUT DM

Requires:
- PostgreSQL with migrations applied and E2E data seeded by init service
- RabbitMQ with exchanges/queues configured
- Discord bot connected to test guild
- API service running on localhost:8000
- Full stack via compose.e2e.yaml profile

E2E data seeded by init service:
- Test guild configuration (from DISCORD_GUILD_ID)
- Test channel configuration (from DISCORD_CHANNEL_ID)
- Test user (from DISCORD_USER_ID) — used as game host for DM verification

Note: Admin bot (from DISCORD_ADMIN_BOT_TOKEN) creates the game.
      Player A bot (from DISCORD_PLAYER_A_TOKEN) is the HOST_ADDED participant that leaves.
      DM is sent to discord_user_id (DISCORD_USER_ID) — the game host.
"""

import json
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import text

from tests.e2e.conftest import TimeoutType, wait_for_game_message_id
from tests.e2e.helpers.discord import DMType

pytestmark = pytest.mark.e2e


@pytest.mark.asyncio
async def test_host_added_dropout_sends_dm_to_host(
    authenticated_admin_client,
    authenticated_player_a_client,
    admin_db,
    main_bot_helper,
    discord_guild_id,
    discord_user_id,
    discord_player_a_id,
    synced_guild,
    test_timeouts,
):
    """
    E2E: HOST_ADDED participant leaving via API sends DM to host.

    Verifies:
    - Admin creates game with discord_user_id as host and Player A as HOST_ADDED participant
    - Player A leaves via POST /api/v1/games/{game_id}/leave
    - NOTIFICATION_SEND_DM event published to RabbitMQ
    - Main bot delivers HOST_ADDED_DROPOUT DM to host (discord_user_id)
    - DM content matches HOST_ADDED_DROPOUT format
    """
    result = await admin_db.execute(
        text("SELECT id FROM guild_configurations WHERE guild_id = :guild_id"),
        {"guild_id": discord_guild_id},
    )
    row = result.fetchone()
    assert row, f"Test guild {discord_guild_id} not found"
    test_guild_id = row[0]

    result = await admin_db.execute(
        text("SELECT id FROM game_templates WHERE guild_id = :guild_id AND is_default = true"),
        {"guild_id": test_guild_id},
    )
    row = result.fetchone()
    assert row, f"Default template not found for guild {test_guild_id}"
    test_template_id = row[0]

    scheduled_time = datetime.now(UTC) + timedelta(hours=2)
    game_title = f"E2E Host Dropout Test {uuid4().hex[:8]}"

    game_data = {
        "template_id": test_template_id,
        "title": game_title,
        "description": "Testing HOST_ADDED dropout DM notification to host",
        "scheduled_at": scheduled_time.isoformat(),
        "max_players": "4",
        "host": f"<@{discord_user_id}>",
        "initial_participants": json.dumps([f"<@{discord_player_a_id}>"]),
    }

    response = await authenticated_admin_client.post("/api/v1/games", data=game_data)
    assert response.status_code == 201, f"Failed to create game: {response.text}"
    game_id = response.json()["id"]
    print(f"\n[TEST] Game created with ID: {game_id}")

    message_id = await wait_for_game_message_id(
        admin_db, game_id, timeout=test_timeouts[TimeoutType.DB_WRITE]
    )
    print(f"[TEST] Message ID: {message_id}")
    assert message_id is not None, "Message ID should be populated after announcement"

    leave_response = await authenticated_player_a_client.post(f"/api/v1/games/{game_id}/leave")
    assert leave_response.status_code == 204, f"Player A failed to leave: {leave_response.text}"
    print("[TEST] Player A left the game")

    dropout_dm = await main_bot_helper.wait_for_recent_dm(
        user_id=discord_user_id,
        game_title=game_title,
        dm_type=DMType.HOST_ADDED_DROPOUT,
        timeout=test_timeouts[TimeoutType.DM_IMMEDIATE],
    )

    assert dropout_dm is not None, (
        f"Host should receive HOST_ADDED_DROPOUT DM for '{game_title}'. "
        "Check bot logs for NOTIFICATION_SEND_DM event processing."
    )
    print(f"[TEST] ✓ HOST_ADDED_DROPOUT DM received: {dropout_dm.content}")

    assert "dropped out" in dropout_dm.content, f"DM should indicate dropout: {dropout_dm.content}"
    assert "who you added" in dropout_dm.content, (
        f"DM should indicate HOST_ADDED participant: {dropout_dm.content}"
    )
    assert game_title in dropout_dm.content, f"DM should mention game title: {dropout_dm.content}"
