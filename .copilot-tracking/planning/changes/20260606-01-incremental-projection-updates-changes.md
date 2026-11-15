<!-- markdownlint-disable-file -->

# Changes: Incremental Redis Projection Updates

## Summary

Replace the 60-second debouncing coalescing worker with per-event incremental Redis writes, fix `on_resumed`/`on_guild_available`/`on_user_update` gaps, and remove the coalescing worker.

---

## Phase 1: Baseline Integration Tests for `repopulate_all`

### Added

- `tests/integration/test_guild_projection_writes.py` — baseline integration tests for `repopulate_all` covering gen pointer, member keys, user_guilds, username sorted set, and prefix search

---

## Phase 2: Incremental `on_member_update`

### Added

- `tests/unit/bot/test_guild_projection_incremental.py` — 5 unit tests for `update_member` covering: member key always written, sorted set ops skipped when names unchanged, new variants added when nick added, dropped variants removed when nick removed, pipeline always executed
- `update_member(gen, member_before, member_after, *, redis)` in `services/bot/guild_projection.py` — atomic pipeline that writes the member key and incrementally ZADDs/ZREMs only changed username variants; does not change the generation pointer
- 4 integration tests in `tests/integration/test_guild_projection_writes.py` — role change updates member key, nick change updates sorted set, no-name-change skips sorted set, atomic visibility after update

### Modified

- `services/bot/bot.py` — `on_member_update` now calls `guild_projection.update_member` directly instead of `_signal_repopulation("member_update")`
- `tests/unit/bot/test_bot_member_event_worker.py` — removed `test_on_member_update_emits_counter_and_sets_event` from `TestMemberEventHandlers` (handler no longer signals the coalescing event)

---

## Phase 3: `on_user_update` Handler

### Added

- `_user_global_variants(user)` in `services/bot/guild_projection.py` — deduped lowercase username and global_name variants for a `discord.User` (no nick, which is guild-scoped)
- `update_user(gen, user_before, user_after, bot_guilds, *, redis)` in `services/bot/guild_projection.py` — returns early if indexed variants unchanged; otherwise opens an atomic pipeline and for each guild where the user is a member, writes the member key and ZADDs/ZREMs changed variants
- `on_user_update` handler in `services/bot/bot.py` — fetches gen, returns if absent, delegates to `update_user`
- 10 unit tests in `tests/unit/bot/test_guild_projection_incremental.py` — 3 for `_user_global_variants`, 5 for `update_user`, 2 for the `on_user_update` handler
- 1 integration test in `tests/integration/test_guild_projection_writes.py` — `test_user_update_updates_all_guilds` verifies both guilds get updated member keys and sorted sets, old variant removed, gen unchanged

---

## Phase 4: Incremental `on_member_add` / `on_member_remove`

### Added

- `add_member(gen, member, *, redis)` in `services/bot/guild_projection.py` — atomic pipeline: writes member key, appends guild to user_guilds, ZADDs all username variants; does not change gen pointer
- `remove_member(gen, member, *, redis)` in `services/bot/guild_projection.py` — atomic pipeline: deletes member key, removes guild from user_guilds, ZREMs all username variants; does not change gen pointer
- 8 unit tests in `tests/unit/bot/test_guild_projection_incremental.py` for `add_member` and `remove_member` (member key written/deleted, guilds list updated, sorted set ZADDs/ZREMs correct, pipeline executed)
- 4 handler unit tests in `tests/unit/bot/test_guild_projection_incremental.py` for `on_member_add` and `on_member_remove` handlers
- 3 integration tests in `tests/integration/test_guild_projection_writes.py` — add creates member key and updates guilds, remove deletes member key and updates guilds, remove from last guild leaves empty guilds list

### Modified

- `services/bot/bot.py` — `on_member_add` and `on_member_remove` now call `add_member`/`remove_member` directly instead of `_signal_repopulation`

### Deleted

- `TestMemberEventHandlers` class from `tests/unit/bot/test_bot_member_event_worker.py` — handler no longer signals the coalescing event
- `TestSignalRepopulation` class from `tests/unit/bot/test_bot_member_event_worker.py` — `_signal_repopulation` is now dead code (removed in Phase 6)

---

## Phase 5: Fix `on_resumed` and Add `on_guild_available`

_(not yet implemented)_

---

## Phase 6: Remove Coalescing Worker

_(not yet implemented)_
