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


"""End-to-end tests for game announcement Discord message validation.

Tests the complete flow:
1. POST /games → Bot posts announcement to Discord channel
2. Verification of Discord message content, embeds, fields
3. Updates and deletions reflect in Discord

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
async def test_game_creation_posts_announcement_to_discord(
    authenticated_admin_client,
    admin_db,
    discord_helper,
    discord_guild_id,
    discord_channel_id,
    discord_user_id,
    synced_guild,
    test_timeouts,
):
    """
    E2E: Creating game via API posts announcement to Discord channel.

    Verifies:
    - Message appears in configured channel
    - Game session has message_id populated
    - Message contains embed with correct content
    - Embed contains game details (title, host mention, player count)
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
    game_title = f"E2E Test Game {uuid4().hex[:8]}"
    game_data = {
        "template_id": test_template_id,
        "title": game_title,
        "description": "Testing game announcement to Discord",
        "scheduled_at": scheduled_time.isoformat(),
        "max_players": "4",
    }

    response = await authenticated_admin_client.post("/api/v1/games", data=game_data)
    assert response.status_code == 201, f"Failed to create game: {response.text}"
    game_id = response.json()["id"]
    print(f"\n[TEST] Game created with ID: {game_id}")

    message_id = await wait_for_game_message_id(
        admin_db, game_id, timeout=test_timeouts[TimeoutType.DB_WRITE]
    )

    print(f"[TEST] Database - message_id: {message_id}")
    print(f"[TEST] Expected Discord channel_id: {discord_channel_id}")
    assert message_id is not None, "Message ID should be populated after announcement"

    message = await discord_helper.get_message(discord_channel_id, message_id)
    print(f"[TEST] Discord message fetched: {message}")
    assert message is not None, "Discord message should exist"
    assert len(message.embeds) == 1, "Message should have exactly one embed"

    embed = message.embeds[0]
    discord_helper.verify_game_embed(
        embed=embed,
        expected_title=game_title,
        expected_host_id=discord_user_id,
        expected_max_players=4,
    )
