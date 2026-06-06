<!-- markdownlint-disable-file -->

# Task Details: Incremental Redis Projection Updates

## Research Reference

**Source Research**: #file:../research/20260606-01-incremental-projection-updates-research.md

---

## Phase 1: Baseline Integration Tests for `repopulate_all`

### Task 1.1: Create `tests/integration/test_guild_projection_writes.py` with baseline tests

`repopulate_all` is already implemented. These tests confirm its correct behaviour before any code changes, providing a safety net for subsequent phases.

Do **not** apply TDD xfail cycle here — this is testing already-implemented code.

- **Files**:
  - `tests/integration/test_guild_projection_writes.py` (create)
- **Tests to write** (all should pass immediately against existing production code):
  - `test_repopulate_all_sets_gen_pointer` — call `repopulate_all` with a mock bot (2 guilds, 3 members each); assert `proj:gen` is set to a non-empty string
  - `test_repopulate_all_writes_member_keys` — assert `proj:member:{gen}:{guild}:{uid}` exists for each member, with JSON containing `roles`, `nick`, `global_name`, `username`, `avatar_url`
  - `test_repopulate_all_writes_user_guilds` — for a member present in both guilds, assert `proj:user_guilds:{gen}:{uid}` contains both guild IDs
  - `test_repopulate_all_writes_username_sorted_set` — assert `proj:usernames:{gen}:{guild}` contains entries for each non-empty name variant
  - `test_repopulate_all_search_returns_member` — call `search_members_by_prefix` after `repopulate_all`, verify the member is returned
- **Research References**:
  - #file:../research/20260606-01-incremental-projection-updates-research.md (Lines 238-252) — integration test list for Task 1
- **Success**:
  - All 5 tests pass with `scripts/run-integration-tests.sh tests/integration/test_guild_projection_writes.py`
  - No existing integration tests regress

---

## Phase 2: Incremental `on_member_update`

### Task 2.1: Add `update_member` to `guild_projection.py` (TDD)

New async function: `update_member(gen: str, member_before: discord.Member, member_after: discord.Member, *, redis: RedisClient) -> None`

Logic (from research):

- Compute `old_variants = set(_member_username_variants(before))`, `new_variants = set(_member_username_variants(after))`
- Open `redis._client.pipeline(transaction=True)`, call `pipe.multi()`
- Always `pipe.set(CacheKeys.proj_member(gen, guild_id, uid), json.dumps(_build_member_data(after)))`
- If `old_variants != new_variants`: ZADD new variants, ZREM dropped variants on `proj:usernames:{gen}:{guild_id}`
- `await pipe.execute()`
- No gen change; writes in-place to current gen

TDD cycle:

- RED: Write unit tests in `tests/unit/bot/test_guild_projection_incremental.py` for `update_member`, marked `@pytest.mark.xfail(strict=True, reason="not yet implemented")`. Run `uv run pytest tests/unit` to confirm red.
- GREEN: Implement `update_member` in `guild_projection.py`. Remove xfail markers. Confirm tests pass.

- **Files**:
  - `tests/unit/bot/test_guild_projection_incremental.py` (create)
  - `services/bot/guild_projection.py` (add `update_member`)
- **Research References**:
  - #file:../research/20260606-01-incremental-projection-updates-research.md (Lines 90-120) — `on_member_update` incremental pipeline design

### Task 2.2: Update `on_member_update` in `bot.py`

Replace `self._signal_repopulation("member_update")` with an incremental call:

```python
async def on_member_update(self, before: discord.Member, after: discord.Member) -> None:
    redis = await get_redis_client()
    gen = await redis.get(CacheKeys.proj_gen())
    if gen is None:
        return
    await guild_projection.update_member(gen, before, after, redis=redis)
```

- **Files**:
  - `services/bot/bot.py` (update `on_member_update`, lines ~455-458)

### Task 2.3: Delete `on_member_update` handler test from `TestMemberEventHandlers`

`TestMemberEventHandlers` in `tests/unit/bot/test_bot_member_event_worker.py` tests that `on_member_update` sets `bot._member_event`. After this phase, `on_member_update` no longer sets that event. Delete the specific test method for `on_member_update` within that class; leave the `on_member_add` and `on_member_remove` test methods intact (they change in Phase 4).

- **Files**:
  - `tests/unit/bot/test_bot_member_event_worker.py` (remove `on_member_update` test method from `TestMemberEventHandlers`)

### Task 2.4: Add integration tests for `update_member`

Add to `tests/integration/test_guild_projection_writes.py`:

- `test_member_update_role_change_updates_member_key` — seed a member via `repopulate_all`; call `update_member` with changed roles; assert `proj:member` reflects new roles, gen is unchanged
- `test_member_update_nick_change_updates_sorted_set` — seed a member with old nick; update with new nick; assert new nick variant in sorted set, old nick variant removed, gen unchanged
- `test_member_update_no_name_change_skips_sorted_set` — role-only change; assert sorted set entries are identical before and after
- `test_member_update_atomic_visibility` — read both `proj:member` and `proj:usernames` after update; verify self-consistent state (can only verify final state, not intermediate, from a test)

- **Files**:
  - `tests/integration/test_guild_projection_writes.py` (add 4 tests)
- **Research References**:
  - #file:../research/20260606-01-incremental-projection-updates-research.md (Lines 254-261) — integration test list for Task 2
- **Success**:
  - All unit tests pass: `uv run pytest tests/unit`
  - All integration tests pass: `scripts/run-integration-tests.sh tests/integration/test_guild_projection_writes.py`

---

## Phase 3: `on_user_update` Handler

### Task 3.1: Add `_user_global_variants` and `update_user` to `guild_projection.py` (TDD)

New private helper: `_user_global_variants(user: discord.User) -> list[str]`

- Mirrors `_member_username_variants` but takes a `discord.User`
- Includes `user.name` and `user.global_name`; excludes `nick` (guild-scoped, not on `User`)
- Same deduplication logic as `_member_username_variants`

New async function: `update_user(gen: str, user_before: discord.User, user_after: discord.User, bot_guilds: Iterable[discord.Guild], *, redis: RedisClient) -> None`

Logic (from research):

- `old_variants = set(_user_global_variants(user_before))`, `new_variants = set(_user_global_variants(user_after))`
- If `old_variants == new_variants`: return early (non-indexed field changed, e.g. avatar)
- Open `redis._client.pipeline(transaction=True)`, call `pipe.multi()`
- For each guild in `bot_guilds`: call `guild.get_member(user_after.id)` (O(1) in-memory); skip if `None`
- Per guild: `pipe.set(proj_member key, json.dumps(_build_member_data(member)))`, ZADD new variants, ZREM dropped variants
- `await pipe.execute()`

TDD cycle:

- RED: Add unit tests for `_user_global_variants` and `update_user` in `tests/unit/bot/test_guild_projection_incremental.py`, marked xfail. Confirm red.
- GREEN: Implement. Remove xfail markers. Confirm green.

- **Files**:
  - `tests/unit/bot/test_guild_projection_incremental.py` (add tests)
  - `services/bot/guild_projection.py` (add `_user_global_variants`, `update_user`)

### Task 3.2: Add `on_user_update` handler to `bot.py`

```python
async def on_user_update(self, before: discord.User, after: discord.User) -> None:
    redis = await get_redis_client()
    gen = await redis.get(CacheKeys.proj_gen())
    if gen is None:
        return
    await guild_projection.update_user(gen, before, after, self.guilds, redis=redis)
```

- **Files**:
  - `services/bot/bot.py` (add `on_user_update` near the other member event handlers, ~line 463)

### Task 3.3: Add integration tests for `update_user`

Add to `tests/integration/test_guild_projection_writes.py`:

- `test_user_update_updates_all_guilds` — seed user in two guilds via `repopulate_all`; call `update_user` with new `global_name`; assert both `proj:member` keys updated (new `global_name`), both `proj:usernames` sorted sets contain new variant and not old variant, gen unchanged

- **Files**:
  - `tests/integration/test_guild_projection_writes.py` (add 1 test)
- **Research References**:
  - #file:../research/20260606-01-incremental-projection-updates-research.md (Lines 119-149) — `on_user_update` cross-guild pipeline design
  - #file:../research/20260606-01-incremental-projection-updates-research.md (Lines 263-265) — integration test for Task 3
- **Success**:
  - All unit tests pass: `uv run pytest tests/unit`
  - All integration tests pass: `scripts/run-integration-tests.sh tests/integration/test_guild_projection_writes.py`

---

## Phase 4: Incremental `on_member_add` / `on_member_remove`

### Task 4.1: Add `add_member` and `remove_member` to `guild_projection.py` (TDD)

New async function: `add_member(gen: str, member: discord.Member, *, redis: RedisClient) -> None`

Logic (from research):

- Read `raw = await redis.get(CacheKeys.proj_user_guilds(gen, uid))`; `current_guilds = json.loads(raw) if raw else []`
- Append `guild_id` if not already present
- Open `redis._client.pipeline(transaction=True)`, call `pipe.multi()`
- `pipe.set(proj_member key, ...)`, `pipe.set(proj_user_guilds key, json.dumps(current_guilds))`, ZADD all username variants
- `await pipe.execute()`

New async function: `remove_member(gen: str, member: discord.Member, *, redis: RedisClient) -> None`

Logic (from research):

- Read `raw`, compute `updated_guilds = [g for g in current_guilds if g != guild_id]`
- Open transactional pipeline
- `pipe.delete(proj_member key)`, `pipe.set(proj_user_guilds key, json.dumps(updated_guilds))`, ZREM all username variants
- `await pipe.execute()`

TDD cycle:

- RED: Add unit tests in `tests/unit/bot/test_guild_projection_incremental.py`, marked xfail. Confirm red.
- GREEN: Implement. Remove xfail markers. Confirm green.

- **Files**:
  - `tests/unit/bot/test_guild_projection_incremental.py` (add tests)
  - `services/bot/guild_projection.py` (add `add_member`, `remove_member`)

### Task 4.2: Update `on_member_add` and `on_member_remove` in `bot.py`

Replace `self._signal_repopulation(...)` calls with incremental calls:

```python
async def on_member_add(self, member: discord.Member) -> None:
    redis = await get_redis_client()
    gen = await redis.get(CacheKeys.proj_gen())
    if gen is None:
        return
    await guild_projection.add_member(gen, member, redis=redis)

async def on_member_remove(self, member: discord.Member) -> None:
    redis = await get_redis_client()
    gen = await redis.get(CacheKeys.proj_gen())
    if gen is None:
        return
    await guild_projection.remove_member(gen, member, redis=redis)
```

- **Files**:
  - `services/bot/bot.py` (update `on_member_add` ~line 451, `on_member_remove` ~line 459)

### Task 4.3: Delete remaining `TestMemberEventHandlers` tests

`TestMemberEventHandlers` in `tests/unit/bot/test_bot_member_event_worker.py` (class at line 208) now has no valid test cases — its remaining methods test that `on_member_add` and `on_member_remove` set `bot._member_event`, which is no longer true. Delete the entire `TestMemberEventHandlers` class and the `TestSignalRepopulation` class (tests `_signal_repopulation`, which is now dead code).

- **Files**:
  - `tests/unit/bot/test_bot_member_event_worker.py` (delete `TestMemberEventHandlers` class and `TestSignalRepopulation` class)

### Task 4.4: Add integration tests for `add_member` and `remove_member`

Add to `tests/integration/test_guild_projection_writes.py`:

- `test_member_add_creates_member_key_and_updates_guilds` — assert `proj:member` created, `proj:user_guilds` updated to include new guild, username variants in sorted set, gen unchanged
- `test_member_remove_deletes_member_key_and_updates_guilds` — assert `proj:member` deleted, `proj:user_guilds` updated to exclude guild, username variants removed from sorted set, gen unchanged
- `test_member_remove_last_guild_leaves_empty_guilds_list` — user removed from their only guild; `proj:user_guilds` becomes `[]`, member key deleted

- **Files**:
  - `tests/integration/test_guild_projection_writes.py` (add 3 tests)
- **Research References**:
  - #file:../research/20260606-01-incremental-projection-updates-research.md (Lines 151-195) — `on_member_add`/`on_member_remove` design
  - #file:../research/20260606-01-incremental-projection-updates-research.md (Lines 267-272) — integration test list for Task 4
- **Success**:
  - All unit tests pass: `uv run pytest tests/unit`
  - All integration tests pass: `scripts/run-integration-tests.sh tests/integration/test_guild_projection_writes.py`

---

## Phase 5: Fix `on_resumed` and Add `on_guild_available`

### Task 5.1: Fix `on_resumed` to call `repopulate_all` (TDD)

`on_resumed` (bot.py ~line 429) currently calls `_recover_pending_workers`, `_trigger_sweep`, and `_sweep_orphaned_embeds` but does NOT call `repopulate_all`. This is a confirmed gap.

Add `await guild_projection.repopulate_all(bot=self, redis=redis)` to `on_resumed` after the existing calls. Also add `await self._rebuild_redis_from_gateway()` if that is the correct pattern from the codebase (check how `on_ready` calls it).

TDD cycle:

- RED: Write unit test in `tests/unit/bot/test_bot_reconnect_repopulation.py`: `test_on_resumed_triggers_repopulate_all` — mock `guild_projection.repopulate_all`; call `bot.on_resumed()`; assert mock called once. Mark xfail. Confirm red.
- GREEN: Implement. Remove xfail. Confirm green.

- **Files**:
  - `tests/unit/bot/test_bot_reconnect_repopulation.py` (create)
  - `services/bot/bot.py` (update `on_resumed`, ~line 429)

### Task 5.2: Add `on_guild_available` handler (TDD)

`on_guild_available` is not currently implemented. This event fires when a guild recovers from a Discord outage. Add:

```python
async def on_guild_available(self, guild: discord.Guild) -> None:
    """Handle guild becoming available after a Discord outage."""
    logger.info("Guild available: %s", guild.id)
    redis = await get_redis_client()
    await guild_projection.repopulate_all(bot=self, redis=redis)
```

TDD cycle:

- RED: Add unit test `test_on_guild_available_triggers_repopulate_all` in `tests/unit/bot/test_bot_reconnect_repopulation.py`, xfail. Confirm red.
- GREEN: Implement. Remove xfail. Confirm green.

- **Files**:
  - `tests/unit/bot/test_bot_reconnect_repopulation.py` (add test)
  - `services/bot/bot.py` (add `on_guild_available` near `on_resumed`)
- **Research References**:
  - #file:../research/20260606-01-incremental-projection-updates-research.md (Lines 196-213) — events that still trigger full repopulation
- **Success**:
  - All unit tests pass: `uv run pytest tests/unit`

---

## Phase 6: Remove Coalescing Worker

### Task 6.1: Remove `_member_event_worker`, `_member_event`, `_signal_repopulation`, and `repopulation_coalesced_counter`

By this phase:

- `_signal_repopulation` is never called (all event handlers use incremental writes or call `repopulate_all` directly)
- `_member_event_worker` never fires (no one sets `_member_event`)
- `repopulation_coalesced_counter` is only used inside `_signal_repopulation`

Remove from `services/bot/bot.py`:

- `self._member_event = asyncio.Event()` (bot `__init__`, ~line 121)
- `_member_event_worker_task` startup in `setup_hook` (~lines 171-172)
- `_signal_repopulation` method (~lines 436-449)
- `_member_event_worker` method (~lines 860-876)

Remove from `services/bot/guild_projection.py`:

- `repopulation_coalesced_counter` metric definition (after confirming it is only referenced by `_signal_repopulation`)

- **Files**:
  - `services/bot/bot.py`
  - `services/bot/guild_projection.py`

### Task 6.2: Delete `tests/unit/bot/test_bot_member_event_worker.py`

The remaining test classes (`TestMemberEventWorkerCoalescing`, `TestMemberEventWorkerDebounce`, `TestOnReadyUnaffected`) all test the removed `_member_event_worker` and its coalescing behaviour. Delete the entire file.

- **Files**:
  - `tests/unit/bot/test_bot_member_event_worker.py` (delete)
- **Success**:
  - All unit tests pass: `uv run pytest tests/unit`
  - No import errors or references to removed symbols

---

## Dependencies

- All phases require Redis available (provided by integration test Docker environment)
- Phase 2 depends on Phase 1 (baseline integration tests must confirm `repopulate_all` is correct)
- Phases 3 and 4 depend on Phase 2 (`update_member` establishes the transactional pipeline pattern)
- Phase 5 is independent of Phases 2-4 (adds repopulation calls; no interaction with incremental functions)
- Phase 6 depends on Phases 2, 3, 4 (all callers of `_signal_repopulation` must be migrated before removal)

## Success Criteria

- `on_member_update` calls `guild_projection.update_member` instead of `_signal_repopulation`
- `on_member_add` calls `guild_projection.add_member` instead of `_signal_repopulation`
- `on_member_remove` calls `guild_projection.remove_member` instead of `_signal_repopulation`
- `on_user_update` handler exists and calls `guild_projection.update_user`
- `on_resumed` calls `guild_projection.repopulate_all`
- `on_guild_available` handler exists and calls `guild_projection.repopulate_all`
- `_member_event_worker`, `_member_event`, `_signal_repopulation` are removed
- `test_bot_member_event_worker.py` is deleted
- All new integration tests in `test_guild_projection_writes.py` pass
- No existing integration tests regress
