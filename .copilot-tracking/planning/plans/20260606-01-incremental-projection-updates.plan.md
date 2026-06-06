---
applyTo: '.copilot-tracking/changes/20260606-01-incremental-projection-updates-changes.md'
---

<!-- markdownlint-disable-file -->

# Task Checklist: Incremental Redis Projection Updates

## Overview

Replace the 60-second debouncing coalescing worker with per-event incremental Redis writes using `MULTI`/`EXEC` transactional pipelines, and fix the `on_resumed`, `on_guild_available`, and `on_user_update` gaps.

## Objectives

- Eliminate O(all members) repopulation cost for individual member events
- Fix `on_user_update` gap (handler does not exist)
- Fix `on_resumed` gap (does not call `repopulate_all`)
- Fix `on_guild_available` gap (handler does not exist)
- Remove the coalescing worker (`_member_event_worker`, `_member_event`, `_signal_repopulation`)

## Research Summary

### Project Files

- `services/bot/guild_projection.py` — `repopulate_all`, `_member_username_variants`, `_build_member_data`, `write_member`
- `services/bot/bot.py` — `on_member_add`, `on_member_update`, `on_member_remove`, `on_resumed`, `_member_event_worker`, `_signal_repopulation`
- `shared/cache/projection.py` — `search_members_by_prefix`, `get_member`, `get_user_guilds`
- `tests/integration/conftest.py` — `seed_bot_freshness` autouse fixture (seeds `proj:gen = "1"`, flushes Redis)
- `tests/unit/bot/test_bot_member_event_worker.py` — tests for the coalescing worker and handler signalling

### Research References

- #file:../research/20260606-01-incremental-projection-updates-research.md — full design, code examples, and integration test plan

## Implementation Checklist

### [x] Phase 1: Baseline Integration Tests for `repopulate_all`

- [x] Task 1.1: Create baseline integration tests in `tests/integration/test_guild_projection_writes.py`
  - Details: `.copilot-tracking/planning/details/20260606-01-incremental-projection-updates-details.md` (Lines 13-33)

### [x] Phase 2: Incremental `on_member_update`

- [x] Task 2.1: Add `update_member` function to `guild_projection.py` (TDD red→green)
  - Details: `.copilot-tracking/planning/details/20260606-01-incremental-projection-updates-details.md` (Lines 37-57)

- [x] Task 2.2: Update `on_member_update` in `bot.py` to call `update_member`
  - Details: `.copilot-tracking/planning/details/20260606-01-incremental-projection-updates-details.md` (Lines 59-72)

- [x] Task 2.3: Delete `on_member_update` test from `TestMemberEventHandlers` in `test_bot_member_event_worker.py`
  - Details: `.copilot-tracking/planning/details/20260606-01-incremental-projection-updates-details.md` (Lines 74-79)

- [x] Task 2.4: Add integration tests for `update_member`
  - Details: `.copilot-tracking/planning/details/20260606-01-incremental-projection-updates-details.md` (Lines 81-97)

### [x] Phase 3: `on_user_update` Handler

- [x] Task 3.1: Add `_user_global_variants` and `update_user` to `guild_projection.py` (TDD red→green)
  - Details: `.copilot-tracking/planning/details/20260606-01-incremental-projection-updates-details.md` (Lines 101-124)

- [x] Task 3.2: Add `on_user_update` handler to `bot.py`
  - Details: `.copilot-tracking/planning/details/20260606-01-incremental-projection-updates-details.md` (Lines 126-138)

- [x] Task 3.3: Add integration tests for `update_user`
  - Details: `.copilot-tracking/planning/details/20260606-01-incremental-projection-updates-details.md` (Lines 140-154)

### [x] Phase 4: Incremental `on_member_add` / `on_member_remove`

- [x] Task 4.1: Add `add_member` and `remove_member` to `guild_projection.py` (TDD red→green)
  - Details: `.copilot-tracking/planning/details/20260606-01-incremental-projection-updates-details.md` (Lines 158-183)

- [x] Task 4.2: Update `on_member_add` and `on_member_remove` in `bot.py`
  - Details: `.copilot-tracking/planning/details/20260606-01-incremental-projection-updates-details.md` (Lines 185-205)

- [x] Task 4.3: Delete `TestMemberEventHandlers` and `TestSignalRepopulation` classes from `test_bot_member_event_worker.py`
  - Details: `.copilot-tracking/planning/details/20260606-01-incremental-projection-updates-details.md` (Lines 207-212)

- [x] Task 4.4: Add integration tests for `add_member` and `remove_member`
  - Details: `.copilot-tracking/planning/details/20260606-01-incremental-projection-updates-details.md` (Lines 214-230)

### [x] Phase 5: Fix `on_resumed` and Add `on_guild_available`

- [x] Task 5.1: Fix `on_resumed` to call `repopulate_all` (TDD red→green)
  - Details: `.copilot-tracking/planning/details/20260606-01-incremental-projection-updates-details.md` (Lines 234-246)

- [x] Task 5.2: Add `on_guild_available` handler (TDD red→green)
  - Details: `.copilot-tracking/planning/details/20260606-01-incremental-projection-updates-details.md` (Lines 248-271)

### [ ] Phase 6: Remove Coalescing Worker

- [ ] Task 6.1: Remove `_member_event_worker`, `_member_event`, `_signal_repopulation`, and `repopulation_coalesced_counter`
  - Details: `.copilot-tracking/planning/details/20260606-01-incremental-projection-updates-details.md` (Lines 275-293)

- [ ] Task 6.2: Delete `tests/unit/bot/test_bot_member_event_worker.py`
  - Details: `.copilot-tracking/planning/details/20260606-01-incremental-projection-updates-details.md` (Lines 295-308)

## Dependencies

- `asyncio` event loop (Discord bot is single-threaded asyncio writer — no write-write races)
- `redis.asyncio` pipeline with `transaction=True` for `MULTI`/`EXEC` atomicity
- Integration test Docker environment (Redis)
- `seed_bot_freshness` autouse fixture in `tests/integration/conftest.py`

## Success Criteria

- `on_member_update`, `on_member_add`, `on_member_remove` each perform an incremental write instead of calling `_signal_repopulation`
- `on_user_update` handler exists and updates all guilds in a single transactional pipeline
- `on_resumed` and `on_guild_available` trigger `repopulate_all`
- `_member_event_worker`, `_member_event`, `_signal_repopulation` are absent from the codebase
- `test_bot_member_event_worker.py` is deleted
- All integration tests in `test_guild_projection_writes.py` pass
- No existing integration tests regress
