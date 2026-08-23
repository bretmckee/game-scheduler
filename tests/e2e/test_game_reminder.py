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


"""End-to-end tests for game reminder hybrid delivery verification.

Tests the complete flow:
1. POST /games with a single-channel location and reminder_minutes=[1]
   → Game scheduled 2 minutes in future
2. Notification daemon processes scheduled reminders
3. Discord bot posts one reminder message to the location channel,
   mentioning confirmed participants + host
4. Discord bot sends a reminder DM to the first waitlisted participant
5. Verification of both the channel post and the waitlist DM

Requires:
- PostgreSQL with migrations applied and E2E data seeded by init service
- RabbitMQ with exchanges/queues configured
- Discord bot connected to test guild
- Notification daemon running to process reminders
- API service running on localhost:8000
- Full stack via compose.e2e.yaml profile

E2E data seeded by init service:
- Test guild configuration (from DISCORD_GUILD_ID)
- Test channel configuration (from DISCORD_CHANNEL_ID)
- Test host user (from DISCORD_USER_ID)
"""

import json
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import text

from tests.e2e.conftest import (
    TimeoutType,
    wait_for_db_condition,
    wait_for_game_message_id,
)
from tests.e2e.helpers.discord import DMType

pytestmark = pytest.mark.e2e


@pytest.mark.timeout(240)
@pytest.mark.asyncio
async def test_game_reminder_hybrid_delivery(
    authenticated_admin_client,
    admin_db,
    main_bot_helper,
    discord_channel_id,
    discord_user_id,
    discord_player_a_id,
    discord_guild_id,
    synced_guild,
    test_timeouts,
):
    """
    E2E: Game reminder delivers a location-channel post plus waitlist DM.

    Verifies:
    - Game created with where=<#location channel>, max_players=1,
      Player A confirmed + test user waitlisted, reminder_minutes=[1]
    - Game scheduled 2 minutes in future
    - Notification daemon processes reminder schedule
    - Main bot posts one reminder embed to the location channel mentioning
      the confirmed participant (Player A)
    - Main bot sends a reminder DM to the first waitlisted participant
      (the test user)
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

    scheduled_time = datetime.now(UTC) + timedelta(minutes=2)
    game_title = f"E2E Reminder Test {uuid4().hex[:8]}"
    game_description = "Test game for DM reminder verification"

    # Player A is confirmed (slot 1 of max_players=1); the test user overflows
    # to waitlist and receives the reminder DM instead of a channel mention.
    game_data = {
        "template_id": test_template_id,
        "title": game_title,
        "description": game_description,
        "where": f"<#{discord_channel_id}>",
        "scheduled_at": scheduled_time.isoformat(),
        "max_players": "1",
        "reminder_minutes": json.dumps([1]),
        "initial_participants": json.dumps([f"<@{discord_player_a_id}>", f"<@{discord_user_id}>"]),
    }

    response = await authenticated_admin_client.post("/api/v1/games", data=game_data)
    assert response.status_code == 201, f"Failed to create game: {response.text}"
    game_id = response.json()["id"]
    print(f"\n[TEST] Game created with ID: {game_id}")
    print(f"[TEST] Game scheduled at: {scheduled_time.isoformat()}")
    print("[TEST] Reminder set for 1 minute before game")
    print(f"[TEST] Location channel: {discord_channel_id} (single <#id> mention)")
    print(f"[TEST] Player A confirmed (discord_id: {discord_player_a_id})")
    print(f"[TEST] Test user waitlisted (discord_id: {discord_user_id})")

    message_id = await wait_for_game_message_id(
        admin_db, game_id, timeout=test_timeouts[TimeoutType.DB_WRITE]
    )
    await main_bot_helper.wait_for_message(
        channel_id=discord_channel_id,
        message_id=message_id,
        timeout=test_timeouts[TimeoutType.MESSAGE_CREATE],
    )

    # Wait for reminder to be scheduled (may take a moment after game creation)
    row = await wait_for_db_condition(
        admin_db,
        "SELECT COUNT(*) FROM notification_schedule "
        "WHERE game_id = :game_id AND reminder_minutes = 1",
        {"game_id": game_id},
        lambda row: row[0] > 0,
        timeout=test_timeouts[TimeoutType.DB_WRITE],
        interval=1,
        description="reminder schedule creation",
    )
    reminder_count = row[0]
    print(f"[TEST] Reminder scheduled in database (count: {reminder_count})")

    # Wait for the reminder channel post in the location channel
    def is_reminder_post(msg) -> bool:
        return (
            msg.embeds
            and msg.embeds[0].title == "🔔 Game Reminder"
            and game_title in (msg.embeds[0].description or "")
        )

    reminder_post = await main_bot_helper.wait_for_channel_message(
        channel_id=discord_channel_id,
        predicate=is_reminder_post,
        timeout=test_timeouts[TimeoutType.DM_SCHEDULED],
        interval=5,
        description=f"reminder channel post for '{game_title}'",
    )

    assert f"<@{discord_player_a_id}>" in reminder_post.content, (
        f"Channel post should mention confirmed participant Player A; content: "
        f"{reminder_post.content!r}"
    )
    print("[TEST] ✓ Reminder posted to location channel with confirmed participant mentioned")
    print(f"[TEST] Post Content: {reminder_post.content}")

    # The waitlisted test user still receives a reminder DM
    reminder_dm = await main_bot_helper.wait_for_recent_dm(
        user_id=discord_user_id,
        game_title=game_title,
        dm_type=DMType.REMINDER,
        timeout=test_timeouts[TimeoutType.DM_SCHEDULED],
        interval=5,
    )

    print("[TEST] ✓ Waitlist reminder DM contains game title")
    print(f"[TEST] DM Content: {reminder_dm.content}")
    print("[TEST] ✓ Game reminder hybrid delivery verified successfully")
