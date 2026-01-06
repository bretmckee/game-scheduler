# Copyright 2025 Bret McKee (bret.mckee@gmail.com)
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


"""End-to-end tests for user join Discord message update validation.

Tests the complete flow:
1. POST /games → Bot posts announcement to Discord channel
2. POST /games/{game_id}/join → User joins game
3. Verification that Discord message updates with incremented participant count

Requires:
- PostgreSQL with migrations applied and E2E data seeded by init service
- RabbitMQ with exchanges/queues configured
- Discord bot connected to test guild
- API service running on localhost:8000
- Full stack via compose.e2e.yaml profile

E2E data seeded by init service:
- Test guild configuration (from DISCORD_GUILD_ID)
- Test channel configuration (from DISCORD_CHANNEL_ID)

Note: Admin bot (from DISCORD_ADMIN_BOT_TOKEN) creates and joins the game in this test.
"""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import text

from tests.e2e.conftest import TimeoutType, wait_for_game_message_id

pytestmark = pytest.mark.e2e


@pytest.mark.asyncio
async def test_user_join_updates_participant_count(
    authenticated_admin_client,
    admin_db,
    discord_helper,
    discord_guild_id,
    discord_channel_id,
    bot_discord_id,
    synced_guild,
    test_timeouts,
):
    """
    E2E: Bot joining game via API updates Discord message participant count.

    Verifies:
    - Game created and message posted to Discord
    - Admin bot joins game via POST /games/{game_id}/join
    - Discord message updates with incremented participant count
    - Participant list shows joined bot
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
    game_title = f"E2E Join Test {uuid4().hex[:8]}"

    game_data = {
        "template_id": test_template_id,
        "title": game_title,
        "description": "Testing user join participant count update",
        "scheduled_at": scheduled_time.isoformat(),
        "max_players": "4",
    }

    response = await authenticated_admin_client.post("/api/v1/games", data=game_data)
    assert response.status_code == 201, f"Failed to create game: {response.text}"
    game_id = response.json()["id"]
    print(f"\n[TEST] Game created with ID: {game_id}")

    # Refresh the session to ensure we see committed data
    admin_db.expire_all()
    await admin_db.commit()

    # Check game and host details
    result = await admin_db.execute(
        text("SELECT id, host_id FROM game_sessions WHERE id = :game_id"),
        {"game_id": game_id},
    )
    game_row = result.fetchone()
    print(f"[DEBUG] Game found: {game_row is not None}")
    if game_row:
        print(f"[DEBUG] Game ID: {game_row[0]}")
        print(f"[DEBUG] Host ID: {game_row[1]}")

    # Check bot user details
    result = await admin_db.execute(
        text("SELECT id, discord_id FROM users WHERE discord_id = :discord_id"),
        {"discord_id": bot_discord_id},
    )
    bot_user = result.fetchone()
    print(f"[DEBUG] Bot user found: {bot_user is not None}")
    if bot_user:
        print(f"[DEBUG] Bot user_id: {bot_user[0]}")
        print(f"[DEBUG] Bot discord_id: {bot_user[1]}")
        if game_row:
            print(f"[DEBUG] Bot is host: {bot_user[0] == game_row[1]}")

    # Check ALL participants (including any with NULL user_id)
    result = await admin_db.execute(
        text(
            "SELECT id, game_session_id, user_id, display_name, position_type, position "
            "FROM game_participants WHERE game_session_id = :game_id"
        ),
        {"game_id": game_id},
    )
    all_participants = result.fetchall()
    print(f"[DEBUG] Total participants in game: {len(all_participants)}")
    for p in all_participants:
        print(
            f"[DEBUG]   Participant: id={p[0]}, game_id={p[1]}, user_id={p[2]}, "
            f"display_name={p[3]}, position_type={p[4]}, position={p[5]}"
        )

    # Check if bot already has a participant record
    if bot_user:
        result = await admin_db.execute(
            text(
                "SELECT id, game_session_id, user_id, display_name "
                "FROM game_participants WHERE user_id = :user_id"
            ),
            {"user_id": bot_user[0]},
        )
        bot_participants = result.fetchall()
        print(f"[DEBUG] Bot's participant records (all games): {len(bot_participants)}")
        for p in bot_participants:
            print(
                f"[DEBUG]   Bot participant: id={p[0]}, game_id={p[1]}, "
                f"user_id={p[2]}, display_name={p[3]}"
            )

    message_id = await wait_for_game_message_id(
        admin_db, game_id, timeout=test_timeouts[TimeoutType.DB_WRITE]
    )
    print(f"[TEST] Message ID: {message_id}")
    assert message_id is not None, "Message ID should be populated after announcement"

    initial_message = await discord_helper.wait_for_message(
        channel_id=discord_channel_id,
        message_id=message_id,
        timeout=test_timeouts[TimeoutType.MESSAGE_CREATE],
    )
    assert initial_message is not None, "Discord message should exist after creation"
    assert len(initial_message.embeds) == 1, "Message should have one embed"

    initial_embed = initial_message.embeds[0]
    participants_field = None
    for field in initial_embed.fields:
        if field.name and "Participants" in field.name:
            participants_field = field
            break

    assert participants_field is not None, "Participants field should exist"
    print(f"[TEST] Initial participant field: {participants_field.name}")
    assert "0/4" in participants_field.name, (
        f"Should show 0/4 participants: {participants_field.name}"
    )

    join_response = await authenticated_admin_client.post(f"/api/v1/games/{game_id}/join")
    assert join_response.status_code == 200, f"Failed to join game: {join_response.text}"
    print("[TEST] User joined game successfully")

    updated_message = await discord_helper.wait_for_message_update(
        channel_id=discord_channel_id,
        message_id=message_id,
        check_func=lambda msg: (
            msg.embeds
            and msg.embeds[0].fields
            and any("1/4" in field.name for field in msg.embeds[0].fields if field.name)
        ),
        timeout=test_timeouts[TimeoutType.MESSAGE_UPDATE],
        description="participant count update to 1/4",
    )
    assert updated_message is not None, "Discord message should be updated after join"
    assert len(updated_message.embeds) == 1, "Message should still have one embed"

    updated_embed = updated_message.embeds[0]
    updated_participants_field = None
    for field in updated_embed.fields:
        if field.name and "Participants" in field.name:
            updated_participants_field = field
            break

    assert updated_participants_field is not None, "Participants field should still exist"
    print(f"[TEST] Updated participant field: {updated_participants_field.name}")
    assert "1/4" in updated_participants_field.name, (
        f"Should show 1/4 participants after join: {updated_participants_field.name}"
    )
    print("[TEST] ✓ User join successfully updated Discord message")
