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


"""E2E test for waitlist promotion notification flow."""

import json
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import text

from shared.models.participant import ParticipantType
from shared.models.signup_method import SignupMethod
from tests.e2e.conftest import TimeoutType, wait_for_game_message_id
from tests.e2e.helpers.discord import DMType

pytestmark = pytest.mark.e2e


async def trigger_promotion_via_removal(
    authenticated_admin_client,
    admin_db,
    game_id: str,
    placeholder_participant_id: str,
) -> str:
    """Trigger promotion by removing placeholder participant."""
    update_data = {
        "removed_participant_ids": json.dumps([placeholder_participant_id]),
    }

    response = await authenticated_admin_client.put(f"/api/v1/games/{game_id}", data=update_data)
    assert response.status_code == 200, f"Failed to remove placeholder: {response.text}"
    return "Removed placeholder participant to trigger promotion"


async def trigger_promotion_via_max_players_increase(
    authenticated_admin_client,
    admin_db,
    game_id: str,
    placeholder_participant_id: str,
) -> str:
    """Trigger promotion by increasing max_players."""
    update_data = {
        "max_players": "2",
    }

    response = await authenticated_admin_client.put(f"/api/v1/games/{game_id}", data=update_data)
    assert response.status_code == 200, f"Failed to increase max_players: {response.text}"
    return "Increased max_players from 1 to 2 to trigger promotion"


@pytest.mark.parametrize(
    ("trigger_func", "expected_player_count", "test_desc"),
    [
        (trigger_promotion_via_removal, "1/1", "participant removal"),
        (trigger_promotion_via_max_players_increase, "2/2", "max_players increase"),
    ],
    ids=["via_removal", "via_max_players_increase"],
)
@pytest.mark.asyncio
async def test_waitlist_promotion_sends_dm(
    trigger_func: Callable,
    expected_player_count: str,
    test_desc: str,
    authenticated_admin_client,
    admin_db,
    discord_helper,
    main_bot_helper,
    discord_channel_id,
    discord_user_id,
    discord_guild_id,
    synced_guild,
    test_timeouts,
    test_user_discord_user_id,
):
    """
    E2E: Waitlist user promoted via trigger and receives DM.

    Verifies:
    - Game created at max capacity with placeholder participant
    - Real test user added to waitlist
    - Trigger (removal or max_players increase) causes promotion
    - Test user receives promotion DM
    - Discord message updated with new participant count
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

    game_title = f"E2E Promotion ({test_desc}) {datetime.now(UTC).isoformat()}"
    scheduled_at = datetime.now(UTC) + timedelta(hours=2)

    # Create game with max_players=1 and both placeholder and test user
    # Test user will be in overflow (waitlist) since max is 1
    game_data = {
        "template_id": test_template_id,
        "title": game_title,
        "description": f"Testing promotion via {test_desc}",
        "scheduled_at": scheduled_at.isoformat(),
        "max_players": 1,
        "initial_participants": json.dumps(["Reserved", f"<@{discord_user_id}>"]),
    }

    response = await authenticated_admin_client.post("/api/v1/games", data=game_data)
    assert response.status_code == 201, f"Failed to create game: {response.text}"

    game_id = response.json()["id"]
    print(f"✓ Created game {game_id} with placeholder + test user (overflow)")

    message_id = await wait_for_game_message_id(
        admin_db, game_id, timeout=test_timeouts[TimeoutType.DB_WRITE]
    )
    assert message_id is not None, "Message ID should be populated after announcement"

    # Wait for initial message to be created
    await discord_helper.wait_for_message(
        channel_id=discord_channel_id,
        message_id=message_id,
        timeout=test_timeouts[TimeoutType.MESSAGE_CREATE],
    )

    # Verify initial message shows 1/1 confirmed with test user in overflow
    initial_message = await discord_helper.get_message(discord_channel_id, message_id)
    assert initial_message is not None
    initial_embed = initial_message.embeds[0]

    # Find participants field
    participants_field = None
    for field in initial_embed.fields:
        if field.name and "Participants" in field.name:
            participants_field = field
            break

    assert participants_field is not None, "Participants field not found"
    assert "1/1" in participants_field.name, (
        f"Expected 1/1 in field name, got: {participants_field.name}"
    )
    assert "Reserved" in participants_field.value, (
        f"Expected 'Reserved' in participants, got: {participants_field.value}"
    )
    print("✓ Initial message shows 1/1 with Reserved, test user in overflow")

    # Get placeholder participant ID for removal trigger
    result = await admin_db.execute(
        text(
            """
            SELECT id FROM game_participants
            WHERE game_session_id = :game_id AND display_name = 'Reserved'
            """
        ),
        {"game_id": game_id},
    )
    placeholder_participant_id = result.scalar_one()
    print(f"✓ Found placeholder participant ID: {placeholder_participant_id}")

    # Trigger promotion using provided strategy
    trigger_message = await trigger_func(
        authenticated_admin_client, admin_db, game_id, placeholder_participant_id
    )
    print(f"✓ {trigger_message}")

    # Wait for bot to process promotion event and send DM
    promotion_dm = await main_bot_helper.wait_for_recent_dm(
        user_id=discord_user_id,
        game_title=game_title,
        dm_type=DMType.PROMOTION,
        timeout=test_timeouts[TimeoutType.DM_IMMEDIATE],
    )

    # Wait for Discord message to be updated with new participant count
    promoted_message = await discord_helper.wait_for_message_update(
        channel_id=discord_channel_id,
        message_id=message_id,
        check_func=lambda msg: (
            msg.embeds
            and any(
                expected_player_count in field.name
                for field in msg.embeds[0].fields
                if field.name and "Participants" in field.name
            )
        ),
        timeout=test_timeouts[TimeoutType.MESSAGE_UPDATE] + 5,
        interval=2.0,
        description=f"message update to show {expected_player_count} after promotion",
    )
    assert promoted_message is not None
    promoted_embed = promoted_message.embeds[0]

    # Find participants field for verification
    participants_field = None
    for field in promoted_embed.fields:
        if field.name and "Participants" in field.name:
            participants_field = field
            break

    assert participants_field is not None, "Participants field not found"
    print(f"✓ Discord message shows {expected_player_count} with test user promoted")

    # Verify promotion DM content
    assert promotion_dm is not None, "Test user should have received promotion DM"
    assert game_title in promotion_dm.content, (
        f"Game title '{game_title}' not found in DM: {promotion_dm.content[:100]}"
    )
    expected_jump_url = (
        f"https://discord.com/channels/{discord_guild_id}/{discord_channel_id}/{message_id}"
    )
    assert f"[View game in Discord]({expected_jump_url})" in promotion_dm.content, (
        f"Promotion DM should contain link to game embed: {expected_jump_url}"
    )
    print(f"✓ Test user received promotion DM: {promotion_dm.content[:100]}...")
    print(f"✓ Test complete: Waitlist promotion via {test_desc} validated")


@pytest.mark.timeout(240)
@pytest.mark.asyncio
async def test_promotion_drag_delivers_promotion_dm(
    authenticated_admin_client,
    admin_db,
    discord_helper,
    main_bot_helper,
    discord_channel_id,
    discord_user_id,
    discord_guild_id,
    synced_guild,
    test_timeouts,
    test_user_discord_user_id,
):
    """
    E2E: Host promoting a waitlisted player in HOST_SELECTED_WITH_WAITLIST sends promotion DM.

    Verifies:
    - Game created with HOST_SELECTED_WITH_WAITLIST
    - Test user joins (lands on waitlist as SELF_ADDED in overflow)
    - Host explicitly selects (promotes) the waitlisted user via the participants update API
    - Test user receives a promotion DM
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

    game_title = f"E2E Host Drag Promote {uuid4().hex[:8]}"
    scheduled_at = datetime.now(UTC) + timedelta(hours=2)

    game_data = {
        "template_id": test_template_id,
        "title": game_title,
        "description": "Testing promotion via host drag in HOST_SELECTED_WITH_WAITLIST",
        "scheduled_at": scheduled_at.isoformat(),
        "max_players": "4",
        "signup_method": SignupMethod.HOST_SELECTED_WITH_WAITLIST.value,
    }

    response = await authenticated_admin_client.post("/api/v1/games", data=game_data)
    assert response.status_code == 201, f"Failed to create game: {response.text}"
    game_id = response.json()["id"]
    print(f"✓ Created HOST_SELECTED_WITH_WAITLIST game {game_id}")

    message_id = await wait_for_game_message_id(
        admin_db, game_id, timeout=test_timeouts[TimeoutType.DB_WRITE]
    )
    await main_bot_helper.wait_for_message(
        channel_id=discord_channel_id,
        message_id=message_id,
        timeout=test_timeouts[TimeoutType.MESSAGE_CREATE],
    )

    real_user_id = test_user_discord_user_id.id

    participant_id = str(uuid4())
    await admin_db.execute(
        text(
            "INSERT INTO game_participants "
            "(id, game_session_id, user_id, position, position_type) "
            "VALUES (:id, :game_id, :user_id, :position, :position_type)"
        ),
        {
            "id": participant_id,
            "game_id": game_id,
            "user_id": real_user_id,
            "position": 5,
            "position_type": int(ParticipantType.SELF_ADDED),
        },
    )
    await admin_db.commit()
    print(
        f"✓ Test user {discord_user_id} added as SELF_ADDED overflow participant "
        f"(id={participant_id})"
    )

    # Host promotes by passing the participant as a host-selected entry
    promote_data = {
        "participants": json.dumps([{"participant_id": participant_id, "position": 1}]),
    }
    promote_response = await authenticated_admin_client.put(
        f"/api/v1/games/{game_id}", data=promote_data
    )
    assert promote_response.status_code == 200, (
        f"Failed to promote participant: {promote_response.text}"
    )
    print(f"✓ Host promoted test user from waitlist (participant {participant_id})")

    # Verify user now has HOST_ADDED position type
    admin_db.expire_all()
    await admin_db.commit()

    result = await admin_db.execute(
        text("SELECT position_type FROM game_participants WHERE id = :participant_id"),
        {"participant_id": participant_id},
    )
    promoted_row = result.fetchone()
    assert promoted_row, f"Participant {participant_id} not found after promotion"
    assert promoted_row[0] == int(ParticipantType.HOST_ADDED), (
        f"Participant should be HOST_ADDED after promotion, got: {promoted_row[0]}"
    )
    print("✓ Participant promoted to HOST_ADDED in DB")

    # Wait for promotion DM
    promotion_dm = await main_bot_helper.wait_for_recent_dm(
        user_id=discord_user_id,
        game_title=game_title,
        dm_type=DMType.PROMOTION,
        timeout=90,
        interval=5,
    )

    assert promotion_dm is not None, "Test user should have received a promotion DM"
    assert game_title in promotion_dm.content, (
        f"Promotion DM should contain game title '{game_title}'"
    )
    expected_jump_url = (
        f"https://discord.com/channels/{discord_guild_id}/{discord_channel_id}/{message_id}"
    )
    assert f"[View game in Discord]({expected_jump_url})" in promotion_dm.content, (
        f"Promotion DM should contain link to game embed: {expected_jump_url}"
    )
    print(f"✓ Test user received promotion DM: {promotion_dm.content[:100]}...")
    print("✓ HOST_SELECTED_WITH_WAITLIST promotion drag DM delivery validated")
