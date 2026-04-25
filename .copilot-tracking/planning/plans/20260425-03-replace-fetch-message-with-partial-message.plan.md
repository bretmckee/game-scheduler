---
applyTo: '.copilot-tracking/changes/20260425-03-replace-fetch-message-with-partial-message-changes.md'
---

<!-- markdownlint-disable-file -->

# Task Checklist: Replace fetch_message REST Calls with PartialMessage

## Overview

Eliminate three `channel.fetch_message()` REST GET calls in `handlers.py` that exist solely to obtain an object for `.edit()` or `.delete()` by replacing them with the synchronous `channel.get_partial_message()`.

## Objectives

- Remove `_fetch_message_for_refresh()` and inline `get_partial_message` in `_refresh_game_message()`
- Rename `_fetch_channel_and_message()` to `_get_channel_and_partial_message()`, make it synchronous, and eliminate the internal `fetch_message` call
- Inline `get_partial_message` in `_archive_game_announcement()`
- Update all callers and all affected unit tests

## Research Summary

### Project Files

- `services/bot/events/handlers.py` (lines 337–400) — `_fetch_message_for_refresh` and `_fetch_channel_and_message` definitions
- `services/bot/events/handlers.py` (lines 401–425) — `_refresh_game_message` caller
- `services/bot/events/handlers.py` (lines 957–990) — `_update_message_for_player_removal` caller
- `services/bot/events/handlers.py` (lines 1090–1115) — `_handle_game_cancelled` caller
- `services/bot/events/handlers.py` (lines 1275–1307) — `_archive_game_announcement` with inline `fetch_message`
- `services/bot/events/handlers.py` (lines 1460–1480) — `_try_edit_game_message` caller
- `tests/unit/services/bot/events/test_handlers.py` (lines 633–702) — archive announcement tests using `fetch_message`
- `tests/unit/services/bot/events/test_handlers.py` (lines 1572–1645) — player removal tests using `fetch_message`
- `tests/unit/services/bot/events/test_handlers.py` (lines 2284–2393) — direct unit tests for the two methods being removed/changed
- `tests/unit/services/bot/events/test_handlers.py` (lines 2415–2460) — `_refresh_game_message` tests patching `_fetch_message_for_refresh`

### External References

- #file:../research/20260425-03-replace-fetch-message-with-partial-message-research.md — full research findings with before/after code examples

### Standards References

- #file:../../.github/instructions/python.instructions.md — Python conventions
- #file:../../.github/instructions/test-driven-development.instructions.md — TDD workflow

## Implementation Checklist

### [ ] Phase 1: RED — Add xfail tests for `_get_channel_and_partial_message`

- [ ] Task 1.1: Write three `xfail` tests for the new `_get_channel_and_partial_message` method (success, channel not in cache, wrong channel type)
  - Details: .copilot-tracking/planning/details/20260425-03-replace-fetch-message-with-partial-message-details.md (Lines 11–29)

### [ ] Phase 2: GREEN — Implement refactoring and update all tests

- [ ] Task 2.1: Rename `_fetch_channel_and_message` to `_get_channel_and_partial_message`, make synchronous, replace `fetch_message` with `get_partial_message`
  - Details: .copilot-tracking/planning/details/20260425-03-replace-fetch-message-with-partial-message-details.md (Lines 33–56)

- [ ] Task 2.2: Delete `_fetch_message_for_refresh`, inline `channel.get_partial_message` in `_refresh_game_message`
  - Details: .copilot-tracking/planning/details/20260425-03-replace-fetch-message-with-partial-message-details.md (Lines 57–87)

- [ ] Task 2.3: Update `_archive_game_announcement` to use `get_partial_message` inline
  - Details: .copilot-tracking/planning/details/20260425-03-replace-fetch-message-with-partial-message-details.md (Lines 88–115)

- [ ] Task 2.4: Update the three `_fetch_channel_and_message` call sites to `_get_channel_and_partial_message` without `await`
  - Details: .copilot-tracking/planning/details/20260425-03-replace-fetch-message-with-partial-message-details.md (Lines 116–133)

- [ ] Task 2.5: Remove xfail markers; delete and update all obsolete tests
  - Details: .copilot-tracking/planning/details/20260425-03-replace-fetch-message-with-partial-message-details.md (Lines 134–175)

## Dependencies

- discord.py 2.6.4 (already installed; `TextChannel.get_partial_message` is available — no package changes)

## Success Criteria

- Zero `channel.fetch_message` calls in `services/bot/events/handlers.py` outside the sweep loop in `bot.py`
- All unit tests pass with no failures or unexpected xfails
- `_get_channel_and_partial_message` is `def` (synchronous), returns `tuple[discord.TextChannel, discord.PartialMessage] | None`
- No caller of `_get_channel_and_partial_message` uses `await`
