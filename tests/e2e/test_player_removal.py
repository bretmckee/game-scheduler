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


"""End-to-end tests for player removal DM notification validation.

Tests the complete flow:
1. POST /games → Bot posts announcement to Discord channel
2. POST /games/{game_id}/join → User joins game
3. PUT /games/{game_id} with removed_participant_ids → Removes user from game
4. Verification that removed user receives DM notification
5. Verification that Discord message updates with decremented participant count

Requires:
- PostgreSQL with migrations applied and E2E data seeded by init service
- RabbitMQ with exchanges/queues configured
- Discord bot connected to test guild
- API service running on localhost:8000
- Full stack via compose.e2e.yaml profile

E2E data seeded by init service:
- Test guild configuration (from DISCORD_GUILD_ID)
- Test channel configuration (from DISCORD_CHANNEL_ID)
- Test user (from DISCORD_USER_ID) - needed for DM verification

Note: Admin bot (from DISCORD_ADMIN_BOT_TOKEN) creates game and removes test user.
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
async def test_player_removal_sends_dm_and_updates_message(
    authenticated_admin_client,
    admin_db,
    discord_helper,
    main_bot_helper,
    discord_guild_id,
    discord_channel_id,
    discord_user_id,
    bot_discord_id,
    synced_guild,
    test_timeouts,
):
    """
    E2E: Removing player from game sends DM and updates Discord message.

    Verifies:
    - Game created with test user as initial participant (via @mention)
    - Admin bot removes test user via PUT /games/{game_id}
    - PLAYER_REMOVED event published to RabbitMQ
    - Removed test user receives DM notification (via main bot)
    - Main bot can verify DM was sent
    - Discord message updates with decremented participant count
    - Removed user no longer appears in participant list

    Note: Uses main_bot_helper to verify DM delivery since bots cannot
    read DMs sent to other bots. Test user (DISCORD_USER_ID) is the
    participant being removed and receiving the DM.
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
    game_title = f"E2E Removal Test {uuid4().hex[:8]}"

    game_data = {
        "template_id": test_template_id,
        "title": game_title,
        "description": "Testing player removal DM and message update",
        "scheduled_at": scheduled_time.isoformat(),
        "max_players": "4",
        "initial_participants": json.dumps([f"<@{discord_user_id}>"]),
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

    await discord_helper.wait_for_message(
        channel_id=discord_channel_id,
        message_id=message_id,
        timeout=test_timeouts[TimeoutType.MESSAGE_CREATE],
    )

    result = await admin_db.execute(
        text("SELECT id FROM game_participants WHERE game_session_id = :game_id"),
        {"game_id": game_id},
    )
    row = result.fetchone()
    assert row is not None, "Participant not found in database"
    participant_id = row[0]
    print(f"[TEST] Participant ID: {participant_id}")

    verify_message = await discord_helper.get_message(discord_channel_id, message_id)
    assert verify_message is not None, "Discord message should exist"
    verify_embed = verify_message.embeds[0]

    verify_participants_field = None
    for field in verify_embed.fields:
        if field.name and "Participants" in field.name:
            verify_participants_field = field
            break

    assert verify_participants_field is not None, "Participants field should exist"
    assert "1/4" in verify_participants_field.name, (
        f"Should show 1/4 participants before removal: {verify_participants_field.name}"
    )
    assert f"<@{discord_user_id}>" in verify_participants_field.value, (
        "Test user should be in participant list before removal"
    )
    print("[TEST] Verified test user is participant (1/4)")

    update_data = {"removed_participant_ids": json.dumps([participant_id])}
    remove_response = await authenticated_admin_client.put(
        f"/api/v1/games/{game_id}",
        data=update_data,
    )
    assert remove_response.status_code == 200, (
        f"Failed to remove participant: {remove_response.text}"
    )
    print(f"[TEST] Removed participant {participant_id}")

    # Wait for PLAYER_REMOVED event to be processed and DM sent
    removal_dm = await main_bot_helper.wait_for_recent_dm(
        user_id=discord_user_id,
        game_title=game_title,
        dm_type=DMType.REMOVAL,
        timeout=test_timeouts[TimeoutType.DM_IMMEDIATE],
    )

    assert removal_dm is not None, (
        f"Test user should receive DM notification about removal from '{game_title}'. "
        f"Check bot logs for PLAYER_REMOVED event processing."
    )
    print(f"[TEST] ✓ Removal DM received: {removal_dm.content}")

    assert "❌" in removal_dm.content or "removed" in removal_dm.content.lower(), (
        f"DM should indicate removal: {removal_dm.content}"
    )
    assert game_title in removal_dm.content, f"DM should mention game title: {removal_dm.content}"

    updated_message = await discord_helper.wait_for_message_update(
        channel_id=discord_channel_id,
        message_id=message_id,
        check_func=lambda msg: (
            msg.embeds
            and any(
                "0/4" in field.name
                for field in msg.embeds[0].fields
                if field.name and "Participants" in field.name
            )
        ),
        timeout=test_timeouts[TimeoutType.MESSAGE_UPDATE] + 5,
        interval=2.0,
        description="message update to show 0/4 participants after removal",
    )
    assert updated_message is not None, "Discord message should still exist after removal"
    assert len(updated_message.embeds) == 1, "Message should have one embed"

    updated_embed = updated_message.embeds[0]
    updated_participants_field = None
    for field in updated_embed.fields:
        if field.name and "Participants" in field.name:
            updated_participants_field = field
            break

    assert updated_participants_field is not None, "Participants field should exist after removal"
    participant_list = updated_participants_field.value
    assert f"<@{discord_user_id}>" not in participant_list, (
        f"Removed user should not appear in participant list: {participant_list}"
    )

    print("[TEST] ✓ Discord message updated successfully (0/4 participants)")
    print("[TEST] ✓ Removed user no longer in participant list")
