<!-- markdownlint-disable-file -->

# Task Details: Bot REST API Elimination

## Research Reference

**Source Research**: #file:../research/20260421-02-bot-rest-api-elimination-research.md

---

## Phase 1: role_checker.py — Replace `fetch_member` with `get_member`

### Task 1.1: Update unit tests for all three permission-check methods

With `members` intent and `chunk_guilds_at_startup=True` already active, `guild.get_member()` provides the identical `guild_permissions` bitfield as `guild.fetch_member()` with zero REST cost. Three methods need updating: `check_manage_guild_permission`, `check_manage_channels_permission`, and `check_administrator_permission`.

Following TDD for existing code modifications: update test assertions to assert `get_member` is called and `fetch_member` is NOT called, then confirm the tests fail against current production code before making the production change.

The existing test `test_get_guild_roles_does_not_call_fetch_guild` demonstrates the exact pattern to follow — replicate it for `fetch_member`.

- **Files**:
  - `tests/unit/services/bot/auth/test_role_checker.py` — update 14 `fetch_member` mock references; add assertions that `fetch_member` is never called
- **Success**:
  - Tests assert `get_member` is called and `fetch_member.assert_not_called()` passes
  - `uv run pytest tests/unit/services/bot/auth/test_role_checker.py` shows the updated tests failing (RED)
- **Research References**:
  - #file:../research/20260421-02-bot-rest-api-elimination-research.md (Lines 9–16) — role_checker.py file analysis
  - #file:../research/20260421-02-bot-rest-api-elimination-research.md (Lines 66–67) — fetch_member production call site count
- **Dependencies**:
  - None

### Task 1.2: Replace `fetch_member` calls in production code

Replace `guild.fetch_member(int(user_id))` with `guild.get_member(int(user_id))` in all three methods. If `get_member` returns `None` (user not in cache), return the same "no permission" result as a failed fetch — do not raise.

- **Files**:
  - `services/bot/auth/role_checker.py` — 3 `fetch_member` call sites replaced with `get_member`
- **Success**:
  - `uv run pytest tests/unit/services/bot/auth/test_role_checker.py` passes (GREEN)
  - No `await` on `get_member` calls (it is synchronous)
- **Research References**:
  - #file:../research/20260421-02-bot-rest-api-elimination-research.md (Lines 103–106) — recommended replacements per method
- **Dependencies**:
  - Task 1.1 complete

---

## Phase 2: handlers.py — Eliminate Channel REST Fallbacks

### Task 2.1: Update unit tests for three channel resolution helpers

Three helpers in `services/bot/events/handlers.py` each follow a Redis→`get_channel`→`fetch_channel` (REST) pattern. Inside the bot process both caches are populated from the same gateway events, making the Redis pre-check and REST fallback pure overhead. Target methods: `_validate_channel_for_refresh`, `_get_bot_channel`, `_fetch_channel_and_message`.

Update tests to:

- Remove mocking of `discord_api.fetch_channel()` from `_validate_channel_for_refresh` tests
- Assert `bot.fetch_channel` is never called in any of the three methods
- Assert `bot.get_channel` is the only resolution call

- **Files**:
  - `tests/unit/services/bot/events/test_handlers.py` — update channel resolution test cases for the three helpers
- **Success**:
  - Updated tests fail against current production code (RED)
- **Research References**:
  - #file:../research/20260421-02-bot-rest-api-elimination-research.md (Lines 17–28) — handlers.py channel call analysis
  - #file:../research/20260421-02-bot-rest-api-elimination-research.md (Lines 57–58) — fetch_channel production call site list
  - #file:../research/20260421-02-bot-rest-api-elimination-research.md (Lines 85–100) — two-cache redundancy explanation
- **Dependencies**:
  - None

### Task 2.2: Strip Redis pre-check and REST fallback from three channel helpers

- `_validate_channel_for_refresh` (line ~322): delete the `discord_api.fetch_channel()` pre-check block; delete the `bot.fetch_channel()` fallback; leave only `bot.get_channel()`. If `get_channel` returns `None`, log a warning and return early.
- `_get_bot_channel` (line ~200): delete the `bot.fetch_channel()` fallback block; use `bot.get_channel()` only.
- `_fetch_channel_and_message` (line ~350): delete the `bot.fetch_channel()` fallback block; use `bot.get_channel()` only.

- **Files**:
  - `services/bot/events/handlers.py` — remove REST fallback paths in three methods
- **Success**:
  - `uv run pytest tests/unit/services/bot/events/test_handlers.py -k "channel"` passes (GREEN)
  - No remaining `fetch_channel` calls outside of `channel.fetch_message()` (the sweep probe — intentional REST)
- **Research References**:
  - #file:../research/20260421-02-bot-rest-api-elimination-research.md (Lines 107–113) — recommended changes for handlers.py channel methods
- **Dependencies**:
  - Task 2.1 complete

---

## Phase 3: handlers.py — Eliminate User Fetch REST Calls

### Task 3.1: Update unit tests for `_send_dm` and `_handle_clone_confirmation`

Two methods make unnecessary REST calls for user objects:

- `_send_dm` (line ~862): calls `discord_api.fetch_user()` as a pre-existence check then `bot.fetch_user()` to get the sendable object.
- `_handle_clone_confirmation` (line ~836): calls `bot.fetch_user()` directly without trying `bot.get_user()` first.

With `members` intent + `chunk_guilds_at_startup=True`, `bot.get_user()` covers all guild members. If it returns `None`, the DM would fail with `discord.Forbidden` regardless.

Update tests to:

- Remove mocking of `discord_api.fetch_user()` from `_send_dm` tests
- Assert `bot.fetch_user` is never called in either method
- Add a test case: `bot.get_user()` returns `None` → method returns `False` / skips with a warning log

- **Files**:
  - `tests/unit/services/bot/events/test_handlers.py` — update DM send test cases; add None-user skip test
- **Success**:
  - Updated tests fail against current production code (RED)
- **Research References**:
  - #file:../research/20260421-02-bot-rest-api-elimination-research.md (Lines 22–27) — fetch_user call analysis in handlers.py
  - #file:../research/20260421-02-bot-rest-api-elimination-research.md (Lines 59–63) — fetch_user production call site details
  - #file:../research/20260421-02-bot-rest-api-elimination-research.md (Lines 105–118) — fetch_user elimination rationale
- **Dependencies**:
  - None

### Task 3.2: Replace `fetch_user` calls in `_send_dm` and `_handle_clone_confirmation`

- `_send_dm`: delete the `discord_api.fetch_user()` pre-check; replace `bot.fetch_user()` with `bot.get_user()`; if `get_user()` returns `None`, log a warning and return `False`.
- `_handle_clone_confirmation`: replace `bot.fetch_user()` with `bot.get_user()`; if `get_user()` returns `None`, log a warning and skip the confirmation DM.

- **Files**:
  - `services/bot/events/handlers.py` — 2 call sites updated
- **Success**:
  - `uv run pytest tests/unit/services/bot/events/test_handlers.py -k "dm or clone"` passes (GREEN)
  - No remaining `bot.fetch_user` or `discord_api.fetch_user` calls in handlers.py
- **Research References**:
  - #file:../research/20260421-02-bot-rest-api-elimination-research.md (Lines 107–113) — recommended changes for user fetch
- **Dependencies**:
  - Task 3.1 complete

---

## Phase 4: guild_sync.py — Add Gateway-Aware Sync Functions

### Task 4.1: Create stubs and xfail tests for two new sync functions

Two new functions are needed to replace the REST-based `sync_all_bot_guilds` call in startup and join paths:

- `sync_guilds_from_gateway(bot, db)` — iterates `bot.guilds`, creates configs for new guilds using `guild.channels` from gateway; no REST calls.
- `sync_single_guild_from_gateway(guild, db)` — handles `on_guild_join`; creates config for one guild using `guild.channels` from gateway.

TDD: create stubs raising `NotImplementedError`, write xfail tests asserting expected behavior (no REST calls, correct DB records created), confirm tests show `xfailed`.

- **Files**:
  - `services/bot/guild_sync.py` — add two stub functions
  - `tests/unit/services/bot/test_guild_sync.py` — add xfail tests for both functions
- **Success**:
  - `uv run pytest tests/unit/services/bot/test_guild_sync.py -v` shows new tests as `xfailed`
- **Research References**:
  - #file:../research/20260421-02-bot-rest-api-elimination-research.md (Lines 38–47) — guild_sync.py analysis
  - #file:../research/20260421-02-bot-rest-api-elimination-research.md (Lines 113–117) — recommended function signatures and behavior
  - #file:../research/20260421-02-bot-rest-api-elimination-research.md (Lines 101–109) — setup_hook silent failure explanation
- **Dependencies**:
  - None

### Task 4.2: Implement `sync_guilds_from_gateway` and `sync_single_guild_from_gateway`

Implement both functions using the same pattern as `_create_guild_with_channels_and_template` but without any REST or Redis reads — use `guild.channels` directly from the gateway-supplied object.

`sync_guilds_from_gateway(bot, db)`:

- Iterate `bot.guilds`
- For each guild not already in DB, call the existing channel+config creation logic with `guild.channels`
- Shares the channel-creation path with `sync_single_guild_from_gateway`

`sync_single_guild_from_gateway(guild, db)`:

- Used by `on_guild_join` for a single gateway `discord.Guild` object
- Creates guild config and channels using `guild.channels`

Remove the `xfail` markers once both functions are implemented and tests pass.

- **Files**:
  - `services/bot/guild_sync.py` — implement both functions
  - `tests/unit/services/bot/test_guild_sync.py` — remove `xfail` markers
- **Success**:
  - `uv run pytest tests/unit/services/bot/test_guild_sync.py` passes (GREEN)
  - Neither function calls `get_guilds()`, `get_guild_channels()`, or any REST method
- **Research References**:
  - #file:../research/20260421-02-bot-rest-api-elimination-research.md (Lines 113–117) — implementation outline
  - #file:../research/20260421-02-bot-rest-api-elimination-research.md (Lines 105–112) — on_guild_join unnecessary fetch explanation
- **Dependencies**:
  - Task 4.1 complete

---

## Phase 5: bot.py — Fix Startup Sync and Remove Remaining REST Fallbacks

### Task 5.1: Fix `setup_hook` / `on_ready` guild sync

Remove the broken `sync_all_bot_guilds` call from `setup_hook`. Add a call to `sync_guilds_from_gateway(bot=self, db=db)` in `on_ready`, after `_rebuild_redis_from_gateway()` completes. This ensures guild configs are created only after gateway data is fully available.

Update any `setup_hook` tests that currently assert `sync_all_bot_guilds` is called.

- **Files**:
  - `services/bot/bot.py` — remove `sync_all_bot_guilds` from `setup_hook`; add `sync_guilds_from_gateway` call in `on_ready`
  - `tests/unit/services/bot/test_bot.py` — update assertions for `setup_hook` and `on_ready`
- **Success**:
  - `setup_hook` no longer calls any REST-based sync function
  - `on_ready` calls `sync_guilds_from_gateway` after `_rebuild_redis_from_gateway()`
  - `uv run pytest tests/unit/services/bot/test_bot.py` passes
- **Research References**:
  - #file:../research/20260421-02-bot-rest-api-elimination-research.md (Lines 29–37) — bot.py analysis including setup_hook silent failure
  - #file:../research/20260421-02-bot-rest-api-elimination-research.md (Lines 96–101) — setup_hook silent failure details
  - #file:../research/20260421-02-bot-rest-api-elimination-research.md (Lines 113–117) — recommended bot.py changes
- **Dependencies**:
  - Phase 4 complete (sync_guilds_from_gateway must exist)

### Task 5.2: Fix `on_guild_join` to use gateway-supplied guild object

Replace the `sync_all_bot_guilds(...)` call in `on_guild_join` with `sync_single_guild_from_gateway(guild=guild, db=db)`. The `guild` object already available from the event parameter contains all needed channel data.

Update `on_guild_join` tests to assert the new function is called with the event-supplied guild object.

- **Files**:
  - `services/bot/bot.py` — replace `sync_all_bot_guilds` call in `on_guild_join`
  - `tests/unit/services/bot/test_bot.py` — update `on_guild_join` test assertions
- **Success**:
  - `on_guild_join` no longer calls `get_guilds()` REST endpoint
  - `uv run pytest tests/unit/services/bot/test_bot.py -k "guild_join"` passes
- **Research References**:
  - #file:../research/20260421-02-bot-rest-api-elimination-research.md (Lines 33–36) — on_guild_join analysis
  - #file:../research/20260421-02-bot-rest-api-elimination-research.md (Lines 103–107) — on_guild_join unnecessary full fetch
- **Dependencies**:
  - Phase 4 complete; Task 5.1 complete

### Task 5.3: Remove `fetch_channel` fallback from `_run_sweep_worker`

`_run_sweep_worker` (line ~585) has a `bot.get_channel()` → `bot.fetch_channel()` REST fallback. With `on_guild_channel_create/update/delete` handlers keeping the in-memory cache current, this fallback never fires in normal operation. Remove it: if `bot.get_channel()` returns `None`, log a warning and skip that channel in the sweep.

- **Files**:
  - `services/bot/bot.py` — remove `fetch_channel` fallback in `_run_sweep_worker`
  - `tests/unit/services/bot/test_bot.py` — update sweep worker test for None-channel skip behavior
- **Success**:
  - `_run_sweep_worker` no longer calls `bot.fetch_channel()`
  - `uv run pytest tests/unit/services/bot/test_bot.py -k "sweep"` passes
- **Research References**:
  - #file:../research/20260421-02-bot-rest-api-elimination-research.md (Lines 36–38) — sweep worker fallback analysis
- **Dependencies**:
  - None (independent of Tasks 5.1–5.2)

---

## Dependencies

- `discord.Intents(members=True)` and `chunk_guilds_at_startup=True` already present in `bot.py` — no new config required
- All five target files already have unit test modules

## Success Criteria

- All modified unit test suites pass with no skips
- No `bot.fetch_member`, `bot.fetch_user`, `discord_api.fetch_user`, or `bot.fetch_channel` calls remain in `role_checker.py`, `handlers.py`, or `bot.py`
- `sync_all_bot_guilds` is no longer called from `setup_hook` or `on_guild_join`
- `sync_guilds_from_gateway` and `sync_single_guild_from_gateway` exist in `guild_sync.py` with full unit test coverage
