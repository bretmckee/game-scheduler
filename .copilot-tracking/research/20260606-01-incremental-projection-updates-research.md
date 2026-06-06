<!-- markdownlint-disable-file -->

# Task Research Notes: Incremental Redis Projection Updates

## Research Executed

### File Analysis

- `services/bot/bot.py`
  - `on_member_add`, `on_member_update`, `on_member_remove` all call `_signal_repopulation()`, which sets `_member_event` for the coalescing worker
  - `on_user_update` is not implemented at all — account-level name changes are only captured if Discord also fires `on_member_update` (not guaranteed)
  - `on_guild_available` is not implemented — guild outage recovery has no handler
  - `_member_event_worker` debounces 60 seconds then calls `repopulate_all`; the worker and `_member_event` can be removed entirely
  - `on_resumed` does not trigger repopulation — confirmed gap
  - `setup_hook` starts `_member_event_worker_task`; this task startup can be removed

- `services/bot/guild_projection.py`
  - `repopulate_all` writes all members via a single non-transactional pipeline, flips `proj:gen`, then deletes the old generation
  - `write_member` does a bare `set_json` + `zadd` — no transaction, no pipeline
  - `_member_username_variants(member)` returns up to 3 deduplicated lowercase variants: `name`, `global_name`, `nick`
  - `_build_member_data(member)` returns `{roles, nick, global_name, username, avatar_url}`
  - `_delete_old_generation` uses `SCAN` + pipeline `DELETE` — correct and retained

- `shared/cache/projection.py`
  - `search_members_by_prefix` uses `ZRANGEBYLEX` on `proj:usernames:{gen}:{guild}` — name-based search, not snowflake
  - All other lookups (`get_member`, `get_user_guilds`, `get_user_roles`) key on snowflake — unaffected by name changes
  - `proj:user_guilds:{gen}:{uid}` is a JSON array — requires read-modify-write for add/remove operations

- `shared/cache/operations.py`
  - `read_projection_key` retries up to `_MAX_GEN_RETRIES` on gen rotation — retained, still needed for full repopulation

- `tests/integration/conftest.py`
  - `seed_bot_freshness` fixture seeds `proj:gen = "1"` and `bot:last_seen` before each test
  - No integration test exercises `repopulate_all` or any projection write function against real Redis

### Code Search Results

- `on_user_update`
  - No matches in `services/bot/bot.py` — handler does not exist
- `on_guild_available`
  - No matches in `services/bot/bot.py` — handler does not exist
- `repopulate_all` in `tests/integration/`
  - No matches — no integration test covers the write path

### Project Conventions

- Standards referenced: `python.instructions.md`, `test-driven-development.instructions.md`, `unit-tests.instructions.md`, `integration-tests.instructions.md`
- TDD applies: Python files — RED (xfail) → GREEN → REFACTOR workflow required
- Integration tests use `scripts/run-integration-tests.sh` with `tee` output capture
- Integration tests must be written and run alongside the code they test, not deferred to a final step

## Key Discoveries

### Current Architecture — What Changes

The coalescing worker exists because every member event triggers a full `repopulate_all`, which takes ~1 CPU second (O(all members across all guilds)). The 60-second debounce amortises the cost but introduces a 60-second lag and still pays the full repopulation cost.

The core insight enabling incremental updates:

- `on_member_update` provides both `before` and `after` as complete `discord.Member` objects
- `on_user_update` provides both `before` and `after` as complete `discord.User` objects
- The diff between before/after is computable in Python without any Redis reads
- There is only one asyncio writer — no write-write race conditions exist
- Redis `MULTI`/`EXEC` provides atomic visibility for readers (see or old or new, never partial)

### Redis Data Model (unchanged)

```
proj:gen                              → current generation string (timestamp ms)
proj:member:{gen}:{guild_id}:{uid}    → JSON: {roles, nick, global_name, username, avatar_url}
proj:user_guilds:{gen}:{uid}          → JSON array of guild_id strings
proj:usernames:{gen}:{guild_id}       → sorted set: "{name_lower}\x00{uid}" entries, score=0
proj:guild_name:{gen}:{guild_id}      → guild display name string
bot:last_seen                         → ISO timestamp, TTL = heartbeat_interval * 3
```

### Generation Pointer — Retained for Full Repopulation

A Redis lock cannot replace the gen pointer because:

- Full repopulation takes ~1 CPU second
- A lock would stall all readers for that duration on every reconnect
- The gen pointer allows readers to read the old complete generation freely until the atomic pointer flip
- After the flip, readers immediately see the complete new generation
- "Lock duration" from a reader's perspective is a single `SET` command, not the full repopulation

The gen pointer is only needed for full repopulation. Incremental updates write in-place to the current gen — no new gen, no pointer flip, no cleanup needed.

### `on_member_update` — Incremental Pipeline

Covers: nick changes, role changes, per-guild avatar changes. Fires once per guild.

```python
async def on_member_update(self, before: discord.Member, after: discord.Member) -> None:
    redis = await get_redis_client()
    gen = await redis.get(CacheKeys.proj_gen())
    if gen is None:
        return  # projection not initialised yet; on_ready repopulate_all will handle it

    guild_id = str(after.guild.id)
    uid = str(after.id)
    old_variants = set(_member_username_variants(before))
    new_variants = set(_member_username_variants(after))

    async with redis._client.pipeline(transaction=True) as pipe:
        pipe.multi()
        pipe.set(CacheKeys.proj_member(gen, guild_id, uid),
                 json.dumps(_build_member_data(after)))
        if old_variants != new_variants:
            for name in new_variants - old_variants:
                pipe.zadd(CacheKeys.proj_usernames(gen, guild_id),
                          {f"{name}\x00{uid}": 0})
            for name in old_variants - new_variants:
                pipe.zrem(CacheKeys.proj_usernames(gen, guild_id),
                          f"{name}\x00{uid}")
        await pipe.execute()
```

Key properties:

- Single `MULTI`/`EXEC` — readers see either old or new state, never partial
- No gen change — in-place update to current gen
- `before` object provides old username variants without any Redis read
- Always includes the `proj:member` SET regardless of whether names changed — one code path for role-only and name+role changes
- If names did not change, pipeline contains exactly one command (SET); still atomic, negligible overhead vs bare SET

### `on_user_update` — Cross-Guild Incremental Pipeline

Covers: `username` (account handle) and `global_name` (display name) changes. Fires once globally.

```python
async def on_user_update(self, before: discord.User, after: discord.User) -> None:
    old_variants = set(_user_global_variants(before))  # name + global_name only (no nick)
    new_variants = set(_user_global_variants(after))
    if old_variants == new_variants:
        return  # only avatar or other non-indexed field changed

    redis = await get_redis_client()
    gen = await redis.get(CacheKeys.proj_gen())
    if gen is None:
        return

    uid = str(after.id)
    async with redis._client.pipeline(transaction=True) as pipe:
        pipe.multi()
        for guild in self.guilds:
            member = guild.get_member(after.id)  # O(1) in-memory lookup, no REST
            if member is None:
                continue
            guild_id = str(guild.id)
            pipe.set(CacheKeys.proj_member(gen, guild_id, uid),
                     json.dumps(_build_member_data(member)))
            for name in new_variants - old_variants:
                pipe.zadd(CacheKeys.proj_usernames(gen, guild_id),
                          {f"{name}\x00{uid}": 0})
            for name in old_variants - new_variants:
                pipe.zrem(CacheKeys.proj_usernames(gen, guild_id),
                          f"{name}\x00{uid}")
        await pipe.execute()
```

Note: A helper `_user_global_variants(user: discord.User)` is needed — mirrors `_member_username_variants` but takes a `User` and excludes `nick` (which is guild-scoped and not present on `User`).

One pipeline across all guilds. `guild.get_member()` is O(1) in-memory. For N guilds the cost is N SET + up to 2\*V ZADD/ZREM commands in one round-trip, vs a full repopulation of all members in all guilds.

### `on_member_add` — Incremental with Read-Modify-Write

```python
async def on_member_add(self, member: discord.Member) -> None:
    redis = await get_redis_client()
    gen = await redis.get(CacheKeys.proj_gen())
    if gen is None:
        return

    guild_id = str(member.guild.id)
    uid = str(member.id)

    # Read-modify-write on user_guilds — safe: single asyncio writer, no concurrent writers
    raw = await redis.get(CacheKeys.proj_user_guilds(gen, uid))
    current_guilds = json.loads(raw) if raw else []
    if guild_id not in current_guilds:
        current_guilds.append(guild_id)

    async with redis._client.pipeline(transaction=True) as pipe:
        pipe.multi()
        pipe.set(CacheKeys.proj_member(gen, guild_id, uid),
                 json.dumps(_build_member_data(member)))
        pipe.set(CacheKeys.proj_user_guilds(gen, uid),
                 json.dumps(current_guilds))
        for name in _member_username_variants(member):
            pipe.zadd(CacheKeys.proj_usernames(gen, guild_id),
                      {f"{name}\x00{uid}": 0})
        await pipe.execute()
```

### `on_member_remove` — Incremental with Read-Modify-Write

The `member` object is available in the event, providing username variants without any Redis read.

```python
async def on_member_remove(self, member: discord.Member) -> None:
    redis = await get_redis_client()
    gen = await redis.get(CacheKeys.proj_gen())
    if gen is None:
        return

    guild_id = str(member.guild.id)
    uid = str(member.id)

    raw = await redis.get(CacheKeys.proj_user_guilds(gen, uid))
    current_guilds = json.loads(raw) if raw else []
    updated_guilds = [g for g in current_guilds if g != guild_id]

    async with redis._client.pipeline(transaction=True) as pipe:
        pipe.multi()
        pipe.delete(CacheKeys.proj_member(gen, guild_id, uid))
        pipe.set(CacheKeys.proj_user_guilds(gen, uid),
                 json.dumps(updated_guilds))
        for name in _member_username_variants(member):
            pipe.zrem(CacheKeys.proj_usernames(gen, guild_id),
                      f"{name}\x00{uid}")
        await pipe.execute()
```

### Events That Still Trigger Full Repopulation

| Event                | Reason                                                                                  |
| -------------------- | --------------------------------------------------------------------------------------- |
| `on_ready`           | Initial population; always correct                                                      |
| `on_resumed`         | Gateway session resumed; currently does NOT trigger repopulation — this is a gap to fix |
| `on_guild_join`      | New guild; could be incremental but rare, full repop is correct and simple              |
| `on_guild_remove`    | Removing a whole guild's keys is complex; full repop is simpler                         |
| `on_guild_available` | Guild recovered from Discord outage; member cache may have drifted                      |

`on_resumed` currently only calls `_recover_pending_workers`, `_trigger_sweep`, and `_sweep_orphaned_embeds` — it does not call `repopulate_all` or `_rebuild_redis_from_gateway`. This is a confirmed gap that should be fixed as part of this work.

### Coalescing Worker — Removed

`_member_event`, `_member_event_worker`, and the `_member_event_worker_task` startup in `setup_hook` are all removed. Each event handles itself immediately and directly.

### `gen is None` Early-Return Decision

If `proj:gen` is absent when an incremental event fires (bot still initializing), return early without writing. The subsequent `repopulate_all` in `on_ready` will write the full correct state. This is an explicit design choice: partial writes to a non-existent generation are silently dropped, not an error.

## Integration Test Plan

Integration tests must be written and run **alongside** the code change they cover, not deferred to a final testing step. Each task below includes its own integration test.

### New Integration Test File: `tests/integration/test_guild_projection_writes.py`

Tests call projection write functions directly against a real Redis instance (provided by the integration test Docker environment). The `seed_bot_freshness` autouse fixture already seeds `proj:gen = "1"` and flushes Redis between tests.

**Task 1 tests (write alongside Task 1 implementation):**

- `test_repopulate_all_sets_gen_pointer` — call `repopulate_all` with a mock bot (2 guilds, 3 members each), assert `proj:gen` is set to a new value
- `test_repopulate_all_writes_member_keys` — assert `proj:member:{gen}:{guild}:{uid}` exists for each member with correct JSON fields
- `test_repopulate_all_writes_user_guilds` — assert `proj:user_guilds:{gen}:{uid}` contains correct guild list for a member present in both guilds
- `test_repopulate_all_writes_username_sorted_set` — assert `proj:usernames:{gen}:{guild}` contains entries for each name variant
- `test_repopulate_all_search_returns_member` — call `search_members_by_prefix` after repopulate, verify it returns the correct member

**Task 2 tests (write alongside Task 2 implementation — `on_member_update`):**

- `test_member_update_role_change_updates_member_key` — seed a member, call the new incremental update with changed roles, assert `proj:member` reflects new roles, gen unchanged
- `test_member_update_nick_change_updates_sorted_set` — seed a member with old nick, update with new nick, assert new nick variant in sorted set, old nick variant removed, gen unchanged
- `test_member_update_no_name_change_skips_sorted_set` — role-only change, assert sorted set is not touched (same entries)
- `test_member_update_atomic_visibility` — verify `proj:member` and `proj:usernames` are updated together (read both before and after, no intermediate state observable)

**Task 3 tests (write alongside Task 3 implementation — `on_user_update`):**

- `test_user_update_updates_all_guilds` — seed user in two guilds, call `on_user_update` with new global name, assert both `proj:member` keys updated and both `proj:usernames` sorted sets reflect new variant, old variant removed

**Task 4 tests (write alongside Task 4 implementation — `on_member_add`/`on_member_remove`):**

- `test_member_add_creates_member_key_and_updates_guilds` — assert `proj:member` created, `proj:user_guilds` updated to include new guild, username variants in sorted set
- `test_member_remove_deletes_member_key_and_updates_guilds` — assert `proj:member` deleted, `proj:user_guilds` updated to exclude guild, username variants removed from sorted set
- `test_member_remove_last_guild_leaves_empty_guilds_list` — user removed from their only guild; `proj:user_guilds` becomes `[]`, member key deleted

### Existing Tests — No Removal Needed

Integration tests in `test_rls_enforcement.py`, `test_games_field_display.py`, etc. that manually seed `proj:member` keys are testing the API read path and RLS behavior — correct layer, should stay.

Unit tests in `test_bot_member_event_worker.py` become obsolete once the coalescing worker is removed. Delete them as part of that task.

## Recommended Approach

Incremental in-place Redis writes using `MULTI`/`EXEC` transactional pipelines, keyed on the current gen without changing the gen pointer. Full repopulation retained only for connect/reconnect events.

## Implementation Guidance

- **Objectives**: Eliminate O(all members) repopulation cost for individual member events; fix `on_user_update` gap; fix `on_resumed` gap; fix `on_guild_available` gap; remove coalescing worker
- **Key Tasks**:
  1. Add integration tests for `repopulate_all` (baseline) — write and run before changing any event handler code
  2. Implement incremental `on_member_update` with transactional pipeline; write and run its integration tests
  3. Implement `on_user_update` handler with cross-guild transactional pipeline; write and run its integration tests
  4. Implement incremental `on_member_add` / `on_member_remove`; write and run their integration tests
  5. Add `on_guild_available` handler calling `repopulate_all`
  6. Fix `on_resumed` to call `repopulate_all` and `_rebuild_redis_from_gateway`
  7. Remove `_member_event`, `_member_event_worker`, `_member_event_worker_task` startup, and obsolete unit tests
- **Dependencies**: All tasks depend on Task 1 (baseline integration tests) completing first, to confirm `repopulate_all` is correct before building on top of it
- **Success Criteria**:
  - `on_member_update` no longer triggers `repopulate_all`
  - `on_member_add` / `on_member_remove` no longer trigger `repopulate_all`
  - `on_user_update` is handled incrementally
  - `on_resumed` and `on_guild_available` trigger `repopulate_all`
  - All new integration tests pass
  - No existing integration tests regress
