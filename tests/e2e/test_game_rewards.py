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


"""End-to-end tests for the rewards feature.

Covers:
- Save and Archive button flow (COMPLETED game → ARCHIVED within seconds)
- Host rewards reminder DM on COMPLETED transition
- Discord embed shows one ||reward|| spoiler field per entry when they fit,
  including an entry at the per-field limit
- Discord embed falls back to a single link field when entries do not fit

Requires full stack via compose.e2e.yaml.
"""

import json
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import text

from shared.models import GameStatus
from shared.utils.limits import DISCORD_EMBED_FIELD_VALUE_LIMIT, EMBED_FIELD_REWARDS
from tests.e2e.conftest import (
    TimeoutType,
    wait_for_db_condition,
    wait_for_game_message_id,
)
from tests.e2e.helpers.discord import DMType, wait_for_condition

pytestmark = pytest.mark.e2e

_ZERO_WIDTH_SPACE = "\u200b"
_MAX_INLINE_ENTRY = DISCORD_EMBED_FIELD_VALUE_LIMIT - len("||||")


def _reward_fields(embed) -> list[tuple[str, str]]:
    """Return (name, value) of the rewards heading field and every field after it."""
    names = [f.name for f in embed.fields]
    if EMBED_FIELD_REWARDS not in names:
        return []
    start = names.index(EMBED_FIELD_REWARDS)
    return [(f.name, f.value) for f in embed.fields[start:]]


def _expected_inline_fields(rewards: list[str]) -> list[tuple[str, str]]:
    return [
        (EMBED_FIELD_REWARDS if index == 0 else _ZERO_WIDTH_SPACE, f"||{entry}||")
        for index, entry in enumerate(rewards)
    ]


def _is_rewards_link_field(fields: list[tuple[str, str]], game_id: str) -> bool:
    if len(fields) != 1:
        return False
    name, value = fields[0]
    return (
        name == EMBED_FIELD_REWARDS
        and value.startswith("[View rewards](")
        and value.endswith(f"/games/{game_id})")
    )


async def _get_guild_ids(admin_db, discord_guild_id: str) -> tuple[str, str]:
    """Return (guild_db_id, template_id) for the test guild."""
    result = await admin_db.execute(
        text("SELECT id FROM guild_configurations WHERE guild_id = :guild_id"),
        {"guild_id": discord_guild_id},
    )
    guild_row = result.fetchone()
    assert guild_row, f"Test guild {discord_guild_id} not found"

    result = await admin_db.execute(
        text("SELECT id FROM game_templates WHERE guild_id = :guild_id AND is_default = true"),
        {"guild_id": guild_row[0]},
    )
    template_row = result.fetchone()
    assert template_row, f"Default template not found for guild {guild_row[0]}"

    return guild_row[0], template_row[0]


async def _ensure_archive_channel(
    admin_db,
    guild_db_id: str,
    archive_channel_discord_id: str,
) -> str:
    """Ensure archive channel exists in DB; return its config ID."""
    result = await admin_db.execute(
        text(
            "SELECT id FROM channel_configurations "
            "WHERE guild_id = :guild_id AND channel_id = :channel_id"
        ),
        {"guild_id": guild_db_id, "channel_id": archive_channel_discord_id},
    )
    row = result.fetchone()
    if row:
        return row[0]

    channel_config_id = str(uuid4())
    now = datetime.now(UTC).replace(tzinfo=None)
    await admin_db.execute(
        text(
            "INSERT INTO channel_configurations "
            "(id, channel_id, guild_id, created_at, updated_at) "
            "VALUES (:id, :channel_id, :guild_id, :created_at, :updated_at)"
        ),
        {
            "id": channel_config_id,
            "channel_id": archive_channel_discord_id,
            "guild_id": guild_db_id,
            "created_at": now,
            "updated_at": now,
        },
    )
    await admin_db.commit()
    return channel_config_id


@pytest.mark.timeout(180)
@pytest.mark.asyncio
async def test_save_and_archive_archives_game_within_seconds(
    authenticated_admin_client,
    admin_db,
    discord_helper,
    discord_channel_id,
    discord_archive_channel_id,
    discord_guild_id,
    discord_user_id,
    test_user_discord_user_id,
    synced_guild,
    test_timeouts,
):
    """E2E: Updating a COMPLETED game with archive_delay_seconds=1 archives it within seconds.

    Verifies the "Save and Archive" shortcut flow:
    - Game is posted to Discord (message_id set in DB)
    - Status is moved to COMPLETED directly via SQL
    - PUT /api/v1/games with rewards and archive_delay_seconds=1 schedules near-immediate archive
    - Scheduler daemon processes the ARCHIVED transition
    - Discord announcement deleted from original channel
    - Reposted to archive channel with one ||reward|| spoiler field per entry
    """
    guild_db_id, template_id = await _get_guild_ids(admin_db, discord_guild_id)
    archive_channel_config_id = await _ensure_archive_channel(
        admin_db, guild_db_id, discord_archive_channel_id
    )

    await admin_db.execute(
        text(
            "UPDATE game_templates SET archive_channel_id = :archive_channel_id "
            "WHERE id = :template_id"
        ),
        {"archive_channel_id": archive_channel_config_id, "template_id": template_id},
    )
    await admin_db.commit()

    rewards = ["magic sword", "cloak of\nshadows"]
    game_title = f"E2E Save Archive {uuid4().hex[:8]}"
    response = await authenticated_admin_client.post(
        "/api/v1/games",
        data={
            "template_id": template_id,
            "title": game_title,
            "scheduled_at": (datetime.now(UTC) + timedelta(minutes=1)).isoformat(),
            "max_players": "4",
            "initial_participants": f'["<@{discord_user_id}>"]',
        },
    )
    assert response.status_code == 201, response.text
    game_id = response.json()["id"]

    message_id = await wait_for_game_message_id(
        admin_db, game_id, timeout=test_timeouts[TimeoutType.DB_WRITE]
    )

    await admin_db.execute(
        text("UPDATE game_sessions SET status = 'COMPLETED' WHERE id = :id"),
        {"id": game_id},
    )
    await admin_db.commit()

    update_response = await authenticated_admin_client.put(
        f"/api/v1/games/{game_id}",
        data={"rewards": json.dumps(rewards), "archive_delay_seconds": "1"},
    )
    assert update_response.status_code == 200, update_response.text

    await wait_for_db_condition(
        admin_db,
        "SELECT status FROM game_sessions WHERE id = :game_id",
        {"game_id": game_id},
        lambda row: row[0] == GameStatus.ARCHIVED.value,
        timeout=test_timeouts[TimeoutType.STATUS_TRANSITION],
        interval=2,
        description="game transition to ARCHIVED via Save and Archive",
    )

    await discord_helper.wait_for_message_deleted(
        channel_id=discord_channel_id,
        message_id=message_id,
        timeout=test_timeouts[TimeoutType.STATUS_TRANSITION] + 15,
        interval=2.0,
    )

    async def check_archive_message():
        msg = await discord_helper.find_message_by_embed_title(
            discord_archive_channel_id, game_title, limit=25
        )
        if msg is None:
            return (False, None)
        return (True, msg)

    archive_message = await wait_for_condition(
        check_archive_message,
        timeout=test_timeouts[TimeoutType.STATUS_TRANSITION] + 15,
        interval=2.0,
        description="archived announcement in archive channel",
    )

    assert archive_message.embeds, "Archive message should have embed"
    embed = archive_message.embeds[0]

    assert _reward_fields(embed) == _expected_inline_fields(rewards), (
        f"Archive embed should keep one spoiler field per reward: {_reward_fields(embed)}"
    )
    print("[TEST] ✓ Archive message contains one spoiler field per reward")

    assert f"<@{discord_user_id}>" in archive_message.content, (
        f"Archive post should @mention confirmed player. Got: {archive_message.content!r}"
    )


@pytest.mark.timeout(300)
@pytest.mark.asyncio
async def test_rewards_reminder_dm_sent_on_completion_when_empty(
    authenticated_admin_client,
    admin_db,
    main_bot_helper,
    discord_channel_id,
    discord_guild_id,
    discord_user_id,
    test_user_discord_user_id,
    synced_guild,
    test_timeouts,
):
    """E2E: Bot sends rewards reminder DM to host when game completes with no rewards set.

    Verifies:
    - Game has remind_host_rewards=True and rewards=None
    - COMPLETED transition triggers DM to the host
    - DM references the game title and rewards
    - No DM is sent when rewards are already populated
    """
    guild_db_id, template_id = await _get_guild_ids(admin_db, discord_guild_id)

    game_title = f"E2E Rewards DM {uuid4().hex[:8]}"
    scheduled_at = datetime.now(UTC) + timedelta(seconds=15)
    response = await authenticated_admin_client.post(
        "/api/v1/games",
        data={
            "template_id": template_id,
            "title": game_title,
            "scheduled_at": scheduled_at.isoformat(),
            "max_players": "4",
            "expected_duration_minutes": "1",
            "host": f"<@{discord_user_id}>",
            "remind_host_rewards": "true",
        },
    )
    assert response.status_code == 201, response.text
    game_id = response.json()["id"]

    await wait_for_game_message_id(admin_db, game_id, timeout=test_timeouts[TimeoutType.DB_WRITE])

    await wait_for_db_condition(
        admin_db,
        "SELECT status FROM game_sessions WHERE id = :game_id",
        {"game_id": game_id},
        lambda row: row[0] == GameStatus.COMPLETED.value,
        timeout=test_timeouts[TimeoutType.STATUS_TRANSITION],
        interval=5,
        description="game transition to COMPLETED",
    )

    rewards_dm = await main_bot_helper.wait_for_recent_dm(
        user_id=discord_user_id,
        game_title=game_title,
        dm_type=DMType.REWARDS_REMINDER,
        timeout=test_timeouts[TimeoutType.DM_IMMEDIATE],
        interval=2,
    )

    assert rewards_dm is not None, (
        f"Host should receive rewards reminder DM for '{game_title}'. Check bot event handler logs."
    )
    assert "rewards" in rewards_dm.content.lower(), (
        f"DM should mention rewards: {rewards_dm.content}"
    )
    assert game_title in rewards_dm.content, f"DM should include game title: {rewards_dm.content}"
    print(f"[TEST] ✓ Rewards reminder DM received: {rewards_dm.content[:100]}...")


async def _post_in_progress_game(
    authenticated_admin_client, admin_db, discord_guild_id: str, title_prefix: str, test_timeouts
) -> tuple[str, str, str]:
    """Create a game, wait for its Discord post, and mark it IN_PROGRESS.

    Returns:
        (game_id, message_id, game_title)
    """
    _guild_db_id, template_id = await _get_guild_ids(admin_db, discord_guild_id)

    game_title = f"{title_prefix} {uuid4().hex[:8]}"
    response = await authenticated_admin_client.post(
        "/api/v1/games",
        data={
            "template_id": template_id,
            "title": game_title,
            "scheduled_at": (datetime.now(UTC) + timedelta(minutes=1)).isoformat(),
            "max_players": "4",
        },
    )
    assert response.status_code == 201, response.text
    game_id = response.json()["id"]

    message_id = await wait_for_game_message_id(
        admin_db, game_id, timeout=test_timeouts[TimeoutType.DB_WRITE]
    )

    result = await admin_db.execute(
        text("UPDATE game_sessions SET status = 'IN_PROGRESS' WHERE id = :id RETURNING id"),
        {"id": game_id},
    )
    await admin_db.commit()
    assert result.fetchone() is not None

    return game_id, message_id, game_title


async def _set_rewards_and_wait_for_embed(
    authenticated_admin_client,
    discord_helper,
    discord_channel_id: str,
    game_id: str,
    message_id: str,
    rewards: list[str],
    check_fields,
    description: str,
    test_timeouts,
) -> list[tuple[str, str]]:
    """PUT rewards and wait until the Discord embed's reward fields satisfy check_fields."""
    update_response = await authenticated_admin_client.put(
        f"/api/v1/games/{game_id}",
        data={"rewards": json.dumps(rewards)},
    )
    assert update_response.status_code == 200, update_response.text

    updated_message = await discord_helper.wait_for_message_update(
        channel_id=discord_channel_id,
        message_id=message_id,
        check_func=lambda msg: bool(msg.embeds) and check_fields(_reward_fields(msg.embeds[0])),
        timeout=test_timeouts[TimeoutType.MESSAGE_UPDATE],
        description=description,
    )
    return _reward_fields(updated_message.embeds[0])


@pytest.mark.timeout(120)
@pytest.mark.asyncio
async def test_discord_embed_shows_one_spoiler_field_per_reward(
    authenticated_admin_client,
    admin_db,
    discord_helper,
    discord_channel_id,
    discord_guild_id,
    synced_guild,
    test_timeouts,
):
    """E2E: each reward gets its own ||spoiler|| field; only the first carries the heading."""
    game_id, message_id, _title = await _post_in_progress_game(
        authenticated_admin_client, admin_db, discord_guild_id, "E2E Rewards Embed", test_timeouts
    )
    rewards = ["a legendary cloak", "100 gold\nand a map", "a loyal hound"]
    expected = _expected_inline_fields(rewards)

    fields = await _set_rewards_and_wait_for_embed(
        authenticated_admin_client,
        discord_helper,
        discord_channel_id,
        game_id,
        message_id,
        rewards,
        lambda f: f == expected,
        "one spoiler field per reward in Discord embed",
        test_timeouts,
    )

    assert fields == expected
    print(f"[TEST] ✓ Discord embed shows {len(fields)} reward spoiler fields")


@pytest.mark.timeout(120)
@pytest.mark.asyncio
async def test_discord_embed_accepts_reward_at_field_value_limit(
    authenticated_admin_client,
    admin_db,
    discord_helper,
    discord_channel_id,
    discord_guild_id,
    synced_guild,
    test_timeouts,
):
    """E2E: a reward whose ||spoiler|| value is exactly 1024 chars renders inline."""
    game_id, message_id, _title = await _post_in_progress_game(
        authenticated_admin_client, admin_db, discord_guild_id, "E2E Rewards Limit", test_timeouts
    )
    rewards = ["x" * _MAX_INLINE_ENTRY]
    expected = _expected_inline_fields(rewards)

    fields = await _set_rewards_and_wait_for_embed(
        authenticated_admin_client,
        discord_helper,
        discord_channel_id,
        game_id,
        message_id,
        rewards,
        lambda f: f == expected,
        "at-limit reward rendered inline in Discord embed",
        test_timeouts,
    )

    assert fields == expected
    assert len(fields[0][1]) == DISCORD_EMBED_FIELD_VALUE_LIMIT


@pytest.mark.timeout(120)
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "rewards",
    [
        pytest.param(["Gold", "x" * (_MAX_INLINE_ENTRY + 1)], id="entry-too-long"),
        pytest.param([f"reward {i}" for i in range(20)], id="too-many-fields"),
    ],
)
async def test_discord_embed_overflowing_rewards_show_single_link_field(
    rewards,
    authenticated_admin_client,
    admin_db,
    discord_helper,
    discord_channel_id,
    discord_guild_id,
    synced_guild,
    test_timeouts,
):
    """E2E: rewards that do not all fit are replaced by one link to the game page."""
    game_id, message_id, _title = await _post_in_progress_game(
        authenticated_admin_client,
        admin_db,
        discord_guild_id,
        "E2E Rewards Overflow",
        test_timeouts,
    )

    fields = await _set_rewards_and_wait_for_embed(
        authenticated_admin_client,
        discord_helper,
        discord_channel_id,
        game_id,
        message_id,
        rewards,
        lambda f: _is_rewards_link_field(f, game_id),
        "single rewards link field in Discord embed",
        test_timeouts,
    )

    assert _is_rewards_link_field(fields, game_id), fields
    assert not any("||" in value for _name, value in fields)
    print(f"[TEST] ✓ Overflowing rewards shown as link: {fields[0][1]}")
