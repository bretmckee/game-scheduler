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


"""Integration tests for GET /api/v1/games/{game_id}/participant-seats.

Covers the host-selected seating endpoint end-to-end against real Postgres,
Redis projection data, and session-cookie auth (see
services/api/routes/games.py::get_participant_seats):

- Only participants with a linked Discord user appear; placeholder seats
  (user_id NULL) are excluded from the response entirely and positions run
  consecutively from 1 over real users alone - including across the
  confirmed/waitlist boundary.
- Names come from the member projection primary name (global_name, falling
  back to username); guild nicknames are never used. Members missing from
  the projection resolve to "Unknown User".
- Authorization: unauthenticated requests get 401; authenticated guild
  members who are neither the host nor a configured bot manager get 403;
  a non-host holding a configured bot manager role gets 200.

Placeholder rows must be inserted directly into game_participants because
the create-game API path does not accept placeholder entries.
"""

import uuid
from datetime import UTC, datetime, timedelta

import httpx
import pytest
from sqlalchemy import text

from shared.cache.client import RedisClient
from shared.cache.keys import CacheKeys
from shared.models.participant import UNPOSITIONED_SENTINEL, ParticipantType
from tests.shared.auth_helpers import cleanup_test_session, create_test_session

pytestmark = pytest.mark.integration

# Fixed identities so the same constants can be reused by every test; the
# function-scoped admin_db_sync fixture wipes all tables at the start of each
# test, so unique-constraint collisions across tests cannot occur.
FAKE_DISCORD_TOKEN = "MTQ0NDA3ODM4NjM4MDAxMzY0OA.GvmbbW.fake_token_for_integration_tests"
HOST_DISCORD_ID = "610000000000000001"
PLAYER_A_DISCORD_ID = "610000000000000002"
PLAYER_B_DISCORD_ID = "610000000000000003"
PLAYER_C_DISCORD_ID = "610000000000000004"
MANAGER_DISCORD_ID = "610000000000000005"
OUTSIDER_DISCORD_ID = "610000000000000009"
BOT_MANAGER_ROLE_ID = "950000000000000001"

# Matches proj:gen written by seed_bot_freshness / seed_redis_cache.
PROJECTION_GEN = "1"


# ============================================================================
# Helpers
# ============================================================================


async def _seed_member_projection(
    guild_discord_id: str, user_discord_id: str, member: dict
) -> None:
    """Seed one projection member key for primary-name resolution."""
    redis_client = RedisClient()
    await redis_client.connect()
    try:
        await redis_client.set_json(
            CacheKeys.proj_member(PROJECTION_GEN, guild_discord_id, user_discord_id), member
        )
    finally:
        await redis_client.disconnect()


def _add_participant(
    admin_db_sync,
    game_session_id: str,
    *,
    user_row: dict | None,
    display_name: str | None,
    position_type: int,
    position: int,
    joined_at: datetime,
) -> str:
    """Insert a participant row directly (bypassing RLS) and return its id.

    Placeholder rows pass user_row=None with a non-NULL display_name; linked
    rows pass the users-row dict and must leave display_name NULL per the
    CHECK constraint on game_participants.
    """
    assert (user_row is None) == (display_name is not None)
    participant_id = str(uuid.uuid4())
    admin_db_sync.execute(
        text(
            "INSERT INTO game_participants "
            "(id, game_session_id, user_id, display_name, joined_at, "
            "position_type, position) "
            "VALUES (:id, :game_session_id, :user_id, :display_name, :joined_at, "
            ":position_type, :position)"
        ),
        {
            "id": participant_id,
            "game_session_id": game_session_id,
            "user_id": user_row["id"] if user_row else None,
            "display_name": display_name,
            "joined_at": joined_at,
            "position_type": position_type,
            "position": position,
        },
    )
    admin_db_sync.commit()
    return participant_id


async def _setup_environment(
    create_user,
    create_guild,
    create_channel,
    create_template,
    seed_redis_cache,
    *,
    max_players: int = 3,
    extra_member_discord_ids: tuple[str, ...] = (),
    manager_member_discord_ids: tuple[str, ...] = (),
) -> dict:
    """Create the guild/channel/users/template and Redis state for one test.

    The host is seeded with the bot-manager role so POST /api/v1/games passes
    its host-permission gate (same pattern as test_games_crud.py). Regular
    members get default membership-only roles; ids in
    manager_member_discord_ids additionally receive the configured bot-manager
    role so their can_manage outcome exercises the role-match branch
    deterministically.
    """
    guild = create_guild(bot_manager_roles=[BOT_MANAGER_ROLE_ID])
    channel = create_channel(guild_id=guild["id"])
    host = create_user(discord_user_id=HOST_DISCORD_ID)
    member_rows = [create_user(discord_user_id=m) for m in extra_member_discord_ids]
    template = create_template(
        guild_id=guild["id"],
        channel_id=channel["id"],
        max_players=max_players,
        allowed_signup_methods=["HOST_SELECTED"],
        default_signup_method="HOST_SELECTED",
    )

    await seed_redis_cache(
        user_discord_id=host["discord_id"],
        guild_discord_id=guild["guild_id"],
        channel_discord_id=channel["channel_id"],
        user_roles=[BOT_MANAGER_ROLE_ID],
    )
    for row in member_rows:
        if row["discord_id"] in manager_member_discord_ids:
            roles = [BOT_MANAGER_ROLE_ID]
        else:
            roles = None
        await seed_redis_cache(
            user_discord_id=row["discord_id"],
            guild_discord_id=guild["guild_id"],
            channel_discord_id=channel["channel_id"],
            user_roles=roles,
        )

    return {
        "guild_db_id": guild["id"],
        "guild_discord_id": guild["guild_id"],
        "template_id": template["id"],
        "host_user_row": host,
        "member_user_rows": {row["discord_id"]: row for row in member_rows},
    }


async def _create_game_via_api(client: httpx.AsyncClient, ctx: dict) -> dict:
    """Create a HOST_SELECTED game through the API and return its JSON."""
    scheduled_at = (datetime.now(UTC) + timedelta(hours=2)).isoformat()
    response = await client.post(
        "/api/v1/games",
        data={
            "template_id": ctx["template_id"],
            "title": "Host Selected Game",
            "scheduled_at": scheduled_at,
            "signup_method": "HOST_SELECTED",
        },
    )
    assert response.status_code == 201, f"Game creation failed: {response.text}"
    return response.json()


# ============================================================================
# Seat listing behavior
# ============================================================================


@pytest.mark.asyncio
async def test_host_sees_linked_users_only_with_consecutive_positions(
    create_user,
    create_guild,
    create_channel,
    create_template,
    seed_redis_cache,
    admin_db_sync,
    api_base_url,
):
    """Host gets real users only: placeholders excluded, positions consecutive.

    With max_players=3 the seat order is [A, placeholder, B] confirmed and C
    waitlisted, so the response must number A=1, B=2, C=3 even though a
    placeholder sits inside the confirmed slice. Names exercise primary-name
    resolution against seeded projection data (nick present but ignored),
    username fallback when global_name is null, and "Unknown User" for a
    member missing from the projection.
    """
    ctx = await _setup_environment(
        create_user,
        create_guild,
        create_channel,
        create_template,
        seed_redis_cache,
        extra_member_discord_ids=(
            PLAYER_A_DISCORD_ID,
            PLAYER_B_DISCORD_ID,
            PLAYER_C_DISCORD_ID,
        ),
    )
    session_token, _ = await create_test_session(FAKE_DISCORD_TOKEN, HOST_DISCORD_ID)
    base_now = datetime.now(UTC)
    try:
        async with httpx.AsyncClient(
            base_url=api_base_url, timeout=30.0, cookies={"session_token": session_token}
        ) as client:
            game = await _create_game_via_api(client, ctx)

            # Confirmed window holds [A, placeholder] plus B at max_players=3;
            # C lands on the waitlist - all four rows exist in this order after
            # sorting by (position_type, position, joined_at).
            user_a = ctx["member_user_rows"][PLAYER_A_DISCORD_ID]
            user_b = ctx["member_user_rows"][PLAYER_B_DISCORD_ID]
            user_c = ctx["member_user_rows"][PLAYER_C_DISCORD_ID]
            _add_participant(
                admin_db_sync,
                game["id"],
                user_row=user_a,
                display_name=None,
                position_type=int(ParticipantType.HOST_ADDED),
                position=0,
                joined_at=base_now - timedelta(hours=5),
            )
            _add_participant(
                admin_db_sync,
                game["id"],
                user_row=None,
                display_name="TBD slot",
                position_type=int(ParticipantType.HOST_ADDED),
                position=1,
                joined_at=base_now - timedelta(hours=4),
            )
            _add_participant(
                admin_db_sync,
                game["id"],
                user_row=user_b,
                display_name=None,
                position_type=int(ParticipantType.SELF_ADDED),
                position=UNPOSITIONED_SENTINEL,
                joined_at=base_now - timedelta(hours=3),
            )
            _add_participant(
                admin_db_sync,
                game["id"],
                user_row=user_c,
                display_name=None,
                position_type=int(ParticipantType.SELF_ADDED),
                position=UNPOSITIONED_SENTINEL,
                joined_at=base_now - timedelta(hours=2),
            )

            guild_discord_id = ctx["guild_discord_id"]
            # Nick is deliberately different from global_name: primary names must
            # never use the nick. B has no global_name so it falls back to username.
            await _seed_member_projection(
                guild_discord_id,
                PLAYER_A_DISCORD_ID,
                {"nick": "AlphaNick", "global_name": "Global Alpha", "username": "alpha"},
            )
            await _seed_member_projection(
                guild_discord_id,
                PLAYER_B_DISCORD_ID,
                {"nick": None, "global_name": None, "username": "bravo"},
            )
            # C intentionally absent from the projection -> "Unknown User".

            response = await client.get(f"/api/v1/games/{game['id']}/participant-seats")

        assert response.status_code == 200, (
            f"Expected 200, got {response.status_code}: {response.text}"
        )
        seats = response.json()["seats"]

        # Placeholder excluded entirely; numbering runs consecutively over real
        # users and continues across the confirmed/waitlist boundary.
        assert [seat["position"] for seat in seats] == [1, 2, 3], (
            f"Expected consecutive positions [1, 2, 3], got {seats}"
        )
        assert [seat["discord_id"] for seat in seats] == [
            PLAYER_A_DISCORD_ID,
            PLAYER_B_DISCORD_ID,
            PLAYER_C_DISCORD_ID,
        ]
        assert [seat["name"] for seat in seats] == ["Global Alpha", "bravo", "Unknown User"], (
            f"Primary names resolved incorrectly: {seats}"
        )
    finally:
        await cleanup_test_session(session_token)


@pytest.mark.asyncio
async def test_placeholders_only_game_returns_empty_seats(
    create_user,
    create_guild,
    create_channel,
    create_template,
    seed_redis_cache,
    admin_db_sync,
    api_base_url,
):
    """A game with only placeholder rows returns 200 with an empty seat list."""
    ctx = await _setup_environment(
        create_user,
        create_guild,
        create_channel,
        create_template,
        seed_redis_cache,
        max_players=4,
    )
    session_token, _ = await create_test_session(FAKE_DISCORD_TOKEN, HOST_DISCORD_ID)
    try:
        async with httpx.AsyncClient(
            base_url=api_base_url, timeout=30.0, cookies={"session_token": session_token}
        ) as client:
            game = await _create_game_via_api(client, ctx)

            now = datetime.now(UTC)
            for index, name in enumerate(("Seat One", "Host friend TBD")):
                _add_participant(
                    admin_db_sync,
                    game["id"],
                    user_row=None,
                    display_name=name,
                    position_type=int(ParticipantType.HOST_ADDED),
                    position=index,
                    joined_at=now - timedelta(minutes=10 * (index + 1)),
                )

            response = await client.get(f"/api/v1/games/{game['id']}/participant-seats")

        assert response.status_code == 200, (
            f"Expected 200, got {response.status_code}: {response.text}"
        )
        # No linked users at all -> the seat list is empty, not placeholders.
        assert response.json()["seats"] == []
    finally:
        await cleanup_test_session(session_token)


# ============================================================================
# Authorization
# ============================================================================


@pytest.mark.asyncio
async def test_non_host_member_forbidden_and_anonymous_unauthorized(
    create_user,
    create_guild,
    create_channel,
    create_template,
    seed_redis_cache,
    api_base_url,
):
    """A guild member who is not the host or a manager gets 403; no session 401."""
    ctx = await _setup_environment(
        create_user,
        create_guild,
        create_channel,
        create_template,
        seed_redis_cache,
        extra_member_discord_ids=(OUTSIDER_DISCORD_ID,),
    )
    host_session, _ = await create_test_session(FAKE_DISCORD_TOKEN, HOST_DISCORD_ID)
    member_session, _ = await create_test_session(FAKE_DISCORD_TOKEN, OUTSIDER_DISCORD_ID)
    try:
        async with httpx.AsyncClient(
            base_url=api_base_url, timeout=30.0, cookies={"session_token": host_session}
        ) as host_client:
            game = await _create_game_via_api(host_client, ctx)

        # Guild member without the configured bot-manager role: passes access,
        # fails can_manage -> deterministic 403 (guild has explicit
        # bot_manager_role_ids, so no permission-bit fallback applies).
        async with httpx.AsyncClient(
            base_url=api_base_url, timeout=30.0, cookies={"session_token": member_session}
        ) as member_client:
            response = await member_client.get(f"/api/v1/games/{game['id']}/participant-seats")
        assert response.status_code == 403, (
            f"Expected 403, got {response.status_code}: {response.text}"
        )
        assert response.json()["detail"] == (
            "Only the host or a server manager can view participant seats."
        )

        # Anonymous callers are rejected before any game lookup happens.
        async with httpx.AsyncClient(base_url=api_base_url, timeout=30.0) as anonymous_client:
            anonymous_response = await anonymous_client.get(
                f"/api/v1/games/{game['id']}/participant-seats"
            )
        assert anonymous_response.status_code == 401
    finally:
        await cleanup_test_session(host_session)
        await cleanup_test_session(member_session)


@pytest.mark.asyncio
async def test_bot_manager_other_than_host_can_view_seats(
    create_user,
    create_guild,
    create_channel,
    create_template,
    seed_redis_cache,
    admin_db_sync,
    api_base_url,
):
    """A non-host holding a configured bot-manager role gets 200 with real seats."""
    ctx = await _setup_environment(
        create_user,
        create_guild,
        create_channel,
        create_template,
        seed_redis_cache,
        extra_member_discord_ids=(MANAGER_DISCORD_ID, PLAYER_A_DISCORD_ID),
        manager_member_discord_ids=(MANAGER_DISCORD_ID,),
    )
    host_session, _ = await create_test_session(FAKE_DISCORD_TOKEN, HOST_DISCORD_ID)
    manager_session, _ = await create_test_session(FAKE_DISCORD_TOKEN, MANAGER_DISCORD_ID)
    try:
        async with httpx.AsyncClient(
            base_url=api_base_url, timeout=30.0, cookies={"session_token": host_session}
        ) as host_client:
            game = await _create_game_via_api(host_client, ctx)

        user_a = ctx["member_user_rows"][PLAYER_A_DISCORD_ID]
        _add_participant(
            admin_db_sync,
            game["id"],
            user_row=user_a,
            display_name=None,
            position_type=int(ParticipantType.HOST_ADDED),
            position=0,
            joined_at=datetime.now(UTC),
        )
        await _seed_member_projection(
            ctx["guild_discord_id"],
            PLAYER_A_DISCORD_ID,
            {"nick": None, "global_name": "Global Alpha", "username": "alpha"},
        )

        # The caller is not the host; access hinges on the configured bot-manager role.
        async with httpx.AsyncClient(
            base_url=api_base_url, timeout=30.0, cookies={"session_token": manager_session}
        ) as manager_client:
            response = await manager_client.get(f"/api/v1/games/{game['id']}/participant-seats")

        assert response.status_code == 200, (
            f"Expected 200, got {response.status_code}: {response.text}"
        )
        seats = response.json()["seats"]
        assert [seat["position"] for seat in seats] == [1]
        assert seats[0]["discord_id"] == PLAYER_A_DISCORD_ID
        assert seats[0]["name"] == "Global Alpha"
    finally:
        await cleanup_test_session(host_session)
        await cleanup_test_session(manager_session)
