<!-- markdownlint-disable-file -->

# Task Details: Discord Gateway Intent Redis Projection

## Research Reference

**Source Research**: #file:../research/20260418-01-gateway-intent-redis-projection-research.md

---

## Phase 1: Foundation — Enable Intent and Add Key Constants

### Task 1.1: Enable GUILD_MEMBERS Privileged Intent

Set `Intents.members = True` and `chunk_guilds_at_startup = True` on the bot. This is a prerequisite for `guild.members` being populated at `on_ready`. No behavior change visible to users yet — it only enables gateway member data delivery.

Also requires toggling "Server Members Intent" in the Discord Developer Portal for the bot application.

- **Files**:
  - `services/bot/bot.py` — update `Intents` construction near line 121
- **Success**:
  - `Intents.members = True` and `chunk_guilds_at_startup = True` are set
  - Bot reconnects and logs `on_ready` without errors after the change
- **Research References**:
  - #file:../research/20260418-01-gateway-intent-redis-projection-research.md (Lines 83–97) — external research on `GUILD_MEMBERS` intent behavior, chunking timing, and `on_ready` guarantees
- **Dependencies**:
  - Discord Developer Portal toggle must be enabled before the change is deployed

### Task 1.2: Add Projection Key Constants to shared/cache/keys.py

Add four new key-factory functions to `shared/cache/keys.py`:

- `proj_gen() -> str` — returns `"proj:gen"`
- `proj_member(gen: str, guild_id: str, uid: str) -> str` — returns `f"proj:member:{gen}:{guild_id}:{uid}"`
- `proj_user_guilds(gen: str, uid: str) -> str` — returns `f"proj:user_guilds:{gen}:{uid}"`
- `bot_last_seen() -> str` — returns `"bot:last_seen"`

No `proj_user_status` key. No changes to existing TTL constants in this step.

- **Files**:
  - `shared/cache/keys.py` — add four key functions after existing keys
- **Success**:
  - All four functions exist and return the documented key strings
  - No existing keys changed
  - Unit tests for all four functions pass
- **Research References**:
  - #file:../research/20260418-01-gateway-intent-redis-projection-research.md (Lines 163–170) — Redis key schema section
  - #file:../research/20260418-01-gateway-intent-redis-projection-research.md (Lines 23–29) — existing key patterns from `shared/cache/keys.py`
- **Dependencies**:
  - None — independent of Task 1.1

---

## Phase 2: Bot-side Writer

### Task 2.1: Create services/bot/guild_projection.py

Create a new module that implements the full repopulation writer. Follow the OTel pattern from `bot.py` lines 62–88 exactly — module-level meter, then named instrument instances.

**Module structure:**

```
module-level OTel meter and 3 instruments
  - bot.projection.repopulation.started (counter, unit="1", attribute: reason)
  - bot.projection.repopulation.duration (histogram, unit="s", attribute: reason)
  - bot.projection.repopulation.members_written (histogram, unit="1", attribute: reason)

repopulate_all(*, bot, redis, reason) -> None
  - compute new_gen = str(int(datetime.now(UTC).timestamp() * 1000))
  - read prev_gen = await redis.get(proj_gen())
  - increment started counter
  - for each guild in bot.guilds, for each member in guild.members:
      call write_member; accumulate user_guild_ids
  - for each uid, write_user_guilds
  - SET proj:gen = new_gen  (generation flip — completeness signal)
  - SCAN+DEL all proj:*:{prev_gen}:* keys
  - record duration and members_written histograms

write_member(*, redis, gen, guild_id, uid, member) -> None
  - SET proj:member:{gen}:{guild_id}:{uid} = JSON of {roles, nick, global_name, username, avatar_url}
  - no TTL

write_user_guilds(*, redis, gen, uid, guild_ids) -> None
  - SET proj:user_guilds:{gen}:{uid} = JSON list of guild_id strings
  - no TTL

write_bot_last_seen(*, redis) -> None
  - SET bot:last_seen = UTC ISO timestamp with TTL = heartbeat_interval * 3
```

The generation flip (`SET proj:gen`) must come **after** all data writes are complete. This invariant ensures any reader observing the new gen value will find all its data already present.

- **Files**:
  - `services/bot/guild_projection.py` — create new file
  - `tests/unit/bot/test_guild_projection.py` — create unit tests (TDD: stub + xfail first)
- **Success**:
  - `repopulate_all` writes all member and user_guilds keys before flipping gen
  - Old generation keys are deleted after the gen flip
  - OTel counters and histograms fire with correct attributes on each repopulation
  - Unit tests cover: normal repopulation, gen flip ordering, old-gen cleanup, empty guild list
- **Research References**:
  - #file:../research/20260418-01-gateway-intent-redis-projection-research.md (Lines 101–130) — key discovery: correct write ordering, data-first / gen-flip-last invariant
  - #file:../research/20260418-01-gateway-intent-redis-projection-research.md (Lines 171–213) — recommended approach: full module structure with code examples
  - #file:../research/20260418-01-gateway-intent-redis-projection-research.md (Lines 60–66) — OTel pattern reference (bot.py lines 62–88)
- **Dependencies**:
  - Task 1.1 (intent enabled) and Task 1.2 (key constants) must be complete

### Task 2.2: Wire Bot Events and Heartbeat Task in bot.py

Add four gateway event handlers to `GameSchedulerBot` and a periodic heartbeat task:

```python
async def on_ready(self) -> None:
    # existing guild sync + new call:
    await guild_projection.repopulate_all(bot=self, redis=redis._client, reason="on_ready")

async def on_member_add(self, member: discord.Member) -> None:
    await guild_projection.repopulate_all(bot=self, redis=redis._client, reason="member_add")

async def on_member_update(self, before: discord.Member, after: discord.Member) -> None:
    await guild_projection.repopulate_all(bot=self, redis=redis._client, reason="member_update")

async def on_member_remove(self, member: discord.Member) -> None:
    await guild_projection.repopulate_all(bot=self, redis=redis._client, reason="member_remove")
```

Add a background task (started in `setup_hook`) that calls `write_bot_last_seen` on a fixed interval (e.g., 30 s).

- **Files**:
  - `services/bot/bot.py` — add handlers and heartbeat task
  - `tests/unit/bot/test_bot.py` — unit tests for event handler dispatch (TDD: stub + xfail first)
- **Success**:
  - All four handlers call `repopulate_all` with the correct `reason` string
  - Heartbeat task writes `bot:last_seen` on each tick
  - Existing `on_ready` behavior (guild sync) is preserved; `repopulate_all` is called after it
- **Research References**:
  - #file:../research/20260418-01-gateway-intent-redis-projection-research.md (Lines 214–237) — bot event wiring code examples
  - #file:../research/20260418-01-gateway-intent-redis-projection-research.md (Lines 83–97) — on_ready timing and session-resume behavior
- **Dependencies**:
  - Task 2.1 (guild_projection.py) must be complete

---

## Phase 3: API-side Reader

### Task 3.1: Create services/api/services/member_projection.py

Create the API-side reader module. Uses `_read_with_gen_retry()` for all Redis reads.

**Module structure:**

```
module-level OTel meter and 2 instruments
  - api.projection.read.retries (counter, unit="1")
  - api.projection.read.not_found (counter, unit="1")

_MAX_GEN_RETRIES = 3

_read_with_gen_retry(redis, key_fn, *key_args) -> str | None
  - reads proj:gen
  - up to _MAX_GEN_RETRIES iterations:
      GET key_fn(gen, *key_args)
      if value: return value
      re-read gen2
      if gen == gen2: increment not_found counter; return None  (gen stable, key absent)
      gen = gen2; increment retries counter
  - return None

get_user_guilds(uid, *, redis) -> list[str] | None
  - calls _read_with_gen_retry with proj_user_guilds key
  - parses JSON list; returns None if absent

get_member(guild_id, uid, *, redis) -> dict | None
  - calls _read_with_gen_retry with proj_member key
  - parses JSON dict; returns None if absent

get_user_roles(guild_id, uid, *, redis) -> list[str]
  - calls get_member; returns member["roles"] or [] if absent

is_bot_fresh(*, redis) -> bool
  - GET bot:last_seen; returns True if key present and timestamp within acceptable age
```

- **Files**:
  - `services/api/services/member_projection.py` — create new file
  - `tests/unit/api/test_member_projection.py` — create unit tests (TDD: stub + xfail first)
- **Success**:
  - `_read_with_gen_retry` handles gen-rotation window correctly (max 6 GETs)
  - `_read_retry_counter` increments on each retry iteration; `_read_not_found_counter` on stable-gen miss
  - All public functions return correct types for present, absent, and gen-rotation cases
  - Unit tests cover: cache hit, genuine miss, gen-rotation mid-read, max retry exhaustion
- **Research References**:
  - #file:../research/20260418-01-gateway-intent-redis-projection-research.md (Lines 101–131) — gen-rotation retry algorithm with annotated code example
  - #file:../research/20260418-01-gateway-intent-redis-projection-research.md (Lines 218–230) — reader function signatures
- **Dependencies**:
  - Task 1.2 (key constants) must be complete
  - Can be developed in parallel with Phase 2

---

## Phase 4: Call Site Migration

Migrate each call site independently. Old TTL-cache keys and new projection keys coexist during this phase. Each migration is independently shippable.

### Task 4.1: Migrate permissions.py verify_guild_membership (Highest Priority)

Replace `_get_user_guilds` / `_check_guild_membership` OAuth REST calls with `member_projection.get_user_guilds()`.

`verify_guild_membership` fires on every protected API route — this is the single highest-frequency REST call elimination.

- **Files**:
  - `services/api/dependencies/permissions.py` — replace `_get_user_guilds` internals
  - `tests/unit/api/test_permissions.py` — update tests
- **Success**:
  - `verify_guild_membership` makes zero OAuth REST calls per request
  - Returns 403 correctly when user is not in the guild
  - Uses `is_bot_fresh()` to return a clear degraded response when bot:last_seen is absent
- **Research References**:
  - #file:../research/20260418-01-gateway-intent-redis-projection-research.md (Lines 36–42) — current permissions.py behavior
  - #file:../research/20260418-01-gateway-intent-redis-projection-research.md (Lines 239–246) — replacement table entry
- **Dependencies**:
  - Phase 2 and Phase 3 must be complete and deployed

### Task 4.2: Migrate login_refresh.py Display Name Reads

Replace `get_current_user_guild_member` REST calls with `member_projection.get_member()`.

- **Files**:
  - `services/api/services/login_refresh.py` — replace REST calls
  - `tests/unit/api/test_login_refresh.py` — update tests
- **Success**:
  - `refresh_display_name_on_login` reads from Redis projection; makes zero REST calls
- **Research References**:
  - #file:../research/20260418-01-gateway-intent-redis-projection-research.md (Lines 29–35) — current login_refresh.py behavior
  - #file:../research/20260418-01-gateway-intent-redis-projection-research.md (Lines 239–246) — replacement table
- **Dependencies**:
  - Phase 2 and Phase 3 complete

### Task 4.3: Migrate RoleChecker REST Fallback

Replace `discord_api.get_guild_member` REST fallback in `RoleChecker.get_user_role_ids` with `member_projection.get_user_roles()`.

- **Files**:
  - `services/bot/auth/role_checker.py` — replace REST fallback
  - `tests/unit/bot/test_role_checker.py` — update tests
- **Success**:
  - `get_user_role_ids` reads from Redis projection; REST fallback removed
- **Research References**:
  - #file:../research/20260418-01-gateway-intent-redis-projection-research.md (Lines 22–27) — current role_checker.py behavior
- **Dependencies**:
  - Phase 2 and Phase 3 complete

### Task 4.4: Migrate DisplayNameResolver REST Fallback

Replace `discord_api.get_guild_members_batch` REST fallback in `DisplayNameResolver` with `member_projection.get_member()`.

- **Files**:
  - `services/api/services/display_names.py` — replace REST fallback
  - `tests/unit/api/test_display_names.py` — update tests
- **Success**:
  - `DisplayNameResolver` resolves display names from Redis projection; zero REST calls
- **Research References**:
  - #file:../research/20260418-01-gateway-intent-redis-projection-research.md (Lines 43–49) — current display_names.py behavior
  - #file:../research/20260418-01-gateway-intent-redis-projection-research.md (Lines 239–246) — replacement table
- **Dependencies**:
  - Phase 2 and Phase 3 complete

---

## Phase 5: Cleanup

### Task 5.1: Remove Dead Code

After all Phase 4 call sites are migrated and verified, delete or gut the following:

- `services/api/services/login_refresh.py` — delete entirely (or gut REST call paths if any non-REST logic remains)
- REST fallback paths in `DisplayNameResolver` and `RoleChecker` already removed in Phase 4
- `_get_user_guilds` and `_check_guild_membership` helper functions in `permissions.py`
- TTL constants `DISPLAY_NAME`, `USER_ROLES`, `DISCORD_MEMBER`, `USER_GUILDS` from `shared/cache/ttl.py`
- Old TTL-cache key functions in `shared/cache/keys.py` if no longer referenced

Verify zero Discord REST calls from the API service before closing this task.

- **Files**:
  - `services/api/services/login_refresh.py`
  - `services/api/dependencies/permissions.py`
  - `shared/cache/ttl.py`
  - `shared/cache/keys.py`
- **Success**:
  - `grep -r "discord_api\|get_guild_member\|get_user_guilds.*oauth\|get_current_user_guild_member" services/api/` returns no matches
  - All TTL constants removed; no references remain
  - Full test suite passes
- **Research References**:
  - #file:../research/20260418-01-gateway-intent-redis-projection-research.md (Lines 239–258) — full dead-code removal list
- **Dependencies**:
  - All Phase 4 tasks complete

### Task 5.2: Drop user_display_names Table

Add an Alembic migration to drop the `user_display_names` table and delete `UserDisplayNameService` and its associated model/data-access files.

- **Files**:
  - `alembic/versions/<new_revision>.py` — drop table migration
  - `services/api/services/display_names.py` — delete or reduce to projection reader only
  - Any `user_display_names` model and data-access files
- **Success**:
  - Migration applies cleanly in dev and staging
  - No import references to `UserDisplayNameService` remain
  - Integration tests pass after migration
- **Research References**:
  - #file:../research/20260418-01-gateway-intent-redis-projection-research.md (Lines 239–258) — user_display_names in the replacement table
- **Dependencies**:
  - Task 5.1 complete

---

## Dependencies

- `discord.py` `GUILD_MEMBERS` intent toggle in Discord Developer Portal
- `redis-py` async (`redis.asyncio`) — already present in codebase
- No new RabbitMQ events or consumers
- No `notify-keyspace-events` Redis configuration required

## Success Criteria

- `verify_guild_membership` fires zero OAuth REST calls per request after Phase 4
- `list_games` display name resolution reads only Redis; no Discord API calls in the hot path
- `api.projection.read.retries` OTel counter is zero under normal operation
- `bot:last_seen` absence causes a clear degraded response, not a silent error
- Zero Discord REST calls from the API server — confirmed by grep before closing Phase 9
- All unit tests pass at each phase boundary before merging

---

## Phase 6: Drop REST Fallbacks in DiscordAPIClient (Work Type A)

These five tasks remove the REST fallback path from `DiscordAPIClient` for each endpoint. The Redis cache is pre-populated and kept current by gateway events, so a cache miss indicates genuine data absence — not a reason to hit Discord REST. Replace all fallback calls with 503 responses or graceful absence handling at call sites.

### Task 6.1: Remove GET /guilds/{id}/channels REST Fallback

Remove the REST fallback from `get_guild_channels()` in `DiscordAPIClient`. Update call sites `channel_resolver.py → get_guild_channels()` and `games.py → get_guild_channels_safe()` to return 503 or an empty result on cache miss rather than triggering a Discord REST call.

- **Files**:
  - `shared/discord/client.py` — guard or remove `_fetch()` for `/guilds/{id}/channels` so cache miss raises instead of calling REST
  - `services/api/services/channel_resolver.py` — update `get_guild_channels()` call site to handle absence
  - `services/api/routes/games.py` — update `get_guild_channels_safe()` call site to return 503 on absence
  - `tests/unit/api/test_channel_resolver.py` — update unit tests
  - `tests/unit/api/test_games.py` — update unit tests for absent-channel behavior
- **Success**:
  - No REST call to `/guilds/{id}/channels` on a cache miss
  - Absence returns a 503 or empty list with a log warning
  - Unit tests verify 503/absence behavior on cache miss
- **Research References**:
  - #file:../research/20260418-01-gateway-intent-redis-projection-research.md (Lines 321–334) — Work Type A description and call site list
- **Dependencies**:
  - Phase 5 complete (all original call sites migrated)

### Task 6.2: Remove GET /channels/{id} REST Fallback

Remove the REST fallback from `fetch_channel_name_safe()`. Update all three call sites — `games.py`, `templates.py`, and `calendar_export.py` — to handle channel absence without triggering a Discord REST call.

- **Files**:
  - `shared/discord/client.py` — guard `_fetch()` for `/channels/{id}` so cache miss raises
  - `services/api/routes/games.py` — handle `fetch_channel_name_safe` absence as 503
  - `services/api/routes/templates.py` — handle absence as 503
  - `services/api/routes/calendar_export.py` — handle absence as 503
  - `tests/unit/api/test_games.py` — update tests
  - `tests/unit/api/test_templates.py` — update tests
  - `tests/unit/api/test_calendar_export.py` — update tests
- **Success**:
  - No REST call to `/channels/{id}` on a cache miss; returns 503 or degraded value
  - Unit tests cover absent-channel behavior for all three call sites
- **Research References**:
  - #file:../research/20260418-01-gateway-intent-redis-projection-research.md (Lines 321–334) — Work Type A call site list
- **Dependencies**:
  - Task 6.1 complete (pattern established)

### Task 6.3: Remove GET /guilds/{id} REST Fallback

Remove the REST fallback from `fetch_guild_name_safe()` in `games.py` and `calendar_export.py`.

- **Files**:
  - `shared/discord/client.py` — guard `_fetch()` for `/guilds/{id}` so cache miss raises
  - `services/api/routes/games.py` — handle absence as 503
  - `services/api/routes/calendar_export.py` — handle absence as 503
  - `tests/unit/api/test_games.py` — update tests
  - `tests/unit/api/test_calendar_export.py` — update tests
- **Success**:
  - No REST call to `/guilds/{id}` on a cache miss
  - Unit tests verify absence handling at both call sites
- **Research References**:
  - #file:../research/20260418-01-gateway-intent-redis-projection-research.md (Lines 321–334) — Work Type A
- **Dependencies**:
  - Task 6.2 complete

### Task 6.4: Remove GET /guilds/{id}/roles REST Fallback

Remove the REST fallback from the role list method in `DiscordAPIClient`. The `discord_guild_roles` Redis key is maintained by `_rebuild_redis_from_gateway` and role create/update gateway events; a cache miss is a genuine absence.

- **Files**:
  - `shared/discord/client.py` — remove or guard `_fetch()` for `/guilds/{id}/roles` so cache miss raises
  - Any call sites that use this method — update to handle absence without REST
  - Relevant unit tests — update
- **Success**:
  - No REST call to `/guilds/{id}/roles` on a cache miss
  - Call sites handle absence gracefully (return empty list or 503)
- **Research References**:
  - #file:../research/20260418-01-gateway-intent-redis-projection-research.md (Lines 321–334) — Work Type A
- **Dependencies**:
  - Task 6.3 complete

### Task 6.5: Replace GET /users/{user_id} in calendar_export.py with Projection Read

`calendar_export.py → fetch_user_display_name_safe()` fetches the host username for calendar export via Discord REST. Replace with `member_projection.get_member()` which already stores `username` and `global_name`.

- **Files**:
  - `services/api/routes/calendar_export.py` — replace REST call with `get_member()` projection read; use `username` or `global_name` from the member dict
  - `tests/unit/api/test_calendar_export.py` — update tests; add cases for hit and absent-member
- **Success**:
  - `fetch_user_display_name_safe()` makes zero REST calls; reads `username`/`global_name` from projection
  - Unit tests cover hit and absent-member cases
- **Research References**:
  - #file:../research/20260418-01-gateway-intent-redis-projection-research.md (Lines 321–334) — Work Type A, `GET /users/{user_id}` row
- **Dependencies**:
  - Phase 3 (member_projection.py) complete; Task 6.4 complete

---

## Phase 7: Add Permissions Bitfield and Replace has_permissions() (Work Type B)

`GET /users/@me/guilds` (OAuth) is called by `RoleVerificationService.has_permissions()` in `roles.py` to obtain the pre-computed `permissions` integer per guild, which is checked for `MANAGE_GUILD`, `MANAGE_CHANNELS`, and `ADMINISTRATOR` flags. This endpoint can be eliminated by storing `discord.Role.permissions.value` in the existing `discord_guild_roles` Redis cache and computing the bitfield locally.

### Task 7.1: Add permissions Field to \_role_list() in bot.py

`_role_list()` in `bot.py` (around line 238) currently omits the permissions bitfield. Add `"permissions": r.permissions.value` to each role entry. This populates the existing `discord_guild_roles` Redis cache with permission data on every `_rebuild_redis_from_gateway` call and every `on_guild_role_create`/`on_guild_role_update` event.

- **Files**:
  - `services/bot/bot.py` — add `"permissions": r.permissions.value` to `_role_list()` output dict
  - `tests/unit/bot/test_bot.py` — update `_role_list` tests to assert `"permissions"` field is present with correct value
- **Success**:
  - Each role entry in `discord_guild_roles` contains a `"permissions"` integer field
  - Redis keys updated on next `_rebuild_redis_from_gateway` call
  - Unit tests verify the field is populated
- **Research References**:
  - #file:../research/20260418-01-gateway-intent-redis-projection-research.md (Lines 335–356) — Work Type B root cause analysis and two-part fix
- **Dependencies**:
  - Phase 2 complete (`_rebuild_redis_from_gateway` wired to gateway events)

### Task 7.2: Replace has_permissions() with Local Bitfield Computation

Replace `RoleVerificationService.has_permissions()` OAuth REST call with local computation:

1. Get user role IDs from `member_projection.get_user_roles()`
2. Fetch guild role list from `CacheKeys.discord_guild_roles(guild_id)` (already in Redis with `permissions` field after Task 7.1)
3. OR-together the `permissions` value of each role the user holds, including `@everyone` (whose role ID equals the guild ID)
4. Check resulting integer against the requested permission flag

No new Redis keys required.

- **Files**:
  - `services/api/services/roles.py` — replace `has_permissions()` REST call with local bitfield computation
  - `tests/unit/api/test_roles.py` — update tests; add cases for `MANAGE_GUILD`, `MANAGE_CHANNELS`, `ADMINISTRATOR` flag checks; cover `@everyone` role inclusion
- **Success**:
  - `has_permissions()` makes zero OAuth REST calls; computes result from Redis data only
  - Permission flag checks produce correct results for all three supported flags
  - Unit tests cover: user holds the flag, user lacks the flag, `@everyone` role included correctly
- **Research References**:
  - #file:../research/20260418-01-gateway-intent-redis-projection-research.md (Lines 335–356) — Work Type B fix details and bitfield computation
- **Dependencies**:
  - Task 7.1 complete; Phase 3 (member_projection.py) complete

---

## Phase 8: Username Sorted Set Index for Member Search (Work Type C)

`GET /guilds/{id}/members/search` is called by `_search_guild_members()` in `participant_resolver.py` for prefix-match autocomplete on participant names. Replace with a Redis sorted set using `ZRANGEBYLEX` for O(log N + M) prefix queries, fully replicable from projection data.

### Task 8.1: Add proj_usernames Key Constant to shared/cache/keys.py

Add `proj_usernames(gen: str, guild_id: str) -> str` to `shared/cache/keys.py`, returning `f"proj:usernames:{gen}:{guild_id}"`. This key is a sorted set per guild, matched by the existing `proj:*:{old_gen}:*` SCAN+DEL pattern in `repopulate_all()` — no additional cleanup code needed.

- **Files**:
  - `shared/cache/keys.py` — add `proj_usernames` static method after existing `proj_*` key functions
  - `tests/unit/shared/test_cache_keys.py` — add unit test for the new key function
- **Success**:
  - `proj_usernames(gen, guild_id)` returns `f"proj:usernames:{gen}:{guild_id}"`
  - Unit test passes
- **Research References**:
  - #file:../research/20260418-01-gateway-intent-redis-projection-research.md (Lines 357–405) — Work Type C description, sorted set design, and `proj_usernames` key definition
- **Dependencies**:
  - Task 1.2 complete (existing `proj_*` key constant pattern established)

### Task 8.2: Update write_member() to Populate Username Sorted Set

In `write_member()` in `guild_projection.py`, after writing the member blob, `ZADD` entries to `proj:usernames:{gen}:{guild_id}` for each non-null name field (lowercased). Entry format: `{name_lowercase}\x00{uid}` — the null byte separator carries the uid in the single sorted-set entry without a second lookup. Up to 3 ZADD calls per member: `username` (always present), `global_name` (optional), `nick` (optional). Deduplicate if `global_name == username`.

- **Files**:
  - `services/bot/guild_projection.py` — update `write_member()` to ZADD name entries to the sorted set
  - `tests/unit/bot/test_guild_projection.py` — add tests: sorted set populated correctly; `global_name == username` yields one entry not two; null `nick`/`global_name` skipped; sorted set cleaned up by existing SCAN+DEL
- **Success**:
  - Sorted set populated with correct `{name}\x00{uid}` entries for all non-null name fields
  - Deduplication: `global_name == username` yields exactly one entry
  - Optional fields (`nick`, `global_name`) skipped when null/empty
  - Old-gen sorted set keys deleted by the existing SCAN+DEL in `repopulate_all()`
- **Research References**:
  - #file:../research/20260418-01-gateway-intent-redis-projection-research.md (Lines 357–405) — Work Type C write details, entry format, and deduplication rule
- **Dependencies**:
  - Task 8.1 complete; Task 2.1 (`write_member()` already exists)

### Task 8.3: Replace \_search_guild_members() with ZRANGEBYLEX Read

Add `search_members_by_prefix()` to `member_projection.py` using `ZRANGEBYLEX` on `proj:usernames:{gen}:{guild_id}`. Replace `_search_guild_members()` in `participant_resolver.py` with a call to `search_members_by_prefix()`. Use `seen_uids` deduplication to avoid returning the same member twice when `username` and `nick` both match the prefix.

- **Files**:
  - `services/api/services/member_projection.py` — add `search_members_by_prefix(guild_id, query, *, redis)` function
  - `services/api/services/participant_resolver.py` — replace `_search_guild_members()` REST call with `search_members_by_prefix()`
  - `tests/unit/api/test_member_projection.py` — add tests: prefix match returns correct members; `seen_uids` dedup works; empty result when gen absent; empty result when no match
  - `tests/unit/api/test_participant_resolver.py` — update tests
- **Success**:
  - Prefix queries return correct members via `ZRANGEBYLEX`
  - Same member matched on two name fields appears only once in results
  - Empty result returned when gen is absent (bot not yet populated)
  - Zero REST calls to `GET /guilds/{id}/members/search`
- **Research References**:
  - #file:../research/20260418-01-gateway-intent-redis-projection-research.md (Lines 357–405) — Work Type C read implementation with code example
- **Dependencies**:
  - Tasks 8.1 and 8.2 complete; Phase 3 (member_projection.py) complete

---

## Phase 9: Final Verification and Test Updates

### Task 9.1: Verify Zero Discord REST Calls from API Server

Run the grep verification from the revised appendix checklist. All items A1–A5, B, and C must be confirmed before declaring "zero Discord REST calls from the API server".

- **Files**: (no code changes — verification only)
- **Success**:
  - `grep -r "discord.com/api\|aiohttp.*session\.get" services/api/` returns zero matches outside of `shared/discord/client.py`
  - All revised checklist items (A1–A5, B, C) are checked off
  - Full unit test suite passes with zero Discord REST calls in any test exercising the API projection path
- **Research References**:
  - #file:../research/20260418-01-gateway-intent-redis-projection-research.md (Lines 406–417) — Step 7 revised checklist
- **Dependencies**:
  - All Phase 6, 7, and 8 tasks complete

### Task 9.2: Update Integration and E2E Tests

Review integration and e2e tests for any tests that mock or stub Discord REST endpoints that have been migrated to projection reads: member lookup, channel/guild name resolution, role verification, permissions checks, and participant search. Update mocks and fixtures to seed Redis projection data instead.

- **Files**:
  - `tests/integration/` — identify and update any tests that mock guild member, channel, guild, role, or permissions REST calls; replace with Redis projection seeding
  - `tests/e2e/` — identify and update any scenarios that depend on Discord REST behavior for the migrated endpoints; seed projection data in Redis test setup instead
  - Test fixtures, factories, or conftest files that generate Discord API mock responses for the above endpoints
- **Success**:
  - All integration tests pass with no Discord REST calls from the API service path
  - All e2e tests pass; scenarios that previously relied on Discord API mocks now use Redis projection data
  - No test still uses a Discord REST mock for member/channel/guild/role/permissions lookups that have been migrated to projection reads
- **Research References**:
  - #file:../research/20260418-01-gateway-intent-redis-projection-research.md (Lines 406–417) — verification checklist context
- **Dependencies**:
  - Task 9.1 complete; all Phase 6–8 tasks complete

---

## Updated Success Criteria (Phases 6–9)

- All Phase 6 REST fallbacks removed; cache miss returns 503 or graceful degradation — never triggers Discord REST
- `has_permissions()` computes permission flags from local Redis role cache data; zero OAuth REST calls per permission check
- Member search uses `ZRANGEBYLEX` on `proj:usernames` sorted set; zero REST calls to `/guilds/{id}/members/search`
- Grep verification passes: zero `discord.com/api` hits in `services/api/` outside `shared/discord/client.py`
- All integration and e2e tests pass after projection-data seeding replaces Discord REST mocks
