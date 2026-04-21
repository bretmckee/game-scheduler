<!-- markdownlint-disable-file -->

# Task Research Notes: Bot REST API Elimination

## Research Executed

### File Analysis

- `services/bot/auth/role_checker.py`
  - Three permission-check methods (`check_manage_guild_permission`, `check_manage_channels_permission`, `check_administrator_permission`) each call `guild.fetch_member()` (REST) despite `members` intent being active and `chunk_guilds_at_startup=True` in `bot.py`. The in-memory `guild.get_member()` provides the identical `guild_permissions` bitfield with zero REST cost.
  - `get_guild_roles` and `check_manage_guild_permission` already have tests asserting `fetch_guild` is NOT called — `fetch_member` replacements follow the same pattern.

- `services/bot/events/handlers.py`
  - `_validate_channel_for_refresh` (line 322): calls `discord_api.fetch_channel()` (Redis read) then `bot.get_channel()` (in-memory) then `bot.fetch_channel()` (REST fallback) — three layers for data the in-memory cache already holds.
  - `_get_bot_channel` (line 200): same get→fetch REST fallback pattern.
  - `_fetch_channel_and_message` (line 350): same get→fetch REST fallback pattern.
  - `_send_dm` (line 862): calls `discord_api.fetch_user()` as a pre-existence check, then immediately calls `bot.fetch_user()` (REST) to get the sendable object — double REST for a user that `bot.get_user()` already has in-memory.
  - `_handle_clone_confirmation` (line 836): calls `bot.fetch_user()` directly without attempting `bot.get_user()` first.

- `services/bot/bot.py`
  - `setup_hook` (line ~155): calls `sync_all_bot_guilds` → `discord_client.get_guilds(token=bot_token)` (REST) before the gateway connects. At this point `get_guild_channels()` in `guild_sync.py` calls `_read_cache_only` which returns 503 because Redis is empty — channel creation silently no-ops for every new guild on startup.
  - `on_guild_join` (line ~720): calls `sync_all_bot_guilds` → `get_guilds()` (REST) to fetch the entire bot guild list to find the one guild that just joined — the `guild` object is already available in the event parameter.
  - `_run_sweep_worker` (line ~585): `bot.get_channel()` → `bot.fetch_channel()` REST fallback. With `on_guild_channel_create/update/delete` handlers keeping the in-memory cache current, this fallback never fires in normal operation.

- `services/bot/guild_sync.py`
  - `sync_all_bot_guilds`: accepts a `DiscordAPIClient` and calls `get_guilds()` then per-guild `get_guild_channels()`. Needs a refactor to accept gateway-supplied guild/channel data directly so REST is never used.
  - `_create_guild_with_channels_and_template`: calls `client.get_guild_channels()` — now a Redis-only call that returns 503 during `setup_hook` because Redis is not yet populated.

- `services/bot/utils/discord_format.py`
  - `get_member_display_info`: uses `discord_api.get_guild_member()` which is a REST+Redis call. This serves the bot's game message formatting. With the member projection in Redis (populated from gateway), this could read from `guild_projection` instead — but this function is also called from the API service path where gateway data isn't available. Needs careful scoping.

### Code Search Results

- `fetch_member` in `services/bot/**/*.py`
  - 3 production call sites in `role_checker.py`; 14 test references all mocking `guild.fetch_member`
- `fetch_channel` in `services/bot/**/*.py`
  - 4 production call sites: `_get_bot_channel`, `_validate_channel_for_refresh`, `_fetch_channel_and_message`, `_run_sweep_worker`
- `fetch_user` in `services/bot/**/*.py`
  - 2 production call sites: `_send_dm` (line 882), `_handle_clone_confirmation` (line 836)
- `discord_api.fetch_user` in `_send_dm`
  - Called as a pre-check before `bot.fetch_user` — purely redundant
- `get_guilds` in `guild_sync.py`
  - Called once in `sync_all_bot_guilds`, consumed from `setup_hook` and `on_guild_join`
- `chunk_guilds_at_startup=True` in `bot.py`
  - Confirmed present in `GameSchedulerBot.__init__`; guarantees full member cache at `on_ready`
- `members` intent in `bot.py`
  - `discord.Intents(guilds=True, guild_messages=True, members=True)` — privileged members intent active

### Project Conventions

- Standards referenced: `services/bot/auth/role_checker.py` already has test `test_get_guild_roles_does_not_call_fetch_guild` enforcing gateway-only pattern — same pattern extends to `fetch_member`
- Instructions followed: `python.instructions.md`, `test-driven-development.instructions.md`

## Key Discoveries

### The Two-Cache Redundancy

Inside the bot process, `_validate_channel_for_refresh` maintains three layers for channel resolution:

1. **Redis** (`discord_api.fetch_channel`) — written by the bot's own gateway event handlers
2. **discord.py in-memory** (`bot.get_channel`) — also written by the same gateway events
3. **REST fallback** (`bot.fetch_channel`) — fires only if both caches miss simultaneously

Both caches 1 and 2 are populated from the same source (gateway events). Cache 1 (Redis) exists for the **API service**, which has no discord.py client. Inside the bot, cache 1 is pure overhead — `bot.get_channel()` already has the same data. Removing the Redis pre-check and REST fallback from bot-internal channel resolution collapses three layers to one.

### The `setup_hook` Silent Failure

`sync_all_bot_guilds` is called in `setup_hook` before the gateway connects and before `_rebuild_redis_from_gateway()` runs. The call sequence:

1. `get_guilds(token=bot_token)` → REST ✓ succeeds
2. For new guilds: `get_guild_channels(guild_id)` → `_read_cache_only()` → Redis miss → raises `DiscordAPIError(503)`
3. The 503 is caught by `except Exception` in `setup_hook` and swallowed silently

**Result:** new guild channel sync on startup is currently broken. Moving guild sync to `on_ready` (after `_rebuild_redis_from_gateway()`) and using `self.guilds` directly eliminates both the REST call and the silent failure.

### The `on_guild_join` Unnecessary Full Fetch

`on_guild_join` receives the joined `guild: discord.Guild` object directly from the gateway event. The current implementation ignores it and calls `sync_all_bot_guilds` → `get_guilds()` (REST for all guilds) to build the full guild list, then creates configs only for guilds absent from the DB. The event guild object already contains channels via `guild.channels`, so the entire REST path can be replaced with a targeted single-guild sync function that uses gateway data.

### `fetch_user` Elimination Rationale

`bot.get_user(id)` returns `None` only for users not in any shared guild. With `members` intent + `chunk_guilds_at_startup=True`, every member of every bot guild is cached. A user who has signed up for a game must have been in a guild — if they have since left all shared guilds, the DM will fail with `discord.Forbidden` regardless of whether we fetched their user object. The `fetch_user` REST call in the `None` case is therefore wasted before an inevitable failure.

### Message Operations Are Irreplaceable

All of the following are writes or intentional existence probes — no gateway substitute exists:

- `channel.send()` — post game announcements
- `message.edit()` — update embed on game change
- `message.delete()` — delete orphaned embeds after restore
- `user.send()` — reminder and notification DMs
- `interaction.response.*` / `interaction.followup.*` — button acknowledgments
- `channel.fetch_message()` — sweep probe (404 response IS the signal)
- `channel.history()` — orphaned embed scan after restore

## Recommended Approach

Replace all non-message REST calls in the bot with gateway-sourced equivalents. No fallbacks to REST for data reads. If gateway data is absent, log a warning and skip — same outcome as a failed REST call but without the network roundtrip.

### Changes by File

**`services/bot/auth/role_checker.py`**

- `check_manage_guild_permission`: `guild.fetch_member(int(user_id))` → `guild.get_member(int(user_id))`
- `check_manage_channels_permission`: same replacement
- `check_administrator_permission`: same replacement

**`services/bot/events/handlers.py`**

- `_validate_channel_for_refresh`: delete the `discord_api.fetch_channel()` pre-check; delete the `bot.fetch_channel()` fallback; use `bot.get_channel()` only
- `_get_bot_channel`: delete the `bot.fetch_channel()` fallback; use `bot.get_channel()` only
- `_fetch_channel_and_message`: delete the `bot.fetch_channel()` fallback; use `bot.get_channel()` only
- `_send_dm`: delete `discord_api.fetch_user()` pre-check; replace `bot.fetch_user()` with `bot.get_user()`; return `False` with warning if `None`
- `_handle_clone_confirmation`: replace `bot.fetch_user()` with `bot.get_user()`; skip with warning if `None`

**`services/bot/bot.py`**

- `setup_hook`: remove `sync_all_bot_guilds` call entirely (broken anyway — Redis empty at this point)
- `on_ready`: call new `sync_guilds_from_gateway(bot, db)` after `_rebuild_redis_from_gateway()`
- `on_guild_join`: replace `sync_all_bot_guilds` call with new `sync_single_guild_from_gateway(guild, db)`
- `_run_sweep_worker`: remove `bot.fetch_channel()` fallback; if `bot.get_channel()` returns `None`, log warning and skip

**`services/bot/guild_sync.py`**

- Add `sync_guilds_from_gateway(bot, db)`: iterates `bot.guilds`, creates configs for new guilds using `guild.channels` — no REST, no Redis reads
- Add `sync_single_guild_from_gateway(guild, db)`: handles `on_guild_join` — creates config for one guild using `guild.channels`
- `sync_all_bot_guilds` and `_create_guild_with_channels_and_template`: can be removed or kept only for the channel-refresh path in `_refresh_guild_channels`

## Implementation Guidance

- **Objectives**: Eliminate all non-message REST calls from the bot; fix the broken `setup_hook` guild sync; reduce bot → Discord API surface to message I/O only
- **Key Tasks**:
  1. Replace `fetch_member` with `get_member` in `role_checker.py` (3 methods)
  2. Strip Redis pre-check and REST fallback from 3 channel resolution helpers in `handlers.py`
  3. Replace `fetch_user` / `discord_api.fetch_user` with `get_user` in 2 DM send sites in `handlers.py`
  4. Move guild sync out of `setup_hook` into `on_ready`; add `sync_guilds_from_gateway` to `guild_sync.py`
  5. Replace `sync_all_bot_guilds` in `on_guild_join` with `sync_single_guild_from_gateway`
  6. Remove `fetch_channel` fallback from `_run_sweep_worker`
  7. Update unit tests for all changed methods (TDD: update test expectations first)
- **Dependencies**: `members` intent and `chunk_guilds_at_startup=True` already in place — no config changes needed
- **Success Criteria**:
  - `discord.http` logger emits zero entries during normal bot operation (excluding message writes and sweep probes)
  - `sync_all_bot_guilds` no longer called from `setup_hook`
  - New guild joining the bot correctly creates guild + channel configs via gateway data
  - All existing unit tests pass; new tests cover `get_member` path and `get_user` None-skip path
