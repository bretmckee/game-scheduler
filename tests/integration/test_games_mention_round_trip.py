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


"""Integration tests for the lossless @mention / #channel round trip.

Each case goes through the real API, database and Redis member projection:
create a game, GET it, then PUT the returned text back unedited, both collapsed
the way the web client does and as the raw labeled tokens the API returned.
Stored text must stay byte-identical across every save.
"""

import re
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import httpx
import pytest
from sqlalchemy import text

from shared.cache.client import RedisClient
from shared.cache.keys import CacheKeys
from shared.utils.discord_tokens import extract_bot_discord_id
from tests.shared.auth_helpers import cleanup_test_session, create_test_session

pytestmark = pytest.mark.integration

TEST_DISCORD_TOKEN = "MTQ0NDA3ODM4NjM4MDAxMzY0OA.GvmbbW.fake_token_for_integration_tests"
TEST_BOT_DISCORD_ID = extract_bot_discord_id(TEST_DISCORD_TOKEN)
BOT_MANAGER_ROLE_ID = "123456789012345678"
PROJECTION_GEN = "1"

ALICE_ID = "300000000000000001"
KALLISTI_ROSE_ID = "300000000000000002"
XANTHIAS_ID = "300000000000000003"
ANGLE_ID = "300000000000000004"
KAL_ID = "300000000000000005"
KALLISTI_ID = "300000000000000006"
KALLISTI_ONE_ID = "300000000000000007"
KALLISTI_TWO_ID = "300000000000000008"
DEPARTED_ID = "300000000000000009"

HYPHEN_CHANNEL_ID = "400000000000000001"
LFG_ONE_ID = "400000000000000002"
LFG_TWO_ID = "400000000000000003"
EMOJI_ID = "500000000000000001"

# Mirrors the client's collapse of an unedited field: frontend mentionTokens
# returns the original text with every labeled token reduced to its bare form.
_LABELED_TOKEN = re.compile(r"<([@#])(\d+)\|[^>]*>")


@dataclass(frozen=True)
class Member:
    """A guild member as the bot's member sync writes it to the projection."""

    uid: str
    username: str
    global_name: str | None = None
    nick: str | None = None


@dataclass(frozen=True)
class RoundTripCase:
    """One mention round-trip scenario applied to description and signup_instructions."""

    submitted: str
    stored: str
    returned: str
    members: tuple[Member, ...] = ()
    channels: tuple[tuple[str, str], ...] = ()
    emojis: tuple[tuple[str, str], ...] = ()


ALICE = Member(ALICE_ID, "roundtrip_alice", global_name="Alice Liddell")
KALLISTI_ROSE = Member(KALLISTI_ROSE_ID, "kallisti_rose", nick="Kallisti of the Ruby Rose")

ROUND_TRIP_CASES = {
    "bare_token": RoundTripCase(
        submitted=f"Ask <@{ALICE_ID}> first",
        stored=f"Ask <@{ALICE_ID}> first",
        returned=f"Ask <@{ALICE_ID}|Alice Liddell> first",
        members=(ALICE,),
    ),
    "at_username": RoundTripCase(
        submitted="Ask @roundtrip_alice first",
        stored=f"Ask <@{ALICE_ID}> first",
        returned=f"Ask <@{ALICE_ID}|Alice Liddell> first",
        members=(ALICE,),
    ),
    "nick_with_spaces": RoundTripCase(
        submitted="Ask @Kallisti first",
        stored=f"Ask <@{KALLISTI_ROSE_ID}> first",
        returned=f"Ask <@{KALLISTI_ROSE_ID}|Kallisti of the Ruby Rose> first",
        members=(KALLISTI_ROSE,),
    ),
    "special_char_username": RoundTripCase(
        submitted="Ask @_xanthias_tag first",
        stored=f"Ask <@{XANTHIAS_ID}> first",
        returned=f"Ask <@{XANTHIAS_ID}|Xanthias (he/him) | @GM> first",
        members=(Member(XANTHIAS_ID, "_xanthias_tag", global_name="Xanthias (he/him) | @GM"),),
    ),
    "label_with_closing_angle": RoundTripCase(
        submitted=f"Ask <@{ANGLE_ID}> first",
        stored=f"Ask <@{ANGLE_ID}> first",
        returned=f"Ask <@{ANGLE_ID}|Xan _<> first",
        members=(Member(ANGLE_ID, "angle_user", global_name="Xan >_<"),),
    ),
    "prefix_of_another_name": RoundTripCase(
        submitted="Ask @kal first",
        stored=f"Ask <@{KAL_ID}> first",
        returned=f"Ask <@{KAL_ID}|kal> first",
        members=(Member(KAL_ID, "kal"), Member(KALLISTI_ID, "kallisti")),
    ),
    "same_display_name": RoundTripCase(
        submitted=f"Ask <@{KALLISTI_TWO_ID}> first",
        stored=f"Ask <@{KALLISTI_TWO_ID}> first",
        returned=f"Ask <@{KALLISTI_TWO_ID}|Kallisti> first",
        members=(
            Member(KALLISTI_ONE_ID, "kallisti_one", global_name="Kallisti"),
            Member(KALLISTI_TWO_ID, "kallisti_two", global_name="Kallisti"),
        ),
    ),
    "departed_member": RoundTripCase(
        submitted=f"Ask <@{DEPARTED_ID}> first",
        stored=f"Ask <@{DEPARTED_ID}> first",
        returned=f"Ask <@{DEPARTED_ID}|> first",
    ),
    "hyphenated_channel": RoundTripCase(
        submitted="Meet in #test-general first",
        stored=f"Meet in <#{HYPHEN_CHANNEL_ID}> first",
        returned=f"Meet in <#{HYPHEN_CHANNEL_ID}|test-general> first",
        channels=((HYPHEN_CHANNEL_ID, "test-general"),),
    ),
    "duplicate_channel_names": RoundTripCase(
        submitted=f"Meet in <#{LFG_TWO_ID}> first",
        stored=f"Meet in <#{LFG_TWO_ID}> first",
        returned=f"Meet in <#{LFG_TWO_ID}|lfg> first",
        channels=((LFG_ONE_ID, "lfg"), (LFG_TWO_ID, "lfg")),
    ),
    "custom_emoji": RoundTripCase(
        submitted="Wave :rtwave: first",
        stored=f"Wave <:rtwave:{EMOJI_ID}> first",
        returned="Wave :rtwave: first",
        emojis=((EMOJI_ID, "rtwave"),),
    ),
    "mixed": RoundTripCase(
        submitted="@roundtrip_alice and @Kallisti in #test-general :rtwave:",
        stored=(
            f"<@{ALICE_ID}> and <@{KALLISTI_ROSE_ID}> in <#{HYPHEN_CHANNEL_ID}> "
            f"<:rtwave:{EMOJI_ID}>"
        ),
        returned=(
            f"<@{ALICE_ID}|Alice Liddell> and <@{KALLISTI_ROSE_ID}|Kallisti of the Ruby Rose> "
            f"in <#{HYPHEN_CHANNEL_ID}|test-general> :rtwave:"
        ),
        members=(ALICE, KALLISTI_ROSE),
        channels=((HYPHEN_CHANNEL_ID, "test-general"),),
        emojis=((EMOJI_ID, "rtwave"),),
    ),
}


def _client_collapse(value: str) -> str:
    return _LABELED_TOKEN.sub(r"<\1\2>", value)


async def _seed_discord_data(
    guild_discord_id: str,
    posting_channel_discord_id: str,
    members: tuple[Member, ...] = (),
    channels: tuple[tuple[str, str], ...] = (),
    emojis: tuple[tuple[str, str], ...] = (),
) -> None:
    """Seed members, guild channels and emojis the way the bot and API caches hold them."""
    redis = RedisClient()
    await redis.connect()
    try:
        for member in members:
            await redis.set_json(
                CacheKeys.proj_member(PROJECTION_GEN, guild_discord_id, member.uid),
                {
                    "roles": [],
                    "nick": member.nick,
                    "global_name": member.global_name,
                    "username": member.username,
                    "avatar_url": None,
                },
                ttl=300,
            )
            names = {n.lower() for n in (member.username, member.global_name, member.nick) if n}
            await redis._client.zadd(
                CacheKeys.proj_usernames(PROJECTION_GEN, guild_discord_id),
                {f"{name}\x00{member.uid}": 0 for name in names},
            )
        channel_list = [{"id": posting_channel_discord_id, "name": "posting", "type": 0}]
        channel_list += [{"id": cid, "name": name, "type": 0} for cid, name in channels]
        await redis.set_json(
            CacheKeys.discord_guild_channels(guild_discord_id), channel_list, ttl=300
        )
        await redis.set_json(
            CacheKeys.discord_guild_emojis(guild_discord_id),
            [{"id": eid, "name": name, "animated": False} for eid, name in emojis],
            ttl=300,
        )
    finally:
        await redis.disconnect()


async def _setup_context(
    create_user, create_guild, create_channel, create_template, seed_redis_cache
) -> dict:
    guild = create_guild(bot_manager_roles=[BOT_MANAGER_ROLE_ID])
    channel = create_channel(guild_id=guild["id"])
    create_user(discord_user_id=TEST_BOT_DISCORD_ID)
    template = create_template(guild_id=guild["id"], channel_id=channel["id"])
    await seed_redis_cache(
        user_discord_id=TEST_BOT_DISCORD_ID,
        guild_discord_id=guild["guild_id"],
        channel_discord_id=channel["channel_id"],
        user_roles=[BOT_MANAGER_ROLE_ID],
    )
    return {
        "guild_db_id": guild["id"],
        "guild_discord_id": guild["guild_id"],
        "channel_discord_id": channel["channel_id"],
        "template_id": template["id"],
    }


def _authed_client(api_base_url: str, session_token: str) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        base_url=api_base_url, timeout=10.0, cookies={"session_token": session_token}
    )


def _game_form(template_id: str, value: str) -> dict:
    return {
        "template_id": template_id,
        "title": "Round Trip Night",
        "scheduled_at": (datetime.now(UTC) + timedelta(hours=2)).isoformat(),
        "description": value,
        "signup_instructions": value,
    }


def _stored_text(admin_db_sync, game_id: str) -> tuple[str | None, str | None]:
    admin_db_sync.expire_all()
    row = admin_db_sync.execute(
        text("SELECT description, signup_instructions FROM game_sessions WHERE id = :id"),
        {"id": game_id},
    ).one()
    return row[0], row[1]


@pytest.mark.asyncio
@pytest.mark.parametrize("case", ROUND_TRIP_CASES.values(), ids=ROUND_TRIP_CASES.keys())
async def test_unedited_resave_keeps_stored_text_byte_identical(
    case: RoundTripCase,
    create_user,
    create_guild,
    create_channel,
    create_template,
    seed_redis_cache,
    admin_db_sync,
    api_base_url,
):
    """Create → GET → PUT unedited (client-collapsed, then raw labeled) never changes storage."""
    ctx = await _setup_context(
        create_user, create_guild, create_channel, create_template, seed_redis_cache
    )
    await _seed_discord_data(
        ctx["guild_discord_id"],
        ctx["channel_discord_id"],
        members=case.members,
        channels=case.channels,
        emojis=case.emojis,
    )
    session_token, _ = await create_test_session(TEST_DISCORD_TOKEN, TEST_BOT_DISCORD_ID)

    try:
        async with _authed_client(api_base_url, session_token) as client:
            created = await client.post(
                "/api/v1/games", data=_game_form(ctx["template_id"], case.submitted)
            )
            assert created.status_code == 201, f"Create failed: {created.text}"
            game_id = created.json()["id"]
            assert _stored_text(admin_db_sync, game_id) == (case.stored, case.stored)

            fetched = (await client.get(f"/api/v1/games/{game_id}")).json()
            assert fetched["description"] == case.returned
            assert fetched["signup_instructions"] == case.returned

            for resubmitted in (_client_collapse(case.returned), case.returned):
                updated = await client.put(
                    f"/api/v1/games/{game_id}",
                    data={"description": resubmitted, "signup_instructions": resubmitted},
                )
                assert updated.status_code == 200, (
                    f"PUT of {resubmitted!r} failed: {updated.status_code} {updated.text}"
                )
                assert _stored_text(admin_db_sync, game_id) == (case.stored, case.stored)
                assert updated.json()["description"] == case.returned

            refetched = (await client.get(f"/api/v1/games/{game_id}")).json()
            assert refetched["description"] == case.returned
    finally:
        await cleanup_test_session(session_token)


@pytest.mark.asyncio
async def test_same_display_name_saves_after_one_disambiguation(
    create_user,
    create_guild,
    create_channel,
    create_template,
    seed_redis_cache,
    admin_db_sync,
    api_base_url,
):
    """Kallisti: two exact '@Kallisti' hits prompt once; resubmitting the picked ID saves."""
    ctx = await _setup_context(
        create_user, create_guild, create_channel, create_template, seed_redis_cache
    )
    await _seed_discord_data(
        ctx["guild_discord_id"],
        ctx["channel_discord_id"],
        members=ROUND_TRIP_CASES["same_display_name"].members,
    )
    session_token, _ = await create_test_session(TEST_DISCORD_TOKEN, TEST_BOT_DISCORD_ID)

    try:
        async with _authed_client(api_base_url, session_token) as client:
            ambiguous = await client.post(
                "/api/v1/games", data=_game_form(ctx["template_id"], "Ask @Kallisti first")
            )
            assert ambiguous.status_code == 422, ambiguous.text
            errors = ambiguous.json()["detail"]["invalid_mentions"]
            assert {e["reason"] for e in errors} == {"Multiple matches found"}
            assert {s["discordId"] for s in errors[0]["suggestions"]} == {
                KALLISTI_ONE_ID,
                KALLISTI_TWO_ID,
            }

            picked = await client.post(
                "/api/v1/games",
                data=_game_form(ctx["template_id"], f"Ask <@{KALLISTI_TWO_ID}> first"),
            )

        assert picked.status_code == 201, picked.text
        stored = f"Ask <@{KALLISTI_TWO_ID}> first"
        assert _stored_text(admin_db_sync, picked.json()["id"]) == (stored, stored)
    finally:
        await cleanup_test_session(session_token)


@pytest.mark.asyncio
async def test_exact_username_beats_longer_prefix_matches_on_real_projection(
    create_user,
    create_guild,
    create_channel,
    create_template,
    seed_redis_cache,
    admin_db_sync,
    api_base_url,
):
    """'@kallisti' resolves to the member named exactly that despite other prefix hits."""
    ctx = await _setup_context(
        create_user, create_guild, create_channel, create_template, seed_redis_cache
    )
    await _seed_discord_data(
        ctx["guild_discord_id"],
        ctx["channel_discord_id"],
        members=(
            Member(KALLISTI_ID, "kallisti"),
            KALLISTI_ROSE,
            Member(KAL_ID, "kallisti_fan", global_name="Kallisti's Biggest Fan"),
        ),
    )
    session_token, _ = await create_test_session(TEST_DISCORD_TOKEN, TEST_BOT_DISCORD_ID)

    try:
        async with _authed_client(api_base_url, session_token) as client:
            created = await client.post(
                "/api/v1/games", data=_game_form(ctx["template_id"], "Ask @kallisti first")
            )

        assert created.status_code == 201, created.text
        stored = f"Ask <@{KALLISTI_ID}> first"
        assert _stored_text(admin_db_sync, created.json()["id"]) == (stored, stored)
    finally:
        await cleanup_test_session(session_token)


@pytest.mark.asyncio
async def test_departed_participant_returns_null_name_and_keeps_seat_on_resave(
    create_user,
    create_guild,
    create_channel,
    create_template,
    seed_redis_cache,
    admin_db_sync,
    api_base_url,
):
    """A participant missing from the projection is null-named on GET and survives a resave."""
    ctx = await _setup_context(
        create_user, create_guild, create_channel, create_template, seed_redis_cache
    )
    await _seed_discord_data(ctx["guild_discord_id"], ctx["channel_discord_id"])
    departed_user = create_user(discord_user_id=DEPARTED_ID)
    session_token, _ = await create_test_session(TEST_DISCORD_TOKEN, TEST_BOT_DISCORD_ID)
    participant_id = str(uuid.uuid4())

    try:
        async with _authed_client(api_base_url, session_token) as client:
            created = await client.post(
                "/api/v1/games", data=_game_form(ctx["template_id"], "Plain text")
            )
            assert created.status_code == 201, created.text
            game_id = created.json()["id"]

            admin_db_sync.execute(
                text(
                    "INSERT INTO game_participants "
                    "(id, game_session_id, user_id, display_name, joined_at, "
                    "position_type, position) "
                    "VALUES (:id, :game_id, :user_id, NULL, :joined_at, 8000, 1)"
                ),
                {
                    "id": participant_id,
                    "game_id": game_id,
                    "user_id": departed_user["id"],
                    "joined_at": datetime.now(UTC),
                },
            )
            admin_db_sync.commit()

            fetched = (await client.get(f"/api/v1/games/{game_id}")).json()
            departed = [p for p in fetched["participants"] if p["id"] == participant_id]
            assert len(departed) == 1, fetched["participants"]
            assert departed[0]["discord_id"] == DEPARTED_ID
            assert departed[0]["display_name"] is None
            assert departed[0]["avatar_url"] is None

            # An unedited client save sends the free-text fields but no participants.
            updated = await client.put(
                f"/api/v1/games/{game_id}",
                data={
                    "description": fetched["description"],
                    "signup_instructions": fetched["signup_instructions"],
                },
            )
            assert updated.status_code == 200, updated.text

        rows = admin_db_sync.execute(
            text(
                "SELECT id, user_id, position_type, position FROM game_participants "
                "WHERE game_session_id = :game_id"
            ),
            {"game_id": game_id},
        ).fetchall()
        assert [(str(r[0]), str(r[1]), r[2], r[3]) for r in rows] == [
            (participant_id, departed_user["id"], 8000, 1)
        ]
    finally:
        await cleanup_test_session(session_token)
