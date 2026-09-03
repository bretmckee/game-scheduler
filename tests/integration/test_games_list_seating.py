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


"""Integration tests for per-participant seating on GET /api/v1/games (list).

The My Games / Browse list cards render a caller's confirmed-vs-waitlisted state
as a color-blind-safe status border (solid when seated, dashed when waitlisted).
That visual depends entirely on the list response already carrying the partitioned
participant arrays (``confirmed_participants`` / ``waitlist_participants``) for each
game - even though the list route builds responses with ``resolve_participants=False``.

These tests lock that data contract end-to-end against real Postgres + Redis + the
running API: with a host-selected game at capacity, a confirmed participant must be
reported under ``confirmed_participants`` and an overflow participant under
``waitlist_participants`` in the *caller's own* list view. Direct row inserts are used
because the create-game path does not accept pre-seated participants (see
test_participant_seats_endpoint.py).
"""

import uuid
from datetime import UTC, datetime, timedelta

import httpx
import pytest
from sqlalchemy import text

from shared.models.participant import UNPOSITIONED_SENTINEL, ParticipantType
from tests.shared.auth_helpers import cleanup_test_session, create_test_session

pytestmark = pytest.mark.integration

# Fixed identities reused across every test; tables are wiped per test so no
# cross-test unique-constraint collisions can occur.
FAKE_DISCORD_TOKEN = "MTQ0NDA3ODM4NjM4MDAxMzY0OA.GvmbbW.fake_token_for_integration_tests"
HOST_DISCORD_ID = "621000000000000001"
PLAYER_A_DISCORD_ID = "621000000000000002"  # seated (within max_players)
PLAYER_B_DISCORD_ID = "621000000000000003"  # seated (within max_players)
PLAYER_C_DISCORD_ID = "621000000000000004"  # overflow / waitlisted
BOT_MANAGER_ROLE_ID = "951000000000000001"


def _add_participant(
    admin_db_sync,
    game_session_id: str,
    *,
    user_row: dict | None,
    position_type: int,
    position: int,
    joined_at: datetime,
) -> str:
    """Insert a linked participant row directly (bypassing RLS) and return its id.

    Mirrors the helper in test_participant_seats_endpoint.py; display_name must be
    NULL for linked rows per the CHECK constraint on game_participants.
    """
    assert user_row is not None
    participant_id = str(uuid.uuid4())
    admin_db_sync.execute(
        text(
            "INSERT INTO game_participants "
            "(id, game_session_id, user_id, display_name, joined_at, "
            "position_type, position) "
            "VALUES (:id, :game_session_id, :user_id, NULL, :joined_at, "
            ":position_type, :position)"
        ),
        {
            "id": participant_id,
            "game_session_id": game_session_id,
            "user_id": user_row["id"],
            "joined_at": joined_at,
            "position_type": position_type,
            "position": position,
        },
    )
    admin_db_sync.commit()
    return participant_id


async def _setup_and_create_game(
    create_user,
    create_guild,
    create_channel,
    create_template,
    seed_redis_cache,
    client: httpx.AsyncClient,
    *,
    max_players: int,
) -> tuple[dict, dict]:
    """Build guild/channel/users/template + Redis membership and a HOST_SELECTED game.

    Returns (context, created_game_json). The host is seeded with the bot-manager role
    so POST /api/v1/games passes its host-permission gate; players are regular members
    so they pass verify_game_access on subsequent list calls.
    """
    guild = create_guild(bot_manager_roles=[BOT_MANAGER_ROLE_ID])
    channel = create_channel(guild_id=guild["id"])
    host = create_user(discord_user_id=HOST_DISCORD_ID)
    player_a = create_user(discord_user_id=PLAYER_A_DISCORD_ID)
    player_b = create_user(discord_user_id=PLAYER_B_DISCORD_ID)
    player_c = create_user(discord_user_id=PLAYER_C_DISCORD_ID)

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
    for member in (player_a, player_b, player_c):
        await seed_redis_cache(
            user_discord_id=member["discord_id"],
            guild_discord_id=guild["guild_id"],
            channel_discord_id=channel["channel_id"],
            user_roles=None,  # regular membership-only roles
        )

    response = await client.post(
        "/api/v1/games",
        data={
            "template_id": template["id"],
            "title": "List Seating Game",
            "scheduled_at": (datetime.now(UTC) + timedelta(hours=24)).isoformat(),
            "signup_method": "HOST_SELECTED",
        },
    )
    assert response.status_code == 201, f"Game creation failed: {response.text}"

    ctx = {
        "guild_discord_id": guild["guild_id"],
        "players": {
            PLAYER_A_DISCORD_ID: player_a,
            PLAYER_B_DISCORD_ID: player_b,
            PLAYER_C_DISCORD_ID: player_c,
        },
    }
    return ctx, response.json()


async def _list_games_for(client: httpx.AsyncClient) -> dict:
    """Call the list endpoint as the current caller and return parsed JSON."""
    response = await client.get("/api/v1/games", params={"role": "participant"})
    assert response.status_code == 200, (
        f"Expected 200 from GET /api/v1/games?role=participant, got "
        f"{response.status_code}: {response.text}"
    )
    return response.json()


@pytest.mark.asyncio
async def test_list_endpoint_exposes_confirmed_vs_waitlist_seating(
    create_user,
    create_guild,
    create_channel,
    create_template,
    seed_redis_cache,
    admin_db_sync,
    api_base_url,
):
    """A seated caller is in confirmed_participants; an overflow caller is on the waitlist.

    With max_players=2 and three self-added participants joined A < B < C, partitioning
    yields confirmed=[A, B], waitlist=[C]. The *caller-specific* list view must report
    each accordingly so the UI can render a solid border for A/B and dashed for C.
    """
    base_now = datetime.now(UTC)

    # POST /api/v1/games requires host permission, so seed + create under the host session.
    token_host, _ = await create_test_session(FAKE_DISCORD_TOKEN, HOST_DISCORD_ID)
    tokens: dict[str, str] = {}
    cleanup_targets: list[str] = [token_host]

    try:
        # Step 1: host creates the game + seeds all three participants.
        async with httpx.AsyncClient(
            base_url=api_base_url,
            timeout=30.0,
            cookies={"session_token": token_host},
        ) as host_client:
            ctx, game = await _setup_and_create_game(
                create_user,
                create_guild,
                create_channel,
                create_template,
                seed_redis_cache,
                host_client,
                max_players=2,
            )

            user_a = ctx["players"][PLAYER_A_DISCORD_ID]
            user_b = ctx["players"][PLAYER_B_DISCORD_ID]
            user_c = ctx["players"][PLAYER_C_DISCORD_ID]
            # All self-added at the unpositioned sentinel slot; ordering falls back to
            # joined_at (A < B < C), so with max_players=2 we get confirmed=[A, B], waitlist=[C].
            _add_participant(
                admin_db_sync,
                game["id"],
                user_row=user_a,
                position_type=int(ParticipantType.SELF_ADDED),
                position=UNPOSITIONED_SENTINEL,
                joined_at=base_now - timedelta(hours=5),
            )
            _add_participant(
                admin_db_sync,
                game["id"],
                user_row=user_b,
                position_type=int(ParticipantType.SELF_ADDED),
                position=UNPOSITIONED_SENTINEL,
                joined_at=base_now - timedelta(hours=4),
            )
            _add_participant(
                admin_db_sync,
                game["id"],
                user_row=user_c,
                position_type=int(ParticipantType.SELF_ADDED),
                position=UNPOSITIONED_SENTINEL,
                joined_at=base_now - timedelta(hours=3),
            )

        def discord_ids(bucket: list[dict]) -> set[str]:
            return {p["discord_id"] for p in bucket}

        async def assert_caller_view(actor_discord_id: str) -> None:
            token_actor, _ = await create_test_session(FAKE_DISCORD_TOKEN, actor_discord_id)
            tokens[actor_discord_id] = token_actor
            cleanup_targets.append(token_actor)

            async with httpx.AsyncClient(
                base_url=api_base_url,
                timeout=30.0,
                cookies={"session_token": token_actor},
            ) as actor_client:
                payload = await _list_games_for(actor_client)

            games = payload.get("games", [])
            match = next((g for g in games if g["id"] == game["id"]), None)
            assert match is not None, (
                f"Caller {actor_discord_id} should see the shared SCHEDULED game in their "
                f"participant list; got ids {[g['id'] for g in games]}"
            )

            # Contract presence on the list item itself.
            assert "confirmed_participants" in match
            assert "waitlist_participants" in match
            confirmed_ids = discord_ids(match["confirmed_participants"])
            waitlist_ids = discord_ids(match["waitlist_participants"])

            # Partition is deterministic from the seeded rows: A & B seated, C overflow.
            expected_confirmed = {PLAYER_A_DISCORD_ID, PLAYER_B_DISCORD_ID}
            expected_waitlist = {PLAYER_C_DISCORD_ID}
            assert confirmed_ids == expected_confirmed, (
                f"Expected confirmed={sorted(expected_confirmed)}, got {sorted(confirmed_ids)}"
            )
            assert waitlist_ids == expected_waitlist, (
                f"Expected waitlist={sorted(expected_waitlist)}, got {sorted(waitlist_ids)}"
            )

        # The caller's own relationship must be reflected correctly for both states.
        await assert_caller_view(PLAYER_A_DISCORD_ID)  # seated -> solid border source
        await assert_caller_view(PLAYER_C_DISCORD_ID)  # waitlisted -> dashed border source

    finally:
        for token in cleanup_targets:
            await cleanup_test_session(token)
