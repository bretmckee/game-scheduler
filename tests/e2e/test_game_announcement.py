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

import json
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import text

from services.bot.formatters.game_message import _PARTICIPANT_COLUMNS, _WAITLIST_COLUMNS
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
    - Embed contains game details (title, host mention, player count, location)
    - Plain text location displays unchanged in Discord embed
    - Links field contains the calendar download URL and the Google Calendar
      quick-add URL for this game
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
    game_location = "Local Game Store, 123 Main St"
    game_data = {
        "template_id": test_template_id,
        "title": game_title,
        "description": "Testing game announcement to Discord",
        "scheduled_at": scheduled_time.isoformat(),
        "max_players": "4",
        "where": game_location,
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
        expected_location=game_location,
        expected_game_id=game_id,
    )


@pytest.mark.asyncio
async def test_game_with_large_waitlist_shows_contiguous_columns(
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
    E2E: A waitlist bigger than max_players renders as contiguous columns.

    Verifies:
    - Players field always spans `_PARTICIPANT_COLUMNS` side-by-side
      columns, matching the waitlist row's width below it (Discord sizes
      inline fields by how many share a row, not by their content, so
      mismatched column counts would make the two rows different widths)
    - Waitlist field spans `_WAITLIST_COLUMNS` side-by-side columns once
      there's overflow
    - Waitlist numbering starts at 1 (does not continue from player count)
    - Waitlist entries are distributed as contiguous chunks (column 1:
      positions 1-3; column 2: positions 4-6; column 3: position 7) rather
      than row-major/interleaved, since Discord's mobile client stacks each
      column as a full field one after another instead of gridding them
      side by side like desktop, which would turn an interleaved split
      (column 1: 1, 4, 7) into a nonsensical reading order.
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
    game_title = f"E2E Waitlist Columns {uuid4().hex[:8]}"

    # First 2 names fill max_players=2; the remaining 7 placeholders overflow
    # onto the waitlist, which is enough to populate all _WAITLIST_COLUMNS
    # columns unevenly (column 1 gets positions 1-3, column 2 gets 4-6,
    # column 3 gets 7).
    waitlist_names = [f"Waitlist {i}" for i in range(1, 8)]
    game_data = {
        "template_id": test_template_id,
        "title": game_title,
        "description": "Testing waitlist contiguous column layout",
        "scheduled_at": scheduled_time.isoformat(),
        "max_players": "2",
        "initial_participants": json.dumps(["Player A", "Player B", *waitlist_names]),
    }

    response = await authenticated_admin_client.post("/api/v1/games", data=game_data)
    assert response.status_code == 201, f"Failed to create game: {response.text}"
    game_id = response.json()["id"]
    print(f"✓ Created game {game_id} with 2 confirmed + 7 waitlisted placeholders")

    message_id = await wait_for_game_message_id(
        admin_db, game_id, timeout=test_timeouts[TimeoutType.DB_WRITE]
    )
    assert message_id is not None, "Message ID should be populated after announcement"

    message = await discord_helper.get_message(discord_channel_id, message_id)
    assert message is not None, "Discord message should exist"
    assert len(message.embeds) == 1, "Message should have exactly one embed"
    embed = message.embeds[0]

    # Baseline structural/numbering checks shared with every announcement test.
    discord_helper.verify_game_embed(
        embed=embed,
        expected_title=game_title,
        expected_host_id=discord_user_id,
        expected_max_players=2,
    )

    # Players always span exactly _PARTICIPANT_COLUMNS columns, matching
    # the waitlist row's width below: with 2 confirmed players, column 1
    # holds Player A, column 2 holds Player B, and column 3 is a blank
    # spacer (contiguous split; see GameMessageFormatter._split_into_columns).
    participants_fields = [f for f in embed.fields if f.name and "Players" in f.name]
    assert len(participants_fields) == 1, "Expected exactly one named Players field"
    participants_idx = embed.fields.index(participants_fields[0])
    participants_columns = embed.fields[participants_idx : participants_idx + _PARTICIPANT_COLUMNS]
    assert len(participants_columns) == _PARTICIPANT_COLUMNS, (
        "Players should render as _PARTICIPANT_COLUMNS columns"
    )
    assert "Player A" in participants_columns[0].value
    assert "Player B" in participants_columns[1].value

    # Waitlist spans exactly _WAITLIST_COLUMNS columns, contiguous, numbered
    # from 1 - not continuing from the 2 confirmed players.
    waitlist_fields = [f for f in embed.fields if f.name and "Waitlist" in f.name]
    assert len(waitlist_fields) == 1, "Expected exactly one named Waitlist field"
    assert "(7)" in waitlist_fields[0].name
    waitlist_idx = embed.fields.index(waitlist_fields[0])
    waitlist_columns = embed.fields[waitlist_idx : waitlist_idx + _WAITLIST_COLUMNS]
    assert len(waitlist_columns) == _WAITLIST_COLUMNS, (
        "Waitlist should render as _WAITLIST_COLUMNS side-by-side columns"
    )

    col1, col2, col3 = (f.value for f in waitlist_columns)
    assert "1. Waitlist 1" in col1
    assert "2. Waitlist 2" in col1
    assert "3. Waitlist 3" in col1
    assert "4. Waitlist 4" in col2
    assert "5. Waitlist 5" in col2
    assert "6. Waitlist 6" in col2
    assert "7. Waitlist 7" in col3
    print(f"✓ Waitlist renders as {_WAITLIST_COLUMNS} contiguous columns numbered from 1")
