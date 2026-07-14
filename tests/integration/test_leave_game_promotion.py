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


"""Integration test for Flow: voluntary leave via the API triggers waitlist promotion.

POST /api/v1/games/{id}/leave on a HOST_SELECTED_WITH_WAITLIST game (max_players=1)
must promote the waitlisted participant and enqueue a waitlist_promotion send_dm row,
the same way the host-edit path (PUT /api/v1/games/{id}) already does.
"""

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
PLAYER_FAKE_TOKEN = "MTQ0NDA3ODM4NjM4MDAxMzY0OA.GvmbbW.fake_token_for_leaving_player"
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


def test_confirmed_leave_via_api_promotes_waitlisted_participant(
    admin_db_sync,
    create_user,
    create_guild,
    create_channel,
    create_template,
    seed_redis_cache,
    create_authenticated_client,
):
    """
    A confirmed participant voluntarily leaving via POST /{game_id}/leave promotes
    the waitlisted participant in a HOST_SELECTED_WITH_WAITLIST game (max_players=1).
    """
    ctx = _make_context(
        create_guild,
        create_channel,
        create_user,
        create_template,
        seed_redis_cache,
        guild_discord_id="764444444444444444",
        channel_discord_id="764444444444444445",
        allowed_signup_methods=[SignupMethod.HOST_SELECTED_WITH_WAITLIST.value],
        default_signup_method=SignupMethod.HOST_SELECTED_WITH_WAITLIST.value,
    )

    confirmed_user = create_user()
    waitlisted_user = create_user()

    # RLS requires the acting user's guild membership to be cached, otherwise
    # get_db_with_user_guilds() resolves an empty guild list and the game is
    # invisible to this session ("Game not found") even though it exists. Seed
    # this before any create_authenticated_client() call: that factory creates
    # and closes its own event loop, and seed_redis_cache's sync wrapper reuses
    # asyncio.get_event_loop() — calling it afterward hits a closed loop.
    seed_redis_cache(
        user_discord_id=confirmed_user["discord_id"],
        guild_discord_id="764444444444444444",
        channel_discord_id="764444444444444445",
    )

    bot_manager_client = create_authenticated_client(TEST_DISCORD_TOKEN, TEST_BOT_DISCORD_ID)

    scheduled_at = (datetime.now(UTC) + timedelta(days=1)).isoformat()
    create_resp = bot_manager_client.post(
        "/api/v1/games",
        data={
            "template_id": ctx["template_id"],
            "title": "INT_TEST Leave Promotion Game",
            "scheduled_at": scheduled_at,
            "signup_method": SignupMethod.HOST_SELECTED_WITH_WAITLIST.value,
            "max_players": "1",
        },
    )
    assert create_resp.status_code in (200, 201), f"Create failed: {create_resp.text}"
    game_id = create_resp.json()["id"]

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

    confirmed_client = create_authenticated_client(PLAYER_FAKE_TOKEN, confirmed_user["discord_id"])
    leave_resp = confirmed_client.post(f"/api/v1/games/{game_id}/leave")
    assert leave_resp.status_code == 204, f"Leave failed: {leave_resp.text}"

    participant_row = admin_db_sync.execute(
        text("SELECT id FROM game_participants WHERE id = :id"),
        {"id": confirmed_participant_id},
    ).fetchone()
    assert participant_row is None, "Confirmed participant must be deleted after leaving"

    dm_rows = admin_db_sync.execute(
        text(
            "SELECT action_type, discord_id, payload FROM bot_action_queue "
            "WHERE action_type = 'send_dm' AND game_id = :game_id"
        ),
        {"game_id": game_id},
    ).fetchall()

    assert len(dm_rows) >= 1, "No send_dm row found in bot_action_queue after leave"
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
