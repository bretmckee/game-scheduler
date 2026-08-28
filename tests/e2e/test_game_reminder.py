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
6. With reminders_as_dms=true the bot skips the channel post entirely and
   delivers the reminder to the host by DM instead (channel and thread
   locations)
7. A game with no location falls back to DM fan-out for its reminder

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

import discord
import pytest
from sqlalchemy import text

from shared.cache import keys as cache_keys
from shared.cache.client import RedisClient
from tests.e2e.conftest import (
    TimeoutType,
    wait_for_db_condition,
    wait_for_game_message_id,
)
from tests.e2e.helpers.discord import DMType, wait_for_condition

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


@pytest.mark.timeout(300)
@pytest.mark.asyncio
async def test_game_reminder_hybrid_delivery_thread_location(
    authenticated_admin_client,
    admin_db,
    main_bot_helper,
    discord_helper,
    discord_channel_id,
    discord_user_id,
    discord_player_a_id,
    discord_guild_id,
    synced_guild,
    test_timeouts,
):
    """
    E2E: A thread used as the location receives the reminder post.

    Mirrors test_game_reminder_hybrid_delivery but with where=<#thread id>:
    - Admin bot creates a public thread in the location channel
    - Game created with where pointing at that thread (single <#id> mention)
    - Notification daemon processes the reminder schedule
    - Main bot posts one reminder embed into the thread mentioning the
      confirmed participant (Player A) — proves _get_bot_channel accepts
      discord.Thread objects from the gateway cache
    - Main bot sends a reminder DM to the first waitlisted participant
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

    # The announcement post goes to the parent channel; only the reminder
    # targets the thread, so the two are unambiguous in their respective histories.
    thread = await discord_helper.create_thread(
        channel_id=discord_channel_id, name=f"e2e-reminder-{uuid4().hex[:8]}"
    )
    try:
        # The main bot learns about new threads via its gateway THREAD_CREATE event;
        # until _sync_thread_cache runs, the API's channel resolver cannot validate
        # <#thread_id> against the Redis cache and game creation fails with 422.
        # Wait for that sync to land instead of racing the event delivery.
        redis = RedisClient()
        await redis.connect()
        try:

            async def check_thread_cached() -> tuple[bool, str | None]:
                channels = (
                    await redis.get_json(
                        cache_keys.CacheKeys.discord_guild_channels(discord_guild_id)
                    )
                    or []
                )
                if any(ch.get("id") == str(thread.id) for ch in channels):
                    return True, str(thread.id)
                return False, None

            await wait_for_condition(
                check_thread_cached,
                timeout=15,
                interval=0.5,
                description=f"main bot gateway cache to include thread {thread.id}",
            )
        finally:
            await redis.disconnect()

        scheduled_time = datetime.now(UTC) + timedelta(minutes=2)
        game_title = f"E2E Reminder Thread Test {uuid4().hex[:8]}"
        game_description = "Test game for thread-location reminder verification"

        # Player A is confirmed (slot 1 of max_players=1); the test user overflows
        # to waitlist and receives the reminder DM instead of a thread mention.
        game_data = {
            "template_id": test_template_id,
            "title": game_title,
            "description": game_description,
            "where": f"<#{thread.id}>",
            "scheduled_at": scheduled_time.isoformat(),
            "max_players": "1",
            "reminder_minutes": json.dumps([1]),
            "initial_participants": json.dumps([
                f"<@{discord_player_a_id}>",
                f"<@{discord_user_id}>",
            ]),
        }

        response = await authenticated_admin_client.post("/api/v1/games", data=game_data)
        assert response.status_code == 201, f"Failed to create game: {response.text}"
        game_id = response.json()["id"]
        print(f"\n[TEST] Game created with ID: {game_id}")
        print(f"[TEST] Game scheduled at: {scheduled_time.isoformat()}")
        print("[TEST] Reminder set for 1 minute before game")
        print(f"[TEST] Location thread: {thread.id} (single <#id> mention)")
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

        def is_reminder_post(msg) -> bool:
            return (
                msg.embeds
                and msg.embeds[0].title == "🔔 Game Reminder"
                and game_title in (msg.embeds[0].description or "")
            )

        # The reminder must land inside the thread itself, not the parent channel.
        reminder_post = await main_bot_helper.wait_for_channel_message(
            channel_id=str(thread.id),
            predicate=is_reminder_post,
            timeout=test_timeouts[TimeoutType.DM_SCHEDULED],
            interval=5,
            description=f"reminder thread post for '{game_title}'",
        )

        assert f"<@{discord_player_a_id}>" in reminder_post.content, (
            f"Thread post should mention confirmed participant Player A; content: "
            f"{reminder_post.content!r}"
        )
        print("[TEST] ✓ Reminder posted to location thread with confirmed participant mentioned")
        print(f"[TEST] Post Content: {reminder_post.content}")

        reminder_dm = await main_bot_helper.wait_for_recent_dm(
            user_id=discord_user_id,
            game_title=game_title,
            dm_type=DMType.REMINDER,
            timeout=test_timeouts[TimeoutType.DM_SCHEDULED],
            interval=5,
        )

        print("[TEST] ✓ Waitlist reminder DM contains game title")
        print(f"[TEST] DM Content: {reminder_dm.content}")
        print("[TEST] ✓ Game reminder hybrid delivery verified successfully for thread location")
    finally:
        # Archive the test thread so it does not accumulate in the guild;
        # cleanup failures must not mask an otherwise passing test.
        try:
            await thread.edit(archived=True)
        except discord.HTTPException as e:
            print(f"[TEST] Could not archive thread {thread.id}: {e}")


@pytest.mark.timeout(300)
@pytest.mark.asyncio
async def test_game_reminder_dms_only_skips_channel_post(
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
    E2E: reminders_as_dms=true delivers reminders by DM only, no channel post.

    Mirrors test_game_reminder_hybrid_delivery with reminders_as_dms="true":
    - Player A confirmed (slot 1 of max_players=1), test user is host
    - Notification daemon processes the 1-minute reminder schedule
    - Main bot sends the host a reminder DM instead of posting to the
      location channel
    - No "🔔 Game Reminder" embed for this game appears in the channel history

    The host DM is asserted on discord_user_id because the main bot cannot
    open a DM channel with another bot account (Player A); fan-out to
    confirmed participants is covered at unit level.
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
    game_title = f"E2E Reminder DMs Test {uuid4().hex[:8]}"
    game_description = "Test game for DM-only reminder verification"

    # Player A fills the single slot; discord_user_id is the explicit host so
    # its reminder DM can be asserted on (the main bot cannot open a DM with
    # another bot account). With reminders_as_dms=true nothing is posted to
    # the location channel.
    game_data = {
        "template_id": test_template_id,
        "title": game_title,
        "description": game_description,
        "where": f"<#{discord_channel_id}>",
        "scheduled_at": scheduled_time.isoformat(),
        "max_players": "1",
        "host": f"<@{discord_user_id}>",
        "reminder_minutes": json.dumps([1]),
        "reminders_as_dms": "true",
        "initial_participants": json.dumps([f"<@{discord_player_a_id}>"]),
    }

    response = await authenticated_admin_client.post("/api/v1/games", data=game_data)
    assert response.status_code == 201, f"Failed to create game: {response.text}"
    assert response.json()["reminders_as_dms"] is True, (
        "Game should be created with reminders_as_dms=true"
    )
    game_id = response.json()["id"]
    print(f"\n[TEST] Game created with ID: {game_id} (reminders_as_dms=true)")
    print(f"[TEST] Player A confirmed (discord_id: {discord_player_a_id})")
    print(f"[TEST] Host is test user (discord_id: {discord_user_id})")

    message_id = await wait_for_game_message_id(
        admin_db, game_id, timeout=test_timeouts[TimeoutType.DB_WRITE]
    )
    await main_bot_helper.wait_for_message(
        channel_id=discord_channel_id,
        message_id=message_id,
        timeout=test_timeouts[TimeoutType.MESSAGE_CREATE],
    )

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
    print(f"[TEST] Reminder scheduled in database (count: {row[0]})")

    # The host DM proves the bot processed the reminder event and delivered it
    # by DM instead of posting to the location channel.
    host_dm = await main_bot_helper.wait_for_recent_dm(
        user_id=discord_user_id,
        game_title=game_title,
        dm_type=DMType.REMINDER,
        timeout=test_timeouts[TimeoutType.DM_SCHEDULED],
        interval=5,
    )
    print("[TEST] ✓ Host received reminder DM")
    print(f"[TEST] DM Content: {host_dm.content}")

    # The DM arrived after the daemon fired the reminder, so any channel post
    # for this game would already be visible — a final history check suffices.
    # Match on the unique game title because the shared e2e channel accumulates
    # reminder posts from other games' tests.
    recent_messages = await main_bot_helper.get_recent_messages(discord_channel_id, limit=50)
    reminder_posts = [
        msg
        for msg in recent_messages
        if msg.embeds
        and msg.embeds[0].title == "🔔 Game Reminder"
        and game_title in (msg.embeds[0].description or "")
    ]
    assert not reminder_posts, (
        f"No reminder embed for '{game_title}' should appear in the location "
        f"channel when reminders_as_dms=true; found {len(reminder_posts)}"
    )
    print("[TEST] ✓ No reminder posted to location channel")
    print("[TEST] ✓ Game reminder DM-only delivery verified successfully")


@pytest.mark.timeout(300)
@pytest.mark.asyncio
async def test_game_reminder_no_location_delivers_dm_fallback(
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
    E2E: A game with no location delivers its reminder by DM fan-out.

    - Game created without `where` and with reminders_as_dms left at its
      default (false), so this exercises the bot's fallback path rather than
      the host opt-out short-circuit
    - Notification daemon processes the 1-minute reminder schedule
    - Main bot cannot resolve a single location channel, so it falls back to
      full DM fan-out: the host receives a reminder DM
    - No "🔔 Game Reminder" embed for this game appears in the e2e channel
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
    game_title = f"E2E Reminder NoLoc Test {uuid4().hex[:8]}"
    game_description = "Test game for no-location reminder verification"

    # No `where` field at all; Player A fills the single slot and the test
    # user is host so its DM can be asserted on.
    game_data = {
        "template_id": test_template_id,
        "title": game_title,
        "description": game_description,
        "scheduled_at": scheduled_time.isoformat(),
        "max_players": "1",
        "host": f"<@{discord_user_id}>",
        "reminder_minutes": json.dumps([1]),
        "initial_participants": json.dumps([f"<@{discord_player_a_id}>"]),
    }

    response = await authenticated_admin_client.post("/api/v1/games", data=game_data)
    assert response.status_code == 201, f"Failed to create game: {response.text}"
    assert response.json()["reminders_as_dms"] is False, (
        "Game should keep the default reminders_as_dms=false"
    )
    game_id = response.json()["id"]
    print(f"\n[TEST] Game created with ID: {game_id} (no location)")
    print(f"[TEST] Player A confirmed (discord_id: {discord_player_a_id})")
    print(f"[TEST] Host is test user (discord_id: {discord_user_id})")

    message_id = await wait_for_game_message_id(
        admin_db, game_id, timeout=test_timeouts[TimeoutType.DB_WRITE]
    )
    await main_bot_helper.wait_for_message(
        channel_id=discord_channel_id,
        message_id=message_id,
        timeout=test_timeouts[TimeoutType.MESSAGE_CREATE],
    )

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
    print(f"[TEST] Reminder scheduled in database (count: {row[0]})")

    host_dm = await main_bot_helper.wait_for_recent_dm(
        user_id=discord_user_id,
        game_title=game_title,
        dm_type=DMType.REMINDER,
        timeout=test_timeouts[TimeoutType.DM_SCHEDULED],
        interval=5,
    )
    print("[TEST] ✓ Host received reminder DM via no-location fallback")
    print(f"[TEST] DM Content: {host_dm.content}")

    # Match on the unique game title because the shared e2e channel accumulates
    # reminder posts from other games' tests.
    recent_messages = await main_bot_helper.get_recent_messages(discord_channel_id, limit=50)
    reminder_posts = [
        msg
        for msg in recent_messages
        if msg.embeds
        and msg.embeds[0].title == "🔔 Game Reminder"
        and game_title in (msg.embeds[0].description or "")
    ]
    assert not reminder_posts, (
        f"No reminder embed for '{game_title}' should appear in the location "
        f"channel when the game has no location; found {len(reminder_posts)}"
    )
    print("[TEST] ✓ No reminder posted to any channel")
    print("[TEST] ✓ Game reminder no-location DM fallback verified successfully")


@pytest.mark.timeout(300)
@pytest.mark.asyncio
async def test_game_reminder_thread_location_dms_only_skips_post(
    authenticated_admin_client,
    admin_db,
    main_bot_helper,
    discord_helper,
    discord_channel_id,
    discord_user_id,
    discord_player_a_id,
    discord_guild_id,
    synced_guild,
    test_timeouts,
):
    """
    E2E: A thread location with reminders_as_dms=true receives no post.

    Mirrors test_game_reminder_hybrid_delivery_thread_location but with
    reminders_as_dms="true":
    - Admin bot creates a public thread used as the game location
    - Notification daemon processes the 1-minute reminder schedule
    - Main bot skips the thread lookup/post entirely and sends the host a
      reminder DM instead
    - Neither the thread nor its parent channel contains a reminder embed
      for this game
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

    # The announcement post goes to the parent channel; only the reminder
    # would target the thread, so both histories are unambiguous.
    thread = await discord_helper.create_thread(
        channel_id=discord_channel_id, name=f"e2e-reminder-dms-{uuid4().hex[:8]}"
    )
    try:
        # The main bot learns about new threads via its gateway THREAD_CREATE event;
        # until _sync_thread_cache runs, the API's channel resolver cannot validate
        # <#thread_id> against the Redis cache and game creation fails with 422.
        redis = RedisClient()
        await redis.connect()
        try:

            async def check_thread_cached() -> tuple[bool, str | None]:
                channels = (
                    await redis.get_json(
                        cache_keys.CacheKeys.discord_guild_channels(discord_guild_id)
                    )
                    or []
                )
                if any(ch.get("id") == str(thread.id) for ch in channels):
                    return True, str(thread.id)
                return False, None

            await wait_for_condition(
                check_thread_cached,
                timeout=15,
                interval=0.5,
                description=f"main bot gateway cache to include thread {thread.id}",
            )
        finally:
            await redis.disconnect()

        scheduled_time = datetime.now(UTC) + timedelta(minutes=2)
        game_title = f"E2E Reminder Thread DMs Test {uuid4().hex[:8]}"
        game_description = "Test game for thread-location DM-only reminder verification"

        # Player A fills the single slot; discord_user_id is host so its
        # reminder DM can be asserted on.
        game_data = {
            "template_id": test_template_id,
            "title": game_title,
            "description": game_description,
            "where": f"<#{thread.id}>",
            "scheduled_at": scheduled_time.isoformat(),
            "max_players": "1",
            "host": f"<@{discord_user_id}>",
            "reminder_minutes": json.dumps([1]),
            "reminders_as_dms": "true",
            "initial_participants": json.dumps([f"<@{discord_player_a_id}>"]),
        }

        response = await authenticated_admin_client.post("/api/v1/games", data=game_data)
        assert response.status_code == 201, f"Failed to create game: {response.text}"
        assert response.json()["reminders_as_dms"] is True, (
            "Game should be created with reminders_as_dms=true"
        )
        game_id = response.json()["id"]
        print(f"\n[TEST] Game created with ID: {game_id} (thread location, reminders_as_dms=true)")
        print(f"[TEST] Player A confirmed (discord_id: {discord_player_a_id})")
        print(f"[TEST] Host is test user (discord_id: {discord_user_id})")

        message_id = await wait_for_game_message_id(
            admin_db, game_id, timeout=test_timeouts[TimeoutType.DB_WRITE]
        )
        await main_bot_helper.wait_for_message(
            channel_id=discord_channel_id,
            message_id=message_id,
            timeout=test_timeouts[TimeoutType.MESSAGE_CREATE],
        )

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
        print(f"[TEST] Reminder scheduled in database (count: {row[0]})")

        def is_reminder_post(msg) -> bool:
            return (
                msg.embeds
                and msg.embeds[0].title == "🔔 Game Reminder"
                and game_title in (msg.embeds[0].description or "")
            )

        host_dm = await main_bot_helper.wait_for_recent_dm(
            user_id=discord_user_id,
            game_title=game_title,
            dm_type=DMType.REMINDER,
            timeout=test_timeouts[TimeoutType.DM_SCHEDULED],
            interval=5,
        )
        print("[TEST] ✓ Host received reminder DM")
        print(f"[TEST] DM Content: {host_dm.content}")

        # The DM arrived after the daemon fired the reminder, so any post for
        # this game would already be visible — final history checks on both the
        # thread and its parent channel suffice.
        thread_messages = await main_bot_helper.get_recent_messages(str(thread.id), limit=20)
        assert not [m for m in thread_messages if is_reminder_post(m)], (
            f"No reminder embed for '{game_title}' should appear in the location "
            f"thread when reminders_as_dms=true"
        )
        parent_messages = await main_bot_helper.get_recent_messages(discord_channel_id, limit=50)
        assert not [m for m in parent_messages if is_reminder_post(m)], (
            f"No reminder embed for '{game_title}' should appear in the parent "
            f"channel when reminders_as_dms=true"
        )
        print("[TEST] ✓ No reminder posted to thread or parent channel")
        print("[TEST] ✓ Game reminder thread-location DM-only delivery verified successfully")
    finally:
        # Archive the test thread so it does not accumulate in the guild;
        # cleanup failures must not mask an otherwise passing test.
        try:
            await thread.edit(archived=True)
        except discord.HTTPException as e:
            print(f"[TEST] Could not archive thread {thread.id}: {e}")
