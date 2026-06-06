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

_(not yet implemented)_

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
