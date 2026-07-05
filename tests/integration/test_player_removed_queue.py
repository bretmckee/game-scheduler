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


"""Integration tests for Flows 3 and 4: player removal and waitlist-promotion DM.

Flow 3: PUT /api/v1/games/{id} with removed_participant_ids creates a
'player_removed' row in bot_action_queue with the correct game_id.

Flow 4: Removing the confirmed player from a HOST_SELECTED_WITH_WAITLIST
game (max_players=1) triggers a 'send_dm' promotion notification for the
waitlisted player.
"""

import json
import uuid as _uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import text

from shared.models.participant import ParticipantType
from shared.models.signup_method import SignupMethod
from shared.utils.discord_tokens import extract_bot_discord_id

pytestmark = pytest.mark.integration

TEST_DISCORD_TOKEN = "MTQ0NDA3ODM4NjM4MDAxMzY0OA.GvmbbW.fake_token_for_integration_tests"
TEST_BOT_DISCORD_ID = extract_bot_discord_id(TEST_DISCORD_TOKEN)
BOT_MANAGER_ROLE_ID = "761234567890123456"


def _make_context(
    create_guild,
    create_channel,
    create_user,
    create_template,
    seed_redis_cache,
    *,
    guild_discord_id: str,
    channel_discord_id: str,
    allowed_signup_methods: list[str] | None = None,
    default_signup_method: str = "SELF_SIGNUP",
):
    guild = create_guild(discord_guild_id=guild_discord_id, bot_manager_roles=[BOT_MANAGER_ROLE_ID])
    channel = create_channel(guild_id=guild["id"], discord_channel_id=channel_discord_id)
    create_user(discord_user_id=TEST_BOT_DISCORD_ID)
    template = create_template(
        guild_id=guild["id"],
        channel_id=channel["id"],
        allowed_signup_methods=allowed_signup_methods or ["SELF_SIGNUP"],
        default_signup_method=default_signup_method,
    )
    seed_redis_cache(
        user_discord_id=TEST_BOT_DISCORD_ID,
        guild_discord_id=guild_discord_id,
        channel_discord_id=channel_discord_id,
        user_roles=[BOT_MANAGER_ROLE_ID, guild_discord_id],
        bot_manager_roles=[BOT_MANAGER_ROLE_ID],
    )
    return {"template_id": template["id"]}


def _insert_participant(
    admin_db_sync,
    game_id: str,
    user_id: str,
    position: int,
    position_type: ParticipantType = ParticipantType.SELF_ADDED,
) -> str:
    participant_id = str(_uuid.uuid4())
    admin_db_sync.execute(
        text(
            "INSERT INTO game_participants "
            "(id, game_session_id, user_id, position, position_type, joined_at) "
            "VALUES (:id, :game_id, :user_id, :position, :position_type, :joined_at)"
        ),
        {
            "id": participant_id,
            "game_id": game_id,
            "user_id": user_id,
            "position": position,
            "position_type": position_type,
            "joined_at": datetime.now(UTC),
        },
    )
    admin_db_sync.commit()
    return participant_id


def test_remove_participant_enqueues_player_removed_row(
    admin_db_sync,
    create_user,
    create_guild,
    create_channel,
    create_template,
    seed_redis_cache,
    create_authenticated_client,
):
    """PUT /api/v1/games/{id} with removed_participant_ids creates a player_removed row."""
    ctx = _make_context(
        create_guild,
        create_channel,
        create_user,
        create_template,
        seed_redis_cache,
        guild_discord_id="762222222222222222",
        channel_discord_id="762222222222222223",
    )
    client = create_authenticated_client(TEST_DISCORD_TOKEN, TEST_BOT_DISCORD_ID)

    scheduled_at = (datetime.now(UTC) + timedelta(days=1)).isoformat()
    create_resp = client.post(
        "/api/v1/games",
        data={
            "template_id": ctx["template_id"],
            "title": "INT_TEST Player Remove Game",
            "scheduled_at": scheduled_at,
        },
    )
    assert create_resp.status_code in (200, 201), f"Create failed: {create_resp.text}"
    game_id = create_resp.json()["id"]

    player = create_user()
    participant_id = _insert_participant(admin_db_sync, game_id, player["id"], position=1)

    update_resp = client.put(
        f"/api/v1/games/{game_id}",
        data={"removed_participant_ids": json.dumps([participant_id])},
    )
    assert update_resp.status_code == 200, f"Update failed: {update_resp.text}"

    queue_row = admin_db_sync.execute(
        text(
            "SELECT action_type, game_id FROM bot_action_queue "
            "WHERE action_type = 'player_removed' AND game_id = :game_id"
        ),
        {"game_id": game_id},
    ).fetchone()
    assert queue_row is not None, "No player_removed row found in bot_action_queue"
    assert queue_row[1] == game_id


def test_removing_confirmed_player_enqueues_waitlist_promotion_dm(
    admin_db_sync,
    create_user,
    create_guild,
    create_channel,
    create_template,
    seed_redis_cache,
    create_authenticated_client,
):
    """
    Removing the only confirmed player from a HOST_SELECTED_WITH_WAITLIST game
    (max_players=1) promotes the waitlisted player and enqueues a send_dm row.
    """
    ctx = _make_context(
        create_guild,
        create_channel,
        create_user,
        create_template,
        seed_redis_cache,
        guild_discord_id="763333333333333333",
        channel_discord_id="763333333333333334",
        allowed_signup_methods=[SignupMethod.HOST_SELECTED_WITH_WAITLIST.value],
        default_signup_method=SignupMethod.HOST_SELECTED_WITH_WAITLIST.value,
    )
    client = create_authenticated_client(TEST_DISCORD_TOKEN, TEST_BOT_DISCORD_ID)

    scheduled_at = (datetime.now(UTC) + timedelta(days=1)).isoformat()
    create_resp = client.post(
        "/api/v1/games",
        data={
            "template_id": ctx["template_id"],
            "title": "INT_TEST Waitlist Promotion Game",
            "scheduled_at": scheduled_at,
            "signup_method": SignupMethod.HOST_SELECTED_WITH_WAITLIST.value,
            "max_players": "1",
        },
    )
    assert create_resp.status_code in (200, 201), f"Create failed: {create_resp.text}"
    game_id = create_resp.json()["id"]

    confirmed_user = create_user()
    waitlisted_user = create_user()

    confirmed_participant_id = _insert_participant(
        admin_db_sync,
        game_id,
        confirmed_user["id"],
        position=1,
        position_type=ParticipantType.HOST_ADDED,
    )
    _insert_participant(
        admin_db_sync,
        game_id,
        waitlisted_user["id"],
        position=2,
        position_type=ParticipantType.HOST_ADDED,
    )

    update_resp = client.put(
        f"/api/v1/games/{game_id}",
        data={"removed_participant_ids": json.dumps([confirmed_participant_id])},
    )
    assert update_resp.status_code == 200, f"Update failed: {update_resp.text}"

    dm_rows = admin_db_sync.execute(
        text(
            "SELECT action_type, discord_id, payload FROM bot_action_queue "
            "WHERE action_type = 'send_dm' AND game_id = :game_id"
        ),
        {"game_id": game_id},
    ).fetchall()

    assert len(dm_rows) >= 1, "No send_dm row found in bot_action_queue after promotion"
    payloads = [row[2] for row in dm_rows]
    assert any(p.get("notification_type") == "waitlist_promotion" for p in payloads), (
        f"Expected waitlist_promotion send_dm but got: {payloads}"
    )
    discord_ids = [
        row[1] for row in dm_rows if row[2].get("notification_type") == "waitlist_promotion"
    ]
    assert waitlisted_user["discord_id"] in discord_ids, (
        "send_dm must target the promoted waitlisted user"
    )
