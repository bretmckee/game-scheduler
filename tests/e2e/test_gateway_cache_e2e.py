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


"""E2E tests verifying gateway-driven Redis cache population at bot startup.

Asserts that _rebuild_redis_from_gateway writes all four key families
(guild, guild_channels, channel, guild_roles) into Redis during on_ready,
before any other e2e test runs.

No polling or waiting is needed: compose.e2e.yaml declares
`depends_on: bot: condition: service_healthy`, which guarantees on_ready
completed before any test container starts.
"""

import os

import pytest

from shared.cache import client as cache_client
from shared.cache import keys as cache_keys
from tests.e2e.conftest import DiscordTestEnvironment

pytestmark = [pytest.mark.e2e, pytest.mark.order(1)]


async def test_startup_cache_guild_key_written(
    discord_ids: DiscordTestEnvironment,
) -> None:
    """Verify discord:guild:{guild_a_id} is a dict with id and name after startup."""
    redis = await cache_client.get_redis_client()
    key = cache_keys.CacheKeys.discord_guild(discord_ids.guild_a_id)
    data = await redis.get_json(key)

    assert data is not None, f"Expected Redis key {key!r} to be populated by on_ready"
    assert "id" in data, f"Guild cache entry missing 'id' field: {data}"
    assert "name" in data, f"Guild cache entry missing 'name' field: {data}"


async def test_startup_cache_guild_channels_key_written(
    discord_ids: DiscordTestEnvironment,
) -> None:
    """Verify discord:guild_channels:{guild_a_id} is a non-empty list after startup.

    Each item must contain id, name, and type fields.
    """
    redis = await cache_client.get_redis_client()
    key = cache_keys.CacheKeys.discord_guild_channels(discord_ids.guild_a_id)
    data = await redis.get_json(key)

    assert data is not None, f"Expected Redis key {key!r} to be populated by on_ready"
    assert isinstance(data, list), f"Expected list, got {type(data).__name__}"
    assert len(data) > 0, "Guild channels list must not be empty"

    for item in data:
        assert "id" in item, f"Channel entry missing 'id': {item}"
        assert "name" in item, f"Channel entry missing 'name': {item}"
        assert "type" in item, f"Channel entry missing 'type': {item}"


async def test_startup_cache_channel_key_written(
    discord_ids: DiscordTestEnvironment,
) -> None:
    """Verify discord:channel:{channel_a_id} is a dict with a name field after startup."""
    redis = await cache_client.get_redis_client()
    key = cache_keys.CacheKeys.discord_channel(discord_ids.channel_a_id)
    data = await redis.get_json(key)

    assert data is not None, f"Expected Redis key {key!r} to be populated by on_ready"
    assert "name" in data, f"Channel cache entry missing 'name' field: {data}"


async def test_startup_cache_guild_roles_key_written(
    discord_ids: DiscordTestEnvironment,
) -> None:
    """Verify discord:guild_roles:{guild_a_id} is a non-empty list after startup.

    Each item must contain id, name, color, position, and managed fields.
    """
    redis = await cache_client.get_redis_client()
    key = cache_keys.CacheKeys.discord_guild_roles(discord_ids.guild_a_id)
    data = await redis.get_json(key)

    assert data is not None, f"Expected Redis key {key!r} to be populated by on_ready"
    assert isinstance(data, list), f"Expected list, got {type(data).__name__}"
    assert len(data) > 0, "Guild roles list must not be empty"

    for item in data:
        assert "id" in item, f"Role entry missing 'id': {item}"
        assert "name" in item, f"Role entry missing 'name': {item}"
        assert "color" in item, f"Role entry missing 'color': {item}"
        assert "position" in item, f"Role entry missing 'position': {item}"
        assert "managed" in item, f"Role entry missing 'managed': {item}"


async def test_startup_cache_known_role_id_in_guild_roles(
    discord_ids: DiscordTestEnvironment,
) -> None:
    """Verify DISCORD_TEST_ROLE_A_ID appears in the cached guild roles list.

    Skips gracefully when the env var is absent so CI runs without the
    optional role configuration still pass.
    """
    role_id = os.environ.get("DISCORD_TEST_ROLE_A_ID", "")
    if not role_id:
        pytest.skip("DISCORD_TEST_ROLE_A_ID not set — skipping known-role assertion")

    redis = await cache_client.get_redis_client()
    key = cache_keys.CacheKeys.discord_guild_roles(discord_ids.guild_a_id)
    data = await redis.get_json(key)

    assert data is not None, f"Expected Redis key {key!r} to be populated by on_ready"
    assert isinstance(data, list), f"Expected list, got {type(data).__name__}"

    cached_role_ids = [str(item["id"]) for item in data if "id" in item]
    assert role_id in cached_role_ids, (
        f"DISCORD_TEST_ROLE_A_ID {role_id!r} not found in cached guild roles: {cached_role_ids}"
    )
