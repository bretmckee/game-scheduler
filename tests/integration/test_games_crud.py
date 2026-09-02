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


"""Integration tests for games CRUD route coverage.

Covers list_games, get_game, update_game, delete_game, join_game, and leave_game
endpoints in services/api/routes/games.py.  Specifically targets the error paths
and optional form-field handling that are missing from existing tests.
"""

import json
import uuid
from datetime import UTC, datetime, timedelta

import httpx
import pytest
from sqlalchemy import text

from shared.utils.discord_tokens import extract_bot_discord_id
from tests.shared.auth_helpers import cleanup_test_session, create_test_session

pytestmark = pytest.mark.integration

TEST_DISCORD_TOKEN = "MTQ0NDA3ODM4NjM4MDAxMzY0OA.GvmbbW.fake_token_for_integration_tests"
TEST_BOT_DISCORD_ID = extract_bot_discord_id(TEST_DISCORD_TOKEN)
BOT_MANAGER_ROLE_ID = "123456789012345678"


async def _setup_game_context(
    create_user,
    create_guild,
    create_channel,
    create_template,
    seed_redis_cache,
    allowed_signup_methods: list[str] | None = None,
) -> dict:
    """Create guild/channel/user/template and seed Redis for game tests."""
    guild = create_guild(bot_manager_roles=[BOT_MANAGER_ROLE_ID])
    channel = create_channel(guild_id=guild["id"])
    user = create_user(discord_user_id=TEST_BOT_DISCORD_ID)
    template = create_template(
        guild_id=guild["id"],
        channel_id=channel["id"],
        allowed_signup_methods=allowed_signup_methods,
    )

    await seed_redis_cache(
        user_discord_id=TEST_BOT_DISCORD_ID,
        guild_discord_id=guild["guild_id"],
        channel_discord_id=channel["channel_id"],
        user_roles=[BOT_MANAGER_ROLE_ID],
    )

    return {
        "guild_id": guild["id"],
        "guild_discord_id": guild["guild_id"],
        "channel_id": channel["id"],
        "channel_discord_id": channel["channel_id"],
        "user_id": user["id"],
        "template_id": template["id"],
    }


async def _create_game_via_api(
    client: httpx.AsyncClient,
    ctx: dict,
    title: str = "Test Game",
    signup_method: str | None = None,
) -> dict:
    """Create a game through the API and return the response JSON."""
    scheduled_at = (datetime.now(UTC) + timedelta(hours=2)).isoformat()
    data = {
        "template_id": ctx["template_id"],
        "title": title,
        "scheduled_at": scheduled_at,
    }
    if signup_method is not None:
        data["signup_method"] = signup_method
    response = await client.post("/api/v1/games", data=data)
    assert response.status_code == 201, f"Game creation failed: {response.text}"
    return response.json()


# ============================================================================
# create_game image handling (lines 75-88, 326-352, 366-369)
# ============================================================================


@pytest.mark.asyncio
async def test_create_game_thumbnail_too_large_returns_400(
    create_user,
    create_guild,
    create_channel,
    create_template,
    seed_redis_cache,
    api_base_url,
):
    """POST /api/v1/games with a thumbnail exceeding 5 MB returns 400 (line 88)."""
    ctx = await _setup_game_context(
        create_user, create_guild, create_channel, create_template, seed_redis_cache
    )
    session_token, _ = await create_test_session(TEST_DISCORD_TOKEN, TEST_BOT_DISCORD_ID)

    try:
        async with httpx.AsyncClient(
            base_url=api_base_url,
            timeout=30.0,
            cookies={"session_token": session_token},
        ) as client:
            scheduled_at = (datetime.now(UTC) + timedelta(hours=2)).isoformat()
            big_file = b"\x89PNG" + b"\x00" * (5 * 1024 * 1024 + 1)
            response = await client.post(
                "/api/v1/games",
                data={
                    "template_id": ctx["template_id"],
                    "title": "Big Thumbnail Game",
                    "scheduled_at": scheduled_at,
                },
                files={"thumbnail": ("big.png", big_file, "image/png")},
            )

        assert response.status_code == 400, (
            f"Expected 400, got {response.status_code}: {response.text}"
        )
    finally:
        await cleanup_test_session(session_token)


@pytest.mark.asyncio
async def test_create_game_with_banner_image(
    create_user,
    create_guild,
    create_channel,
    create_template,
    seed_redis_cache,
    api_base_url,
):
    """POST /api/v1/games with a banner image stores it (lines 343-352)."""
    ctx = await _setup_game_context(
        create_user, create_guild, create_channel, create_template, seed_redis_cache
    )
    session_token, _ = await create_test_session(TEST_DISCORD_TOKEN, TEST_BOT_DISCORD_ID)

    try:
        async with httpx.AsyncClient(
            base_url=api_base_url,
            timeout=10.0,
            cookies={"session_token": session_token},
        ) as client:
            scheduled_at = (datetime.now(UTC) + timedelta(hours=2)).isoformat()
            response = await client.post(
                "/api/v1/games",
                data={
                    "template_id": ctx["template_id"],
                    "title": "Banner Game",
                    "scheduled_at": scheduled_at,
                },
                files={"image": ("banner.png", b"\x89PNG\r\n\x1a\n", "image/png")},
            )

        assert response.status_code == 201, (
            f"Expected 201, got {response.status_code}: {response.text}"
        )
    finally:
        await cleanup_test_session(session_token)


@pytest.mark.asyncio
async def test_create_game_with_thumbnail(
    create_user,
    create_guild,
    create_channel,
    create_template,
    seed_redis_cache,
    api_base_url,
):
    """POST /api/v1/games with a valid PNG thumbnail stores the image (lines 326-335)."""
    ctx = await _setup_game_context(
        create_user, create_guild, create_channel, create_template, seed_redis_cache
    )
    session_token, _ = await create_test_session(TEST_DISCORD_TOKEN, TEST_BOT_DISCORD_ID)

    try:
        async with httpx.AsyncClient(
            base_url=api_base_url,
            timeout=10.0,
            cookies={"session_token": session_token},
        ) as client:
            scheduled_at = (datetime.now(UTC) + timedelta(hours=2)).isoformat()
            response = await client.post(
                "/api/v1/games",
                data={
                    "template_id": ctx["template_id"],
                    "title": "Thumbnail Game",
                    "scheduled_at": scheduled_at,
                },
                files={"thumbnail": ("icon.png", b"\x89PNG\r\n\x1a\n", "image/png")},
            )

        assert response.status_code == 201, (
            f"Expected 201, got {response.status_code}: {response.text}"
        )
    finally:
        await cleanup_test_session(session_token)


@pytest.mark.asyncio
async def test_create_game_invalid_thumbnail_type_returns_400(
    create_user,
    create_guild,
    create_channel,
    create_template,
    seed_redis_cache,
    api_base_url,
):
    """POST /api/v1/games with a non-image thumbnail returns 400 (lines 75-80)."""
    ctx = await _setup_game_context(
        create_user, create_guild, create_channel, create_template, seed_redis_cache
    )
    session_token, _ = await create_test_session(TEST_DISCORD_TOKEN, TEST_BOT_DISCORD_ID)

    try:
        async with httpx.AsyncClient(
            base_url=api_base_url,
            timeout=10.0,
            cookies={"session_token": session_token},
        ) as client:
            scheduled_at = (datetime.now(UTC) + timedelta(hours=2)).isoformat()
            response = await client.post(
                "/api/v1/games",
                data={
                    "template_id": ctx["template_id"],
                    "title": "Bad Thumbnail Game",
                    "scheduled_at": scheduled_at,
                },
                files={"thumbnail": ("bad.txt", b"not an image", "text/plain")},
            )

        assert response.status_code == 400, (
            f"Expected 400, got {response.status_code}: {response.text}"
        )
    finally:
        await cleanup_test_session(session_token)


@pytest.mark.asyncio
async def test_create_game_nonexistent_template_returns_404(
    create_user,
    create_guild,
    create_channel,
    create_template,
    seed_redis_cache,
    api_base_url,
):
    """POST /api/v1/games with a nonexistent template_id returns 404 (lines 368-369)."""
    await _setup_game_context(
        create_user, create_guild, create_channel, create_template, seed_redis_cache
    )
    session_token, _ = await create_test_session(TEST_DISCORD_TOKEN, TEST_BOT_DISCORD_ID)

    try:
        async with httpx.AsyncClient(
            base_url=api_base_url,
            timeout=10.0,
            cookies={"session_token": session_token},
        ) as client:
            scheduled_at = (datetime.now(UTC) + timedelta(hours=2)).isoformat()
            response = await client.post(
                "/api/v1/games",
                data={
                    "template_id": str(uuid.uuid4()),
                    "title": "Bad Template Game",
                    "scheduled_at": scheduled_at,
                },
            )

        assert response.status_code == 404, (
            f"Expected 404, got {response.status_code}: {response.text}"
        )
    finally:
        await cleanup_test_session(session_token)


# ============================================================================
# list_games (lines 392-422)
# ============================================================================


@pytest.mark.asyncio
async def test_list_games_returns_authorized_games(
    create_user,
    create_guild,
    create_channel,
    create_template,
    seed_redis_cache,
    api_base_url,
):
    """GET /api/v1/games returns games the user is authorized to see (lines 392-422)."""
    ctx = await _setup_game_context(
        create_user, create_guild, create_channel, create_template, seed_redis_cache
    )
    session_token, _ = await create_test_session(TEST_DISCORD_TOKEN, TEST_BOT_DISCORD_ID)

    try:
        async with httpx.AsyncClient(
            base_url=api_base_url,
            timeout=10.0,
            cookies={"session_token": session_token},
        ) as client:
            game = await _create_game_via_api(client, ctx, title="Listed Game")
            response = await client.get(
                "/api/v1/games",
                params={"guild_id": ctx["guild_id"]},
            )

        assert response.status_code == 200, (
            f"Expected 200, got {response.status_code}: {response.text}"
        )
        data = response.json()
        assert "games" in data
        assert any(g["id"] == game["id"] for g in data["games"])
    finally:
        await cleanup_test_session(session_token)


# ============================================================================
# get_game (lines 435-462)
# ============================================================================


@pytest.mark.asyncio
async def test_get_game_success(
    create_user,
    create_guild,
    create_channel,
    create_template,
    seed_redis_cache,
    api_base_url,
):
    """GET /api/v1/games/{id} returns game details for an authorized user (lines 435-462)."""
    ctx = await _setup_game_context(
        create_user, create_guild, create_channel, create_template, seed_redis_cache
    )
    session_token, _ = await create_test_session(TEST_DISCORD_TOKEN, TEST_BOT_DISCORD_ID)

    try:
        async with httpx.AsyncClient(
            base_url=api_base_url,
            timeout=10.0,
            cookies={"session_token": session_token},
        ) as client:
            game = await _create_game_via_api(client, ctx, title="Get Game Test")
            response = await client.get(f"/api/v1/games/{game['id']}")

        assert response.status_code == 200, (
            f"Expected 200, got {response.status_code}: {response.text}"
        )
        data = response.json()
        assert data["id"] == game["id"]
    finally:
        await cleanup_test_session(session_token)


@pytest.mark.asyncio
async def test_get_game_not_found(
    create_user,
    create_guild,
    create_channel,
    create_template,
    seed_redis_cache,
    api_base_url,
):
    """GET /api/v1/games/{id} returns 404 for nonexistent game (lines 435-440)."""
    await _setup_game_context(
        create_user, create_guild, create_channel, create_template, seed_redis_cache
    )
    session_token, _ = await create_test_session(TEST_DISCORD_TOKEN, TEST_BOT_DISCORD_ID)

    try:
        async with httpx.AsyncClient(
            base_url=api_base_url,
            timeout=10.0,
            cookies={"session_token": session_token},
        ) as client:
            response = await client.get(f"/api/v1/games/{uuid.uuid4()}")

        assert response.status_code == 404, (
            f"Expected 404, got {response.status_code}: {response.text}"
        )
    finally:
        await cleanup_test_session(session_token)


# ============================================================================
# update_game (lines 153, 157, 161, 165, 169, 199-200, 552-555)
# ============================================================================


@pytest.mark.asyncio
async def test_update_game_success(
    create_user,
    create_guild,
    create_channel,
    create_template,
    seed_redis_cache,
    api_base_url,
):
    """PUT /api/v1/games/{id} updates game title and returns updated game (lines 552-555)."""
    ctx = await _setup_game_context(
        create_user, create_guild, create_channel, create_template, seed_redis_cache
    )
    session_token, _ = await create_test_session(TEST_DISCORD_TOKEN, TEST_BOT_DISCORD_ID)

    try:
        async with httpx.AsyncClient(
            base_url=api_base_url,
            timeout=10.0,
            cookies={"session_token": session_token},
        ) as client:
            game = await _create_game_via_api(client, ctx, title="Original Title")
            response = await client.put(
                f"/api/v1/games/{game['id']}",
                data={"title": "Updated Title"},
            )

        assert response.status_code == 200, (
            f"Expected 200, got {response.status_code}: {response.text}"
        )
        assert response.json()["title"] == "Updated Title"
    finally:
        await cleanup_test_session(session_token)


@pytest.mark.asyncio
async def test_update_game_with_all_optional_form_fields(
    create_user,
    create_guild,
    create_channel,
    create_template,
    seed_redis_cache,
    api_base_url,
):
    """PUT /api/v1/games/{id} with all optional parsed fields covers lines 153,157,161,165,169."""
    ctx = await _setup_game_context(
        create_user, create_guild, create_channel, create_template, seed_redis_cache
    )
    session_token, _ = await create_test_session(TEST_DISCORD_TOKEN, TEST_BOT_DISCORD_ID)

    try:
        async with httpx.AsyncClient(
            base_url=api_base_url,
            timeout=10.0,
            cookies={"session_token": session_token},
        ) as client:
            game = await _create_game_via_api(client, ctx, title="Optional Fields Game")
            scheduled_at = (datetime.now(UTC) + timedelta(hours=3)).isoformat()
            response = await client.put(
                f"/api/v1/games/{game['id']}",
                data={
                    "scheduled_at": scheduled_at,
                    "reminder_minutes": json.dumps([30, 60]),
                    "notify_role_ids": json.dumps([]),
                    "participants": json.dumps([]),
                    "removed_participant_ids": json.dumps([]),
                },
            )

        assert response.status_code == 200, (
            f"Expected 200, got {response.status_code}: {response.text}"
        )
    finally:
        await cleanup_test_session(session_token)


@pytest.mark.asyncio
async def test_update_game_persists_self_added_participant_reposition(
    create_user,
    create_guild,
    create_channel,
    create_template,
    seed_redis_cache,
    api_base_url,
    admin_db_sync,
):
    """A host-repositioned SELF_ADDED participant's new position persists (Phase 2 fix)."""
    ctx = await _setup_game_context(
        create_user, create_guild, create_channel, create_template, seed_redis_cache
    )
    participant_user = create_user()
    session_token, _ = await create_test_session(TEST_DISCORD_TOKEN, TEST_BOT_DISCORD_ID)

    try:
        async with httpx.AsyncClient(
            base_url=api_base_url,
            timeout=10.0,
            cookies={"session_token": session_token},
        ) as client:
            game = await _create_game_via_api(client, ctx, title="Self Added Reposition Game")

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
                    "game_session_id": game["id"],
                    "user_id": participant_user["id"],
                    "joined_at": datetime.now(UTC),
                    "position_type": 24000,  # SELF_ADDED
                    "position": 32767,  # UNPOSITIONED_SENTINEL
                },
            )
            admin_db_sync.commit()

            response = await client.put(
                f"/api/v1/games/{game['id']}",
                data={
                    "participants": json.dumps([{"participant_id": participant_id, "position": 1}]),
                },
            )

        assert response.status_code == 200, (
            f"Expected 200, got {response.status_code}: {response.text}"
        )

        row = admin_db_sync.execute(
            text("SELECT position_type, position FROM game_participants WHERE id = :id"),
            {"id": participant_id},
        ).fetchone()
        assert row is not None, "Participant row not found after update"
        assert row[0] == 24000, "SELF_ADDED participant must not be promoted by a reposition"
        assert row[1] == 1
    finally:
        await cleanup_test_session(session_token)


@pytest.mark.asyncio
async def test_update_game_persists_role_matched_reposition_as_self_added(
    create_user,
    create_guild,
    create_channel,
    create_template,
    seed_redis_cache,
    api_base_url,
    admin_db_sync,
):
    """A host-repositioned ROLE_MATCHED participant converts to SELF_ADDED (Phase 2 Task 2.5)."""
    ctx = await _setup_game_context(
        create_user,
        create_guild,
        create_channel,
        create_template,
        seed_redis_cache,
        allowed_signup_methods=["ROLE_BASED"],
    )
    participant_user = create_user()
    session_token, _ = await create_test_session(TEST_DISCORD_TOKEN, TEST_BOT_DISCORD_ID)

    try:
        async with httpx.AsyncClient(
            base_url=api_base_url,
            timeout=10.0,
            cookies={"session_token": session_token},
        ) as client:
            game = await _create_game_via_api(
                client, ctx, title="Role Matched Reposition Game", signup_method="ROLE_BASED"
            )

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
                    "game_session_id": game["id"],
                    "user_id": participant_user["id"],
                    "joined_at": datetime.now(UTC),
                    "position_type": 16000,  # ROLE_MATCHED
                    "position": 0,  # real priority-role index
                },
            )
            admin_db_sync.commit()

            response = await client.put(
                f"/api/v1/games/{game['id']}",
                data={
                    "participants": json.dumps([{"participant_id": participant_id, "position": 1}]),
                },
            )

        assert response.status_code == 200, (
            f"Expected 200, got {response.status_code}: {response.text}"
        )

        row = admin_db_sync.execute(
            text("SELECT position_type, position FROM game_participants WHERE id = :id"),
            {"id": participant_id},
        ).fetchone()
        assert row is not None, "Participant row not found after update"
        assert row[0] == 24000, "ROLE_MATCHED participant must convert to SELF_ADDED on reposition"
        assert row[1] == 1
    finally:
        await cleanup_test_session(session_token)


@pytest.mark.asyncio
async def test_update_game_preserves_host_added_participant_omitted_from_payload(
    create_user,
    create_guild,
    create_channel,
    create_template,
    seed_redis_cache,
    api_base_url,
    admin_db_sync,
):
    """A HOST_ADDED participant omitted from `participants` survives an update.

    Regression test for a bug report: a host manually queued a HOST_ADDED waitlist
    entry (e.g. a boundary marker like "Auto Waitlisters End") past the confirmed
    slots of a HOST_SELECTED_WITH_WAITLIST game. The edit-game frontend's
    disturbed-prefix payload never resends untouched HOST_ADDED rows sitting past the
    confirmed prefix, and the backend used to (incorrectly) delete any HOST_ADDED
    participant absent from the submitted list on every save. Omission from
    `participants` must not delete a participant -- only `removed_participant_ids` may.
    """
    ctx = await _setup_game_context(
        create_user,
        create_guild,
        create_channel,
        create_template,
        seed_redis_cache,
        allowed_signup_methods=["HOST_SELECTED_WITH_WAITLIST"],
    )
    confirmed_user = create_user()
    session_token, _ = await create_test_session(TEST_DISCORD_TOKEN, TEST_BOT_DISCORD_ID)

    try:
        async with httpx.AsyncClient(
            base_url=api_base_url,
            timeout=10.0,
            cookies={"session_token": session_token},
        ) as client:
            game = await _create_game_via_api(
                client,
                ctx,
                title="Host Added Waitlist Game",
                signup_method="HOST_SELECTED_WITH_WAITLIST",
            )

            confirmed_id = str(uuid.uuid4())
            waitlisted_marker_id = str(uuid.uuid4())
            insert_sql = text(
                "INSERT INTO game_participants "
                "(id, game_session_id, user_id, display_name, joined_at, "
                "position_type, position) "
                "VALUES (:id, :game_session_id, :user_id, :display_name, :joined_at, "
                ":position_type, :position)"
            )
            admin_db_sync.execute(
                insert_sql,
                {
                    "id": confirmed_id,
                    "game_session_id": game["id"],
                    "user_id": confirmed_user["id"],
                    "display_name": None,
                    "joined_at": datetime.now(UTC),
                    "position_type": 8000,  # HOST_ADDED
                    "position": 0,
                },
            )
            admin_db_sync.execute(
                insert_sql,
                {
                    "id": waitlisted_marker_id,
                    "game_session_id": game["id"],
                    "user_id": None,
                    "display_name": "Auto Waitlisters End",
                    "joined_at": datetime.now(UTC),
                    "position_type": 8000,  # HOST_ADDED, past the confirmed prefix
                    "position": 99,
                },
            )
            admin_db_sync.commit()

            # Mirrors the frontend's disturbed-prefix payload: only the confirmed
            # participant is resent; the waitlisted marker is omitted, not removed.
            response = await client.put(
                f"/api/v1/games/{game['id']}",
                data={
                    "signup_method": "SELF_SIGNUP",
                    "participants": json.dumps([{"participant_id": confirmed_id, "position": 0}]),
                },
            )

        assert response.status_code == 200, (
            f"Expected 200, got {response.status_code}: {response.text}"
        )

        row = admin_db_sync.execute(
            text("SELECT id FROM game_participants WHERE id = :id"),
            {"id": waitlisted_marker_id},
        ).fetchone()
        assert row is not None, "HOST_ADDED participant omitted from payload must not be deleted"
    finally:
        await cleanup_test_session(session_token)


@pytest.mark.asyncio
async def test_update_game_replaces_placeholder_via_removed_and_mention_in_same_request(
    create_user,
    create_guild,
    create_channel,
    create_template,
    seed_redis_cache,
    api_base_url,
    admin_db_sync,
):
    """A single PUT with `removed_participant_ids` + a new `participants` mention
    replaces a participant's identity at the same position.

    Regression test for a bug report: a host edited an existing placeholder's name
    in the edit-game UI, saved with no error, and the name never changed. The
    frontend has no way to update an existing participant_id's identity, so an
    in-place edit must be submitted as remove-old + add-new in one request. This
    verifies that combination actually replaces the participant rather than, e.g.,
    leaving both the old and new rows behind or losing the position.
    """
    ctx = await _setup_game_context(
        create_user, create_guild, create_channel, create_template, seed_redis_cache
    )
    session_token, _ = await create_test_session(TEST_DISCORD_TOKEN, TEST_BOT_DISCORD_ID)

    try:
        async with httpx.AsyncClient(
            base_url=api_base_url,
            timeout=10.0,
            cookies={"session_token": session_token},
        ) as client:
            game = await _create_game_via_api(client, ctx, title="Placeholder Replace Game")

            placeholder_id = str(uuid.uuid4())
            admin_db_sync.execute(
                text(
                    "INSERT INTO game_participants "
                    "(id, game_session_id, user_id, display_name, joined_at, "
                    "position_type, position) "
                    "VALUES (:id, :game_session_id, NULL, :display_name, :joined_at, "
                    ":position_type, :position)"
                ),
                {
                    "id": placeholder_id,
                    "game_session_id": game["id"],
                    "display_name": "Guest Player",
                    "joined_at": datetime.now(UTC),
                    "position_type": 8000,  # HOST_ADDED
                    "position": 1,
                },
            )
            admin_db_sync.commit()

            response = await client.put(
                f"/api/v1/games/{game['id']}",
                data={
                    "removed_participant_ids": json.dumps([placeholder_id]),
                    "participants": json.dumps([{"mention": "Real Player", "position": 1}]),
                },
            )

        assert response.status_code == 200, (
            f"Expected 200, got {response.status_code}: {response.text}"
        )

        rows = admin_db_sync.execute(
            text(
                "SELECT id, display_name, position_type, position FROM game_participants "
                "WHERE game_session_id = :game_id"
            ),
            {"game_id": game["id"]},
        ).fetchall()

        assert len(rows) == 1, f"Expected exactly 1 participant after replace, got: {rows}"
        assert rows[0][0] != placeholder_id, "Old placeholder record must be deleted, not reused"
        assert rows[0][1] == "Real Player"
        assert rows[0][2] == 8000  # HOST_ADDED
        assert rows[0][3] == 1
    finally:
        await cleanup_test_session(session_token)


ALREADY_SEATED_UID_ALPHA = "111111111111111111"
ALREADY_SEATED_UID_BETA = "222222222222222222"


async def _seed_guild_member_projection(redis_client, guild_discord_id: str) -> None:
    """Seed the username/member projection keys so '@alpha' and '@beta' resolve.

    Mirrors what the bot's member sync writes to Redis; without these keys the
    resolver cannot map user-friendly mentions to Discord users in tests.
    """
    from shared.cache.keys import CacheKeys  # noqa: PLC0415

    gen = await redis_client.get(CacheKeys.proj_gen())
    if gen is None:
        gen = "1"
        await redis_client.set(CacheKeys.proj_gen(), gen)

    for username, uid in (
        ("alpha", ALREADY_SEATED_UID_ALPHA),
        ("beta", ALREADY_SEATED_UID_BETA),
    ):
        member = {
            "roles": [],
            "nick": None,
            "global_name": None,
            "username": username,
            "avatar_url": None,
        }
        await redis_client.set_json(
            CacheKeys.proj_member(gen, guild_discord_id, uid), member, ttl=3600
        )
        raw_client = redis_client._client
        entry = f"{username}\x00{uid}"
        await raw_client.zadd(CacheKeys.proj_usernames(gen, guild_discord_id), {entry: 0})


@pytest.mark.asyncio
async def test_update_game_replaces_two_entries_in_same_request(
    create_user,
    create_guild,
    create_channel,
    create_template,
    seed_redis_cache,
    api_base_url,
    admin_db_sync,
):
    """A single PUT replacing two placeholder rows at once updates both.

    Control case for the multi-edit failure: two non-colliding in-place edits
    submitted together must both persist without error.
    """
    ctx = await _setup_game_context(
        create_user, create_guild, create_channel, create_template, seed_redis_cache
    )
    session_token, _ = await create_test_session(TEST_DISCORD_TOKEN, TEST_BOT_DISCORD_ID)

    try:
        async with httpx.AsyncClient(
            base_url=api_base_url,
            timeout=10.0,
            cookies={"session_token": session_token},
        ) as client:
            game = await _create_game_via_api(client, ctx, title="Multi Replace Game")

            placeholder_a = str(uuid.uuid4())
            placeholder_b = str(uuid.uuid4())
            for pid, name, position in (
                (placeholder_a, "Seat One", 1),
                (placeholder_b, "Seat Two", 2),
            ):
                admin_db_sync.execute(
                    text(
                        "INSERT INTO game_participants "
                        "(id, game_session_id, user_id, display_name, joined_at, "
                        "position_type, position) "
                        "VALUES (:id, :game_session_id, NULL, :display_name, :joined_at, "
                        ":position_type, :position)"
                    ),
                    {
                        "id": pid,
                        "game_session_id": game["id"],
                        "display_name": name,
                        "joined_at": datetime.now(UTC),
                        "position_type": 8000,  # HOST_ADDED
                        "position": position,
                    },
                )
            admin_db_sync.commit()

            response = await client.put(
                f"/api/v1/games/{game['id']}",
                data={
                    "removed_participant_ids": json.dumps([placeholder_a, placeholder_b]),
                    "participants": json.dumps([
                        {"mention": "New Seat One", "position": 1},
                        {"mention": "New Seat Two", "position": 2},
                    ]),
                },
            )

        assert response.status_code == 200, (
            f"Expected 200, got {response.status_code}: {response.text}"
        )

        rows = admin_db_sync.execute(
            text(
                "SELECT id, display_name, position FROM game_participants "
                "WHERE game_session_id = :game_id ORDER BY position"
            ),
            {"game_id": game["id"]},
        ).fetchall()

        assert len(rows) == 2, f"Expected exactly 2 participants after replace, got: {rows}"
        names_by_position = {row[2]: row[1] for row in rows}
        assert names_by_position == {1: "New Seat One", 2: "New Seat Two"}, rows
    finally:
        await cleanup_test_session(session_token)


@pytest.mark.asyncio
async def test_update_game_mention_of_user_already_seated_adopts_existing_seat(
    create_user,
    create_guild,
    create_channel,
    create_template,
    seed_redis_cache,
    api_base_url,
    redis_client_async,
    admin_db_sync,
):
    """Replacing another seat with the @mention of a user who already sits on the
    game adopts their existing seat instead of duplicating it or crashing.

    Regression lineage for the multi-edit failure: when an entered value resolves to
    a user whose participant row already exists on this game, two INSERTs used to be
    created that trip `unique_game_participant` at flush time; that IntegrityError is
    not one of the exception types the PUT route maps, so hosts saw a bare 500 and
    the generic 'Failed to submit' banner. Final contract: mentioning a seated user
    moves their single row -- converted to HOST_ADDED at the requested position --
    with no second row, no duplicate join notification, and no error.
    """
    ctx = await _setup_game_context(
        create_user, create_guild, create_channel, create_template, seed_redis_cache
    )
    session_token, _ = await create_test_session(TEST_DISCORD_TOKEN, TEST_BOT_DISCORD_ID)
    await _seed_guild_member_projection(redis_client_async, ctx["guild_discord_id"])

    try:
        async with httpx.AsyncClient(
            base_url=api_base_url,
            timeout=10.0,
            cookies={"session_token": session_token},
        ) as client:
            # Create the game with both seats held by real (already-seated) users,
            # mirroring the edit-game flow's remove-old + add-new submission shape.
            scheduled_at = (datetime.now(UTC) + timedelta(hours=2)).isoformat()
            create_response = await client.post(
                "/api/v1/games",
                data={
                    "template_id": ctx["template_id"],
                    "title": "Duplicate Seat Game",
                    "scheduled_at": scheduled_at,
                    "initial_participants": json.dumps(["@alpha", "@beta"]),
                },
            )
            assert create_response.status_code == 201, (
                f"Game creation failed: {create_response.text}"
            )
            game = create_response.json()
            participants = {p["discord_id"]: p for p in game["participants"]}
            assert set(participants) == {
                ALREADY_SEATED_UID_ALPHA,
                ALREADY_SEATED_UID_BETA,
            }, game["participants"]

            # Edit alpha's seat to point at beta, who still holds their own seat:
            # exactly what a host typing '@beta' into another entry submits.
            response = await client.put(
                f"/api/v1/games/{game['id']}",
                data={
                    "removed_participant_ids": json.dumps([
                        participants[ALREADY_SEATED_UID_ALPHA]["id"]
                    ]),
                    "participants": json.dumps([{"mention": "@beta", "position": 1}]),
                },
            )

        # Adoption succeeds end-to-end instead of crashing or rejecting the submit.
        assert response.status_code == 200, (
            f"Expected adoption success (200), got {response.status_code}: {response.text}"
        )

        # Exactly one participant row remains: beta's own, converted to HOST_ADDED
        # at position 1. No second row exists for them and alpha's is gone.
        rows = admin_db_sync.execute(
            text(
                "SELECT u.discord_id, gp.position_type, gp.position "
                "FROM game_participants gp JOIN users u ON u.id = gp.user_id "
                "WHERE gp.game_session_id = :game_id"
            ),
            {"game_id": game["id"]},
        ).fetchall()
        assert len(rows) == 1, f"Adoption must leave a single seat, not two: {rows}"
        discord_id, position_type, position = rows[0]
        assert discord_id == ALREADY_SEATED_UID_BETA, rows
        assert position_type == 8000, f"HOST_ADDED expected: {rows}"  # 8000 == HOST_ADDED
        assert position == 1, rows
    finally:
        await cleanup_test_session(session_token)


@pytest.mark.asyncio
async def test_update_game_replace_placeholder_with_seated_user_moves_existing_seat(
    create_user,
    create_guild,
    create_channel,
    create_template,
    seed_redis_cache,
    api_base_url,
    redis_client_async,
    admin_db_sync,
):
    """A host replacing a placeholder with the mention of a user who already sits on
    the game moves that user's existing seat.

    Mirrors the reported scenario as-is: a placeholder holds one entry while the
    player holds a self-added seat further down the list. When the host types '@bret'
    into the placeholder's field, their single participant record is converted from
    SELF_ADDED to HOST_ADDED at the new position -- no rejection, no duplicate row.
    """
    ctx = await _setup_game_context(
        create_user, create_guild, create_channel, create_template, seed_redis_cache
    )
    session_token, _ = await create_test_session(TEST_DISCORD_TOKEN, TEST_BOT_DISCORD_ID)
    await _seed_guild_member_projection(redis_client_async, ctx["guild_discord_id"])

    try:
        async with httpx.AsyncClient(
            base_url=api_base_url,
            timeout=10.0,
            cookies={"session_token": session_token},
        ) as client:
            scheduled_at = (datetime.now(UTC) + timedelta(hours=2)).isoformat()
            create_response = await client.post(
                "/api/v1/games",
                data={
                    "template_id": ctx["template_id"],
                    "title": "Placeholder Replace Game",
                    "scheduled_at": scheduled_at,
                    "initial_participants": json.dumps(["@beta", "Placeholder Two"]),
                },
            )
            assert create_response.status_code == 201, (
                f"Game creation failed: {create_response.text}"
            )
            game = create_response.json()
            all_participants = game["participants"]
            beta_entry = next(
                p for p in all_participants if p.get("discord_id") == ALREADY_SEATED_UID_BETA
            )
            placeholder_entry = next(p for p in all_participants if not p.get("discord_id"))

            # Simulate the player having signed up on their own: convert their seat
            # to SELF_ADDED and move it down the list away from position one.
            admin_db_sync.execute(
                text(
                    "UPDATE game_participants SET position_type = :self_added, position = 10 "
                    "WHERE id = :pid"
                ),
                {"self_added": 24000, "pid": beta_entry["id"]},  # 24000 == SELF_ADDED
            )
            admin_db_sync.commit()

            # The host replaces the placeholder's field with '@beta'.
            response = await client.put(
                f"/api/v1/games/{game['id']}",
                data={
                    "removed_participant_ids": json.dumps([placeholder_entry["id"]]),
                    "participants": json.dumps([{"mention": "@beta", "position": 1}]),
                },
            )

        assert response.status_code == 200, (
            f"Expected adoption success (200), got {response.status_code}: {response.text}"
        )

        # Their single seat moved from SELF_ADDED@10 to HOST_ADDED@1.
        rows = admin_db_sync.execute(
            text(
                "SELECT u.discord_id, gp.position_type, gp.position "
                "FROM game_participants gp JOIN users u ON u.id = gp.user_id "
                "WHERE gp.game_session_id = :game_id"
            ),
            {"game_id": game["id"]},
        ).fetchall()
        assert len(rows) == 1, f"Adoption must leave a single seat, not two: {rows}"
        discord_id, position_type, position = rows[0]
        assert discord_id == ALREADY_SEATED_UID_BETA, rows
        assert position_type == 8000, f"HOST_ADDED expected after host mention: {rows}"
        assert position == 1, rows
    finally:
        await cleanup_test_session(session_token)


@pytest.mark.asyncio
async def test_create_game_with_same_user_mentioned_twice_returns_invalid_mentions(
    create_user,
    create_guild,
    create_channel,
    create_template,
    seed_redis_cache,
    api_base_url,
    redis_client_async,
    admin_db_sync,
):
    """Creating a game whose pre-filled participants list mentions one user twice
    fails cleanly (422 invalid_mentions), not with an unhandled duplicate-key crash.

    Same root cause as the multi-edit failure, reached through POST /games instead of
    PUT: two pre-filled entries resolving to the same user produce two INSERTs that
    collide on `unique_game_participant` at flush time, which the create route does
    not map -- hosts would see a bare 500 and lose the whole form submission.
    """
    ctx = await _setup_game_context(
        create_user, create_guild, create_channel, create_template, seed_redis_cache
    )
    session_token, _ = await create_test_session(TEST_DISCORD_TOKEN, TEST_BOT_DISCORD_ID)
    await _seed_guild_member_projection(redis_client_async, ctx["guild_discord_id"])

    try:
        async with httpx.AsyncClient(
            base_url=api_base_url,
            timeout=10.0,
            cookies={"session_token": session_token},
        ) as client:
            scheduled_at = (datetime.now(UTC) + timedelta(hours=2)).isoformat()
            response = await client.post(
                "/api/v1/games",
                data={
                    "template_id": ctx["template_id"],
                    "title": "Double Mention Create Game",
                    "scheduled_at": scheduled_at,
                    "initial_participants": json.dumps(["@beta", "@beta"]),
                },
            )

        assert response.status_code == 422, (
            f"Expected 422 invalid_mentions, got {response.status_code}: {response.text}"
        )
        detail = response.json()["detail"]
        assert detail["error"] == "invalid_mentions", detail
        reasons = {(e.get("input"), e.get("reason")) for e in detail["invalid_mentions"]}
        assert any(
            input_ == "@beta" and "more than once" in reason.lower() for input_, reason in reasons
        ), reasons

        # The rejected submit must not leave a half-created game behind.
        count = admin_db_sync.execute(text("SELECT COUNT(*) FROM game_sessions")).scalar_one()
        assert count == 0, f"No game_sessions row should survive a rejected create: {count}"
    finally:
        await cleanup_test_session(session_token)


@pytest.mark.asyncio
async def test_update_game_remove_thumbnail(
    create_user,
    create_guild,
    create_channel,
    create_template,
    seed_redis_cache,
    api_base_url,
):
    """PUT /api/v1/games/{id} with remove_thumbnail=true covers lines 199-200."""
    ctx = await _setup_game_context(
        create_user, create_guild, create_channel, create_template, seed_redis_cache
    )
    session_token, _ = await create_test_session(TEST_DISCORD_TOKEN, TEST_BOT_DISCORD_ID)

    try:
        async with httpx.AsyncClient(
            base_url=api_base_url,
            timeout=10.0,
            cookies={"session_token": session_token},
        ) as client:
            game = await _create_game_via_api(client, ctx, title="Remove Thumbnail Game")
            response = await client.put(
                f"/api/v1/games/{game['id']}",
                data={"remove_thumbnail": "true"},
            )

        assert response.status_code == 200, (
            f"Expected 200, got {response.status_code}: {response.text}"
        )
    finally:
        await cleanup_test_session(session_token)


@pytest.mark.asyncio
async def test_update_game_nonexistent_returns_404(
    create_user,
    create_guild,
    create_channel,
    create_template,
    seed_redis_cache,
    api_base_url,
):
    """PUT /api/v1/games/{id} with nonexistent game returns 404 (lines 554-555, 247-249)."""
    await _setup_game_context(
        create_user, create_guild, create_channel, create_template, seed_redis_cache
    )
    session_token, _ = await create_test_session(TEST_DISCORD_TOKEN, TEST_BOT_DISCORD_ID)

    try:
        async with httpx.AsyncClient(
            base_url=api_base_url,
            timeout=10.0,
            cookies={"session_token": session_token},
        ) as client:
            response = await client.put(
                f"/api/v1/games/{uuid.uuid4()}",
                data={"title": "Should Not Matter"},
            )

        assert response.status_code == 404, (
            f"Expected 404, got {response.status_code}: {response.text}"
        )
    finally:
        await cleanup_test_session(session_token)


@pytest.mark.asyncio
async def test_update_game_with_image_file(
    create_user,
    create_guild,
    create_channel,
    create_template,
    seed_redis_cache,
    api_base_url,
):
    """PUT /api/v1/games/{id} with a banner image processes the upload (lines 203-214)."""
    ctx = await _setup_game_context(
        create_user, create_guild, create_channel, create_template, seed_redis_cache
    )
    session_token, _ = await create_test_session(TEST_DISCORD_TOKEN, TEST_BOT_DISCORD_ID)

    try:
        async with httpx.AsyncClient(
            base_url=api_base_url,
            timeout=10.0,
            cookies={"session_token": session_token},
        ) as client:
            game = await _create_game_via_api(client, ctx, title="Image Update Game")
            response = await client.put(
                f"/api/v1/games/{game['id']}",
                files={"image": ("banner.png", b"\x89PNG\r\n\x1a\n", "image/png")},
            )

        assert response.status_code == 200, (
            f"Expected 200, got {response.status_code}: {response.text}"
        )
    finally:
        await cleanup_test_session(session_token)


# ============================================================================
# delete_game (lines 577-586)
# ============================================================================


@pytest.mark.asyncio
async def test_delete_game_not_found(
    create_user,
    create_guild,
    create_channel,
    create_template,
    seed_redis_cache,
    api_base_url,
):
    """DELETE /api/v1/games/{id} returns 404 for a nonexistent game (lines 577-585)."""
    await _setup_game_context(
        create_user, create_guild, create_channel, create_template, seed_redis_cache
    )
    session_token, _ = await create_test_session(TEST_DISCORD_TOKEN, TEST_BOT_DISCORD_ID)

    try:
        async with httpx.AsyncClient(
            base_url=api_base_url,
            timeout=10.0,
            cookies={"session_token": session_token},
        ) as client:
            response = await client.delete(f"/api/v1/games/{uuid.uuid4()}")

        assert response.status_code == 404, (
            f"Expected 404, got {response.status_code}: {response.text}"
        )
    finally:
        await cleanup_test_session(session_token)


# ============================================================================
# clone_game (lines 612-616)
# ============================================================================


@pytest.mark.asyncio
async def test_clone_game_not_found(
    create_user,
    create_guild,
    create_channel,
    create_template,
    seed_redis_cache,
    api_base_url,
):
    """POST /api/v1/games/{id}/clone with nonexistent game returns 404 (lines 612-614)."""
    await _setup_game_context(
        create_user, create_guild, create_channel, create_template, seed_redis_cache
    )
    session_token, _ = await create_test_session(TEST_DISCORD_TOKEN, TEST_BOT_DISCORD_ID)

    try:
        async with httpx.AsyncClient(
            base_url=api_base_url,
            timeout=10.0,
            cookies={"session_token": session_token},
        ) as client:
            scheduled_at = (datetime.now(UTC) + timedelta(hours=2)).isoformat()
            response = await client.post(
                f"/api/v1/games/{uuid.uuid4()}/clone",
                json={"title": "Cloned Game", "scheduled_at": scheduled_at},
            )

        assert response.status_code == 404, (
            f"Expected 404, got {response.status_code}: {response.text}"
        )
    finally:
        await cleanup_test_session(session_token)


# ============================================================================
# join_game (lines 635-684)
# ============================================================================


@pytest.mark.asyncio
async def test_join_game_not_found(
    create_user,
    create_guild,
    create_channel,
    create_template,
    seed_redis_cache,
    api_base_url,
):
    """POST /api/v1/games/{id}/join with nonexistent game returns 404 (lines 635-637)."""
    await _setup_game_context(
        create_user, create_guild, create_channel, create_template, seed_redis_cache
    )
    session_token, _ = await create_test_session(TEST_DISCORD_TOKEN, TEST_BOT_DISCORD_ID)

    try:
        async with httpx.AsyncClient(
            base_url=api_base_url,
            timeout=10.0,
            cookies={"session_token": session_token},
        ) as client:
            response = await client.post(f"/api/v1/games/{uuid.uuid4()}/join")

        assert response.status_code == 404, (
            f"Expected 404, got {response.status_code}: {response.text}"
        )
    finally:
        await cleanup_test_session(session_token)


@pytest.mark.asyncio
async def test_join_game_success(
    create_user,
    create_guild,
    create_channel,
    create_template,
    create_game,
    seed_redis_cache,
    api_base_url,
):
    """POST /api/v1/games/{id}/join adds user as participant (lines 638-684)."""
    guild = create_guild(bot_manager_roles=[BOT_MANAGER_ROLE_ID])
    channel = create_channel(guild_id=guild["id"])
    host_user = create_user()
    create_user(discord_user_id=TEST_BOT_DISCORD_ID)
    template = create_template(guild_id=guild["id"], channel_id=channel["id"])
    game = create_game(
        guild_id=guild["id"],
        channel_id=channel["id"],
        host_id=host_user["id"],
        template_id=template["id"],
        status="SCHEDULED",
    )

    await seed_redis_cache(
        user_discord_id=TEST_BOT_DISCORD_ID,
        guild_discord_id=guild["guild_id"],
        channel_discord_id=channel["channel_id"],
        user_roles=[BOT_MANAGER_ROLE_ID],
    )
    session_token, _ = await create_test_session(TEST_DISCORD_TOKEN, TEST_BOT_DISCORD_ID)

    try:
        async with httpx.AsyncClient(
            base_url=api_base_url,
            timeout=10.0,
            cookies={"session_token": session_token},
        ) as client:
            response = await client.post(f"/api/v1/games/{game['id']}/join")

        assert response.status_code == 200, (
            f"Expected 200, got {response.status_code}: {response.text}"
        )
        data = response.json()
        assert data["discord_id"] == TEST_BOT_DISCORD_ID
    finally:
        await cleanup_test_session(session_token)


# ============================================================================
# leave_game (lines 698-713)
# ============================================================================


@pytest.mark.asyncio
async def test_leave_game_not_found(
    create_user,
    create_guild,
    create_channel,
    create_template,
    seed_redis_cache,
    api_base_url,
):
    """POST /api/v1/games/{id}/leave with nonexistent game returns 404 (lines 698-712)."""
    await _setup_game_context(
        create_user, create_guild, create_channel, create_template, seed_redis_cache
    )
    session_token, _ = await create_test_session(TEST_DISCORD_TOKEN, TEST_BOT_DISCORD_ID)

    try:
        async with httpx.AsyncClient(
            base_url=api_base_url,
            timeout=10.0,
            cookies={"session_token": session_token},
        ) as client:
            response = await client.post(f"/api/v1/games/{uuid.uuid4()}/leave")

        assert response.status_code == 404, (
            f"Expected 404, got {response.status_code}: {response.text}"
        )
    finally:
        await cleanup_test_session(session_token)
