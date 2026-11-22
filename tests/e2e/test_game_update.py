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

import json
import re
from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import text

from shared.cache.client import RedisClient
from shared.cache.projection import search_members_by_prefix
from tests.e2e.conftest import TimeoutType, wait_for_game_message_id
from tests.e2e.helpers.discord import DMType

pytestmark = pytest.mark.e2e

# Mirrors the free-text scanner (participant_resolver) and the suggestion cap.
_SCANNABLE_PREFIX = re.compile(r"\w+")
_MAX_MENTION_SUGGESTIONS = 10
_NAME_FIELDS = ("username", "nick", "global_name")


@pytest.fixture
async def redis() -> AsyncGenerator[RedisClient]:
    """Fresh Redis client per test, avoiding the module-level singleton."""
    client = RedisClient()
    await client.connect()
    yield client
    await client.disconnect()


async def _default_template_id(admin_db, discord_guild_id: str) -> str:
    result = await admin_db.execute(
        text(
            "SELECT t.id FROM game_templates t "
            "JOIN guild_configurations g ON g.id = t.guild_id "
            "WHERE g.guild_id = :guild_id AND t.is_default = true"
        ),
        {"guild_id": discord_guild_id},
    )
    row = result.fetchone()
    assert row, f"Default template not found for guild {discord_guild_id}"
    return row[0]


def _members_matching(members: list[dict], prefix: str) -> list[dict]:
    return [
        m
        for m in members
        if any((m.get(field) or "").casefold().startswith(prefix) for field in _NAME_FIELDS)
    ]


def _find_ambiguous_prefix(members: list[dict]) -> tuple[str, set[str]]:
    """
    Pick a scannable prefix that matches 2..cap real members and no name exactly.

    Such a prefix makes the API return "Multiple matches found" with suggestions
    instead of resolving outright via the exact-match rule.
    """
    candidates = sorted(
        {
            name[:length]
            for m in members
            for field in _NAME_FIELDS
            if (name := (m.get(field) or "").casefold())
            for length in range(1, len(name) + 1)
            if _SCANNABLE_PREFIX.fullmatch(name[:length])
        },
        key=lambda p: (-len(p), p),
    )
    for prefix in candidates:
        matches = _members_matching(members, prefix)
        exact = any(
            (m.get(field) or "").casefold() == prefix for m in matches for field in _NAME_FIELDS
        )
        if 2 <= len(matches) <= _MAX_MENTION_SUGGESTIONS and not exact:
            return prefix, {m["uid"] for m in matches}
    pytest.fail(
        "E2E guild needs two members sharing a name prefix that is not itself a "
        f"member name; projection members: {[m.get('username') for m in members]}"
    )


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


@pytest.mark.timeout(240)
@pytest.mark.asyncio
async def test_game_time_change_sends_dm(
    authenticated_admin_client,
    admin_db,
    main_bot_helper,
    discord_channel_id,
    discord_user_id,
    discord_guild_id,
    synced_guild,
    test_user_discord_user_id,
    test_timeouts,
):
    """
    E2E: Moving an announced game's time DMs its participants.

    Verifies:
    - Game created with the real test user as a participant and announced
    - scheduled_at moved by one hour via PUT /games/{game_id}
    - Test user receives a game_updated DM with the old time, new time and game link
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

    game_title = f"E2E Time Change {uuid4().hex[:8]}"
    old_scheduled_at = (datetime.now(UTC) + timedelta(hours=2)).replace(microsecond=0)
    new_scheduled_at = old_scheduled_at + timedelta(hours=1)

    game_data = {
        "template_id": test_template_id,
        "title": game_title,
        "description": "Testing game time change DM",
        "scheduled_at": old_scheduled_at.isoformat(),
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
    assert message_id is not None, "Message ID should be populated after announcement"
    await main_bot_helper.wait_for_message(
        channel_id=discord_channel_id,
        message_id=message_id,
        timeout=test_timeouts[TimeoutType.MESSAGE_CREATE],
    )

    update_response = await authenticated_admin_client.put(
        f"/api/v1/games/{game_id}",
        data={"scheduled_at": new_scheduled_at.isoformat()},
    )
    assert update_response.status_code == 200, f"Failed to update game: {update_response.text}"
    print("[TEST] Game time moved by one hour")

    change_dm = await main_bot_helper.wait_for_recent_dm(
        user_id=discord_user_id,
        game_title=game_title,
        dm_type=DMType.GAME_UPDATED,
        timeout=test_timeouts[TimeoutType.DM_IMMEDIATE],
    )

    old_unix = int(old_scheduled_at.timestamp())
    new_unix = int(new_scheduled_at.timestamp())
    assert f"<t:{old_unix}:F>" in change_dm.content, (
        f"Change DM should show the old time <t:{old_unix}:F>: {change_dm.content}"
    )
    assert f"<t:{new_unix}:F>" in change_dm.content, (
        f"Change DM should show the new time <t:{new_unix}:F>: {change_dm.content}"
    )
    expected_jump_url = (
        f"https://discord.com/channels/{discord_guild_id}/{discord_channel_id}/{message_id}"
    )
    assert expected_jump_url in change_dm.content, (
        f"Change DM should contain link to game embed: {expected_jump_url}"
    )
    print(f"[TEST] ✓ Participant received change DM: {change_dm.content[:100]}...")


@pytest.mark.asyncio
async def test_unedited_mentions_survive_edit_of_other_field(
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
    E2E (2b regression): echoing the GET description back on edit keeps mention IDs.

    The GET returns labeled tokens (<@id|label>, <#id|label>) whatever the member's
    display name contains; the PUT sends them back untouched alongside a title change.

    Verifies:
    - GET description carries the IDs as labeled tokens
    - Stored description is byte-identical after the PUT
    - The edited Discord embed still contains the plain <@id> / <#id> mentions
    """
    template_id = await _default_template_id(admin_db, discord_guild_id)
    user_mention = f"<@{discord_user_id}>"
    channel_mention = f"<#{discord_channel_id}>"
    stored_description = f"Ask {user_mention} for the code, then join {channel_mention}."

    response = await authenticated_admin_client.post(
        "/api/v1/games",
        data={
            "template_id": template_id,
            "title": f"E2E Mention Round Trip {uuid4().hex[:8]}",
            "description": stored_description,
            "scheduled_at": (datetime.now(UTC) + timedelta(hours=2)).isoformat(),
            "max_players": "4",
        },
    )
    assert response.status_code == 201, f"Failed to create game: {response.text}"
    game_id = response.json()["id"]

    message_id = await wait_for_game_message_id(
        admin_db, game_id, timeout=test_timeouts[TimeoutType.DB_WRITE]
    )
    assert message_id is not None, "Message ID should be populated after announcement"

    fetched = await authenticated_admin_client.get(f"/api/v1/games/{game_id}")
    assert fetched.status_code == 200, fetched.text
    returned_description = fetched.json()["description"]
    labeled_pattern = (
        rf"Ask <@{discord_user_id}\|[^>]+> for the code, "
        rf"then join <#{discord_channel_id}\|[^>]+>\."
    )
    assert re.fullmatch(labeled_pattern, returned_description), (
        f"GET should return labeled tokens for live mentions, got: {returned_description!r}"
    )

    updated_title = f"E2E Mention Round Trip Edited {uuid4().hex[:8]}"
    update_response = await authenticated_admin_client.put(
        f"/api/v1/games/{game_id}",
        data={"title": updated_title, "description": returned_description},
    )
    assert update_response.status_code == 200, f"Failed to update game: {update_response.text}"

    result = await admin_db.execute(
        text("SELECT description FROM game_sessions WHERE id = :game_id"),
        {"game_id": game_id},
    )
    assert result.scalar_one() == stored_description

    updated_message = await discord_helper.wait_for_message_update(
        channel_id=discord_channel_id,
        message_id=message_id,
        check_func=lambda msg: msg.embeds and msg.embeds[0].title == updated_title,
        timeout=test_timeouts[TimeoutType.MESSAGE_UPDATE],
        description="game title update after mention round trip",
    )
    embed_description = updated_message.embeds[0].description
    assert stored_description in embed_description, (
        f"Embed should keep plain Discord mentions, got: {embed_description!r}"
    )


@pytest.mark.asyncio
async def test_ambiguous_mention_saves_on_first_retry_with_picked_id(
    authenticated_admin_client,
    admin_db,
    discord_helper,
    discord_channel_id,
    discord_guild_id,
    synced_guild,
    redis,
    test_timeouts,
):
    """
    E2E (2a regression): an ambiguous @prefix prompts once; the picked <@id> saves.

    The prefix is chosen from the live member projection so it matches several real
    guild members without exactly naming any of them.

    Verifies:
    - First POST returns 422 "Multiple matches found" listing exactly those members
    - Resubmitting with the suggestion's <@id> (what the editor sends) returns 201
    - The announcement embed contains the picked member's mention
    """
    members = await search_members_by_prefix(discord_guild_id, "", redis=redis)
    prefix, expected_ids = _find_ambiguous_prefix(members)
    template_id = await _default_template_id(admin_db, discord_guild_id)

    def game_form(description: str) -> dict[str, str]:
        return {
            "template_id": template_id,
            "title": f"E2E Ambiguous Mention {uuid4().hex[:8]}",
            "description": description,
            "scheduled_at": (datetime.now(UTC) + timedelta(hours=2)).isoformat(),
            "max_players": "4",
        }

    ambiguous = await authenticated_admin_client.post(
        "/api/v1/games", data=game_form(f"Ask @{prefix} first")
    )
    assert ambiguous.status_code == 422, ambiguous.text
    errors = ambiguous.json()["detail"]["invalid_mentions"]
    assert [(e["input"], e["reason"]) for e in errors] == [(f"@{prefix}", "Multiple matches found")]
    suggestion_ids = {s["discordId"] for s in errors[0]["suggestions"]}
    assert suggestion_ids == expected_ids

    picked_id = sorted(suggestion_ids)[0]
    picked_description = f"Ask <@{picked_id}> first"
    picked = await authenticated_admin_client.post(
        "/api/v1/games", data=game_form(picked_description)
    )
    assert picked.status_code == 201, f"Picked suggestion should save: {picked.text}"
    game_id = picked.json()["id"]

    message_id = await wait_for_game_message_id(
        admin_db, game_id, timeout=test_timeouts[TimeoutType.DB_WRITE]
    )
    assert message_id is not None, "Message ID should be populated after announcement"
    message = await discord_helper.wait_for_message(
        channel_id=discord_channel_id,
        message_id=message_id,
        timeout=test_timeouts[TimeoutType.MESSAGE_CREATE],
    )
    assert picked_description in message.embeds[0].description
