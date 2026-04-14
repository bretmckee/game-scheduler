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


"""Cache operation names, generic hit/miss counters, and latency histogram."""

import time
from enum import StrEnum
from typing import Any

from opentelemetry import metrics

from shared.cache.client import get_redis_client

_meter = metrics.get_meter(__name__)
_hit_counter = _meter.create_counter("cache.hits", description="Cache hits", unit="1")
_miss_counter = _meter.create_counter("cache.misses", description="Cache misses", unit="1")
_duration_histogram = _meter.create_histogram("cache.duration", unit="s")


class CacheOperation(StrEnum):
    """Symbolic names for every cache read site in the codebase."""

    FETCH_GUILD = "fetch_guild"
    FETCH_CHANNEL = "fetch_channel"
    FETCH_GUILD_ROLES = "fetch_guild_roles"
    FETCH_GUILD_CHANNELS = "fetch_guild_channels"
    FETCH_USER = "fetch_user"
    GET_GUILD_MEMBER = "get_guild_member"
    GET_APPLICATION_INFO = "get_application_info"
    GET_USER_GUILDS = "get_user_guilds"
    USER_ROLES_API = "user_roles_api"
    DISPLAY_NAME = "display_name"
    SESSION_LOOKUP = "session_lookup"
    SESSION_REFRESH = "session_refresh"
    OAUTH_STATE = "oauth_state"
    USER_ROLES_BOT = "user_roles_bot"
    GUILD_ROLES_BOT = "guild_roles_bot"


async def cache_get(key: str, operation: CacheOperation) -> Any | None:  # noqa: ANN401
    """
    Read a JSON value from Redis and record hit/miss counter and latency.

    Args:
        key: Redis cache key.
        operation: Symbolic operation name used as the metric label.

    Returns:
        Deserialized value on hit, None on miss.
    """
    redis = await get_redis_client()
    t0 = time.monotonic()
    result = await redis.get_json(key)
    hit = result is not None
    (_hit_counter if hit else _miss_counter).add(1, {"operation": operation})
    _duration_histogram.record(
        time.monotonic() - t0,
        {"operation": operation, "result": "hit" if hit else "miss"},
    )
    return result
