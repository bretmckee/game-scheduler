<!-- markdownlint-disable-file -->

# Changes: Gateway-Driven Cache Enhancement

**Plan**: .copilot-tracking/planning/plans/20260411-01-gateway-cache-enhancement.plan.md
**Details**: .copilot-tracking/planning/details/20260411-01-gateway-cache-enhancement-details.md

---

## Phase 1: on_ready Redis Cache Rebuild — COMPLETE

### Added

- `tests/unit/bot/test_bot_ready.py` — Four unit tests verifying `on_ready` writes
  `discord:guild`, `discord:guild_channels`, `discord:channel`, and `discord:guild_roles`
  keys to Redis from the in-memory gateway cache without any REST calls.

### Modified

- `shared/cache/ttl.py` — Added `DISCORD_GUILD_ROLES: int = 300` constant (was missing;
  required by `on_ready` implementation and test assertions).
- `services/bot/bot.py` — Added `CacheKeys` and `CacheTTL` imports; added
  `_rebuild_redis_from_gateway` method that loops over `self.guilds` and writes guild,
  channel-list, per-channel, and role-list keys to Redis; updated `on_ready` to call
  `await self._rebuild_redis_from_gateway()` before `_recover_pending_workers`.

---

## Phase 2: role_checker.py — Use In-Memory Cache — COMPLETE

### Modified

- `tests/unit/services/bot/auth/test_role_checker.py` — Added six tests verifying each
  of the five methods (`get_user_role_ids`, `get_guild_roles`, `check_manage_guild_permission`,
  `check_manage_channels_permission`, `check_administrator_permission`, `check_game_host_permission`)
  does not call `fetch_guild()`; updated all existing tests that set up `fetch_guild` as
  `AsyncMock` to instead set up `get_guild` as `MagicMock`.

- `services/bot/auth/role_checker.py` — Replaced `await self.bot.fetch_guild(int(guild_id))`
  with `self.bot.get_guild(int(guild_id))` (synchronous, in-memory, no `await`) in all five
  methods: `get_user_role_ids` (line 78), `get_guild_roles` (line 114),
  `check_manage_guild_permission` (line 151), `check_manage_channels_permission` (line 177),
  `check_administrator_permission` (line 203). Eliminates at least one REST call per role
  check that misses the `user_roles` Redis cache.

---

## Phase 3: Remove Redundant fetch_channel in handlers.py — COMPLETE

### Modified

- `tests/unit/bot/events/test_handlers_lifecycle_events.py` — Added three tests verifying
  `_validate_discord_channel` does not call `discord_api.fetch_channel`, returns `False`
  when `get_channel()` returns `None`, and returns `True` when `get_channel()` returns a
  valid channel.

- `services/bot/events/handlers.py` — Replaced `_validate_discord_channel` body: removed
  `get_discord_client()` / `await discord_api.fetch_channel(channel_id)` pre-check and
  replaced with `self.bot.get_channel(int(channel_id))`. This eliminates one REST call per
  `game.created` event that previously validated the channel before processing.

---

## Phase 4: Gateway Event Handlers — COMPLETE

### Added

- `tests/unit/bot/test_bot_events.py` — Nine unit tests verifying the six new gateway
  event handlers correctly write/invalidate Redis keys:
  - `on_guild_channel_create`: writes `discord:channel:{id}` and deletes `discord:guild_channels:{guild_id}`
  - `on_guild_channel_update`: updates `discord:channel:{id}` and deletes `discord:guild_channels:{guild_id}`
  - `on_guild_channel_delete`: deletes both `discord:channel:{id}` and `discord:guild_channels:{guild_id}`
  - `on_guild_role_create`, `on_guild_role_update`, `on_guild_role_delete`: each deletes `discord:guild_roles:{guild_id}`

### Modified

- `services/bot/bot.py` — Added six new gateway event handler methods between
  `_rebuild_redis_from_gateway` and `on_disconnect`. Channel handlers use
  `redis.set_json(..., None)` (no TTL) for individual channel keys and `redis.delete` for
  the guild channel list. Role handlers use invalidation-only (`redis.delete`) so the next
  `fetch_guild_roles` call rebuilds from Discord rather than storing stale role data.

---

## Phase 5: Fix \_make_api_request Guard + Remove TTLs — COMPLETE

### Modified

- `tests/unit/shared/discord/test_discord_api_client.py` — Added two tests to
  `TestMakeAPIRequest`:
  - `test_cache_key_with_ttl_none_writes_to_redis`: verifies `_make_api_request` calls
    `redis.set` with `ttl=None` when `cache_key` is set and `cache_ttl=None`.
  - `test_cache_key_with_ttl_int_writes_to_redis`: regression guard verifying the
    `cache_ttl=300` path still writes to Redis unchanged.

- `shared/discord/client.py` — Changed `if cache_key and cache_ttl:` to `if cache_key:`
  on the Redis write guard. `cache.client.set()` already handles `ttl=None` via a plain
  `SET` (no `SETEX`), so the guard was incorrectly suppressing writes for gateway-maintained
  keys whose TTL is `None`.

- `shared/cache/ttl.py` — Set `DISCORD_CHANNEL`, `DISCORD_GUILD`, `DISCORD_GUILD_CHANNELS`,
  and `DISCORD_GUILD_ROLES` to `None` (type annotated as `int | None`). These keys are now
  maintained by gateway events and must never expire. `DISCORD_USER` and `APP_INFO` retain
  their TTLs since they are not gateway-maintained.

---

## Phase 6: get_guild_member Redis Caching — COMPLETE

### Added

- `tests/unit/shared/discord/test_discord_api_client.py` — Two new tests in
  `TestGuildMemberMethods`:
  - `test_get_guild_member_cache_miss`: verifies that a cache miss fetches from the
    Discord REST API, calls `redis.get` with the key `discord:member:{guild_id}:{user_id}`,
    and stores the result with `ttl=CacheTTL.DISCORD_MEMBER`.
  - `test_get_guild_member_cache_hit`: verifies that a cache hit returns the stored data
    without making any REST call (`redis.set` not called).

### Modified

- `shared/cache/keys.py` — Added `CacheKeys.discord_member(guild_id, user_id)` returning
  `f"discord:member:{guild_id}:{user_id}"`.

- `shared/cache/ttl.py` — Added `DISCORD_MEMBER: int = 300` (5-minute TTL for
  guild member objects; shorter than guild/channel data since membership can change).

- `shared/discord/client.py` — Rewrote `get_guild_member` to follow the same read-through
  caching pattern as `fetch_guild`: checks Redis first via `redis.get(cache_key)`; on a
  miss, delegates to `_make_api_request` with `cache_key` and
  `cache_ttl=CacheTTL.DISCORD_MEMBER` so the result is stored on success.

- `tests/unit/services/bot/auth/test_role_checker.py` — Updated seven tests and added two
  new tests for `get_user_role_ids`:
  - `test_get_user_role_ids_does_not_call_fetch_member`: verifies `guild.fetch_member` is
    never called; uses `patch("services.bot.auth.role_checker.get_discord_client")`.
  - `test_get_user_role_ids_uses_get_guild_member`: verifies `discord_api.get_guild_member`
    is called with the correct `(guild_id, user_id)` string arguments and that role IDs
    come directly from `member_data["roles"]`.
  - Updated `test_get_user_role_ids_from_discord`, `test_get_user_role_ids_force_refresh`,
    `test_get_user_role_ids_does_not_call_fetch_guild` to patch `get_discord_client` and
    mock `get_guild_member` returning `{"roles": [...]}`.
  - Updated `test_get_user_role_ids_member_not_found`, `test_get_user_role_ids_member_returns_none`
    to raise `DiscordAPIError(404, "Unknown Member")` instead of `discord.NotFound`.
  - Updated `test_get_user_role_ids_forbidden` to raise `DiscordAPIError(403, "Missing Permissions")`
    instead of `discord.Forbidden`.
  - Added `from shared.discord.client import DiscordAPIError` and `from unittest.mock import patch`
    imports to the test file.

- `services/bot/auth/role_checker.py` — Added imports `get_discord_client` and
  `DiscordAPIError`; replaced the `guild.fetch_member(int(user_id))` call in
  `get_user_role_ids` with `discord_api = get_discord_client()` followed by
  `member_data = await discord_api.get_guild_member(guild_id, user_id)`; extracts
  `role_ids = member_data.get("roles", [])`; replaces `except discord.NotFound` and
  `except discord.Forbidden` with a single `except DiscordAPIError as e` handler that
  checks `e.status`. Eliminates one uncached `fetch_member` REST call per role-check cache
  miss, replacing it with a cacheable `get_guild_member` call.
