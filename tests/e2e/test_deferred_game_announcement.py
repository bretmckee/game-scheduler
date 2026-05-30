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


"""End-to-end tests for deferred game announcement via AnnouncementLoop.

Tests the full stack (API + bot AnnouncementLoop + real Discord):
1. Game with future post_at is hidden from non-host players until announced
2. Bot announces the game when post_at time arrives
3. Game becomes visible to all guild members after announcement
4. Clearing post_at via PATCH triggers immediate announcement

Requires:
- PostgreSQL with migrations applied and E2E data seeded by init service
- RabbitMQ with exchanges/queues configured
- Discord bot connected to test guild, running AnnouncementLoop
- API service running on localhost:8000
- Full stack via compose.e2e.yaml profile

Additional Discord infrastructure (beyond standard E2E setup):
- Player Bot A: a plain Guild A member with no host/manager role
  See docs/developer/TESTING.md § "Player Bot A" for setup instructions.
"""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import text

from tests.e2e.conftest import TimeoutType, wait_for_game_message_id

pytestmark = pytest.mark.e2e

# post_at offset used for deferred tests: gives the stack time to start the
# LISTEN connection and reach the assertion before post_at passes.
_POST_AT_DELAY_SECONDS = 30

# Timeout that covers the full delay plus bot processing headroom.
_DEFERRED_TIMEOUT_SECONDS = 90


async def _get_guild_and_template_ids(admin_db, discord_guild_id):
    """Return (guild_db_id, template_id) for the test guild."""
    result = await admin_db.execute(
        text("SELECT id FROM guild_configurations WHERE guild_id = :guild_id"),
        {"guild_id": discord_guild_id},
    )
    row = result.fetchone()
    assert row, f"Test guild {discord_guild_id} not found"
    guild_db_id = row[0]

    result = await admin_db.execute(
        text("SELECT id FROM game_templates WHERE guild_id = :guild_id AND is_default = true"),
        {"guild_id": guild_db_id},
    )
    row = result.fetchone()
    assert row, f"Default template not found for guild {guild_db_id}"
    return guild_db_id, row[0]


@pytest.mark.asyncio
async def test_deferred_game_not_visible_before_announcement(
    authenticated_admin_client,
    authenticated_player_a_client,
    admin_db,
    discord_guild_id,
    synced_guild,
    test_timeouts,
):
    """
    E2E: Deferred game is hidden from non-host players before announcement.

    Verifies:
    - Admin creates game with future post_at → message_id is None immediately
    - Non-host (Player A) lists games → deferred game is absent
    - Admin lists games → deferred game is present (host always sees it)
    """
    guild_db_id, template_id = await _get_guild_and_template_ids(admin_db, discord_guild_id)

    post_at = datetime.now(UTC) + timedelta(seconds=_POST_AT_DELAY_SECONDS)
    game_title = f"E2E Deferred Hidden {uuid4().hex[:8]}"
    game_data = {
        "template_id": template_id,
        "title": game_title,
        "description": "Testing deferred announcement visibility",
        "scheduled_at": (datetime.now(UTC) + timedelta(hours=2)).isoformat(),
        "max_players": "4",
        "post_at": post_at.isoformat(),
    }

    response = await authenticated_admin_client.post("/api/v1/games", data=game_data)
    assert response.status_code == 201, f"Failed to create game: {response.text}"
    game_id = response.json()["id"]

    # Immediately after creation: message_id must be None (not yet announced).
    result = await admin_db.execute(
        text("SELECT message_id FROM game_sessions WHERE id = :game_id"),
        {"game_id": game_id},
    )
    row = result.fetchone()
    assert row is not None, "Game row not found in database"
    assert row[0] is None, (
        f"Game with future post_at should not be announced immediately; message_id={row[0]}"
    )

    # Player A (non-host, non-manager) must not see the pending game in the list.
    player_response = await authenticated_player_a_client.get(
        f"/api/v1/games?guild_id={guild_db_id}"
    )
    assert player_response.status_code == 200, player_response.text
    player_game_ids = [g["id"] for g in player_response.json()["games"]]
    assert game_id not in player_game_ids, (
        "Deferred game should be hidden from non-host player before announcement"
    )

    # Admin (host) must still see their own pending game.
    admin_response = await authenticated_admin_client.get(f"/api/v1/games?guild_id={guild_db_id}")
    assert admin_response.status_code == 200, admin_response.text
    admin_game_ids = [g["id"] for g in admin_response.json()["games"]]
    assert game_id in admin_game_ids, (
        "Deferred game should be visible to its host before announcement"
    )


@pytest.mark.timeout(120)
@pytest.mark.asyncio
async def test_deferred_game_announces_at_post_at_time(
    authenticated_admin_client,
    admin_db,
    discord_helper,
    discord_channel_id,
    discord_guild_id,
    synced_guild,
    test_timeouts,
):
    """
    E2E: Bot posts Discord announcement when post_at time arrives.

    Verifies:
    - After waiting for post_at, message_id is set in the database
    - The Discord message exists in the configured channel
    """
    _guild_db_id, template_id = await _get_guild_and_template_ids(admin_db, discord_guild_id)

    post_at = datetime.now(UTC) + timedelta(seconds=_POST_AT_DELAY_SECONDS)
    game_title = f"E2E Deferred Announce {uuid4().hex[:8]}"
    game_data = {
        "template_id": template_id,
        "title": game_title,
        "description": "Testing deferred announcement timing",
        "scheduled_at": (datetime.now(UTC) + timedelta(hours=2)).isoformat(),
        "max_players": "4",
        "post_at": post_at.isoformat(),
    }

    response = await authenticated_admin_client.post("/api/v1/games", data=game_data)
    assert response.status_code == 201, f"Failed to create game: {response.text}"
    game_id = response.json()["id"]

    message_id = await wait_for_game_message_id(
        admin_db, game_id, timeout=_DEFERRED_TIMEOUT_SECONDS
    )
    assert message_id is not None, (
        f"message_id not set within {_DEFERRED_TIMEOUT_SECONDS}s after post_at"
    )

    message = await discord_helper.get_message(discord_channel_id, message_id)
    assert message is not None, "Discord announcement message should exist after post_at"
    assert len(message.embeds) == 1, "Announcement message should have exactly one embed"
    assert message.embeds[0].title == game_title, (
        f"Embed title mismatch: expected '{game_title}', got '{message.embeds[0].title}'"
    )


@pytest.mark.timeout(120)
@pytest.mark.asyncio
async def test_deferred_game_visible_after_announcement(
    authenticated_admin_client,
    authenticated_player_a_client,
    admin_db,
    discord_guild_id,
    synced_guild,
    test_timeouts,
):
    """
    E2E: Deferred game appears in non-host player's list after announcement.

    Verifies:
    - After message_id is set, Player A can see the game in the list
    """
    guild_db_id, template_id = await _get_guild_and_template_ids(admin_db, discord_guild_id)

    post_at = datetime.now(UTC) + timedelta(seconds=_POST_AT_DELAY_SECONDS)
    game_title = f"E2E Deferred Visible {uuid4().hex[:8]}"
    game_data = {
        "template_id": template_id,
        "title": game_title,
        "description": "Testing post-announcement visibility",
        "scheduled_at": (datetime.now(UTC) + timedelta(hours=2)).isoformat(),
        "max_players": "4",
        "post_at": post_at.isoformat(),
    }

    response = await authenticated_admin_client.post("/api/v1/games", data=game_data)
    assert response.status_code == 201, f"Failed to create game: {response.text}"
    game_id = response.json()["id"]

    # Wait for announcement so message_id is set.
    await wait_for_game_message_id(admin_db, game_id, timeout=_DEFERRED_TIMEOUT_SECONDS)

    # Now Player A must see the game.
    player_response = await authenticated_player_a_client.get(
        f"/api/v1/games?guild_id={guild_db_id}"
    )
    assert player_response.status_code == 200, player_response.text
    player_game_ids = [g["id"] for g in player_response.json()["games"]]
    assert game_id in player_game_ids, (
        "Deferred game should be visible to non-host player after announcement"
    )


@pytest.mark.asyncio
async def test_clear_post_at_triggers_immediate_announcement(
    authenticated_admin_client,
    admin_db,
    discord_helper,
    discord_channel_id,
    discord_guild_id,
    synced_guild,
    test_timeouts,
):
    """
    E2E: Clearing post_at via PATCH causes immediate Discord announcement.

    Verifies:
    - Game created with future post_at is not announced immediately
    - PATCH with clear_post_at=true triggers announcement without waiting for post_at
    - message_id is set within normal DB-write timeout after the PATCH
    """
    _guild_db_id, template_id = await _get_guild_and_template_ids(admin_db, discord_guild_id)

    post_at = datetime.now(UTC) + timedelta(seconds=_POST_AT_DELAY_SECONDS)
    game_title = f"E2E Clear PostAt {uuid4().hex[:8]}"
    game_data = {
        "template_id": template_id,
        "title": game_title,
        "description": "Testing clear_post_at immediate announcement",
        "scheduled_at": (datetime.now(UTC) + timedelta(hours=2)).isoformat(),
        "max_players": "4",
        "post_at": post_at.isoformat(),
    }

    response = await authenticated_admin_client.post("/api/v1/games", data=game_data)
    assert response.status_code == 201, f"Failed to create game: {response.text}"
    game_id = response.json()["id"]

    # Confirm not announced yet.
    result = await admin_db.execute(
        text("SELECT message_id FROM game_sessions WHERE id = :game_id"),
        {"game_id": game_id},
    )
    assert result.fetchone()[0] is None, "Game should not be announced before PATCH"

    # Clear post_at — this should trigger an immediate announcement via the
    # game_announcement_changed NOTIFY, which wakes AnnouncementLoop.
    patch_response = await authenticated_admin_client.put(
        f"/api/v1/games/{game_id}",
        data={"clear_post_at": "true"},
    )
    assert patch_response.status_code == 200, f"PUT clear_post_at failed: {patch_response.text}"

    # Announcement should arrive quickly — well within MESSAGE_CREATE timeout.
    message_id = await wait_for_game_message_id(
        admin_db, game_id, timeout=test_timeouts[TimeoutType.MESSAGE_CREATE]
    )
    assert message_id is not None, "message_id should be set quickly after clearing post_at"

    message = await discord_helper.get_message(discord_channel_id, message_id)
    assert message is not None, "Discord announcement message should exist after clearing post_at"
