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

_(not yet implemented)_

---

## Phase 4: Incremental `on_member_add` / `on_member_remove`

_(not yet implemented)_

---

## Phase 5: Fix `on_resumed` and Add `on_guild_available`

_(not yet implemented)_

---

## Phase 6: Remove Coalescing Worker

_(not yet implemented)_
