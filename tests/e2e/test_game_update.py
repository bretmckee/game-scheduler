# Copyright 2025-2026 Bret McKee
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


"""End-to-end tests for game update Discord message refresh validation.

Tests the complete flow:
1. POST /games → Bot posts announcement to Discord channel
2. PUT /games/{game_id} → Bot edits Discord message with new content
3. Verification that message_id unchanged, content updated

Requires:
- PostgreSQL with migrations applied and E2E data seeded by init service
- RabbitMQ with exchanges/queues configured
- Discord bot connected to test guild
- API service running on localhost:8000
- Full stack via compose.e2e.yaml profile

E2E data seeded by init service:
- Test guild configuration (from DISCORD_GUILD_ID)
- Test channel configuration (from DISCORD_CHANNEL_ID)
- Test host user (from DISCORD_USER_ID)
"""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import text

from tests.e2e.conftest import TimeoutType, wait_for_game_message_id

pytestmark = pytest.mark.e2e


@pytest.mark.asyncio
async def test_game_update_refreshes_message(
    authenticated_admin_client,
    admin_db,
    discord_helper,
    discord_channel_id,
    discord_user_id,
    discord_guild_id,
    synced_guild,
    test_timeouts,
):
    """
    E2E: Updating game via API refreshes Discord message with new content.

    Verifies:
    - Game created and message posted to Discord
    - Game updated via PUT /games/{game_id}
    - message_id remains unchanged
    - Discord message content reflects updated title and description
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
    original_title = f"E2E Update Test {uuid4().hex[:8]}"
    original_description = "Original game description"

    game_data = {
        "template_id": test_template_id,
        "title": original_title,
        "description": original_description,
        "scheduled_at": scheduled_time.isoformat(),
        "max_players": "4",
    }

    response = await authenticated_admin_client.post("/api/v1/games", data=game_data)
    assert response.status_code == 201, f"Failed to create game: {response.text}"
    game_id = response.json()["id"]
    print(f"\n[TEST] Game created with ID: {game_id}")

    original_message_id = await wait_for_game_message_id(
        admin_db, game_id, timeout=test_timeouts[TimeoutType.DB_WRITE]
    )
    print(f"[TEST] Original message_id: {original_message_id}")
    assert original_message_id is not None, "Message ID should be populated after announcement"

    message = await discord_helper.wait_for_message(
        channel_id=discord_channel_id,
        message_id=original_message_id,
        timeout=test_timeouts[TimeoutType.MESSAGE_CREATE],
    )
    assert message is not None, "Discord message should exist after creation"
    assert len(message.embeds) == 1, "Message should have one embed"
    original_embed = message.embeds[0]
    assert original_embed.title == original_title, "Embed should have original title"

    updated_title = f"Updated Title {uuid4().hex[:8]}"
    updated_description = "Updated game description with new information"

    update_data = {
        "title": updated_title,
        "description": updated_description,
    }

    update_response = await authenticated_admin_client.put(
        f"/api/v1/games/{game_id}", data=update_data
    )
    assert update_response.status_code == 200, f"Failed to update game: {update_response.text}"
    print("[TEST] Game updated successfully")

    result = await admin_db.execute(
        text("SELECT message_id FROM game_sessions WHERE id = :game_id"),
        {"game_id": game_id},
    )
    row = result.fetchone()
    assert row is not None, "Game session not found after update"
    updated_message_id = row[0]
    print(f"[TEST] Updated message_id: {updated_message_id}")

    assert updated_message_id == original_message_id, (
        "message_id should remain unchanged after update"
    )

    updated_message = await discord_helper.wait_for_message_update(
        channel_id=discord_channel_id,
        message_id=updated_message_id,
        check_func=lambda msg: msg.embeds and msg.embeds[0].title == updated_title,
        timeout=test_timeouts[TimeoutType.MESSAGE_UPDATE],
        description="game title update",
    )
    assert updated_message is not None, "Discord message should still exist after update"
    assert len(updated_message.embeds) == 1, "Message should have one embed after update"

    updated_embed = updated_message.embeds[0]
    assert updated_embed.title == updated_title, (
        f"Embed title should be updated to '{updated_title}'"
    )
    assert updated_description in updated_embed.description, (
        f"Embed description should contain '{updated_description}'"
    )

    discord_helper.verify_game_embed(
        embed=updated_embed,
        expected_title=updated_title,
        expected_host_id=discord_user_id,
        expected_max_players=4,
    )

    print("[TEST] ✓ Message refreshed successfully with updated content")
