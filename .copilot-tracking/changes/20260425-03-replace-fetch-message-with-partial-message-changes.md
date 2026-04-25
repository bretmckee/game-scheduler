---
applyTo: '.copilot-tracking/changes/20260425-03-replace-fetch-message-with-partial-message-changes.md'
---

<!-- markdownlint-disable-file -->

# Changes Tracking: Replace fetch_message REST Calls with PartialMessage

## Summary

Eliminated three `channel.fetch_message()` REST GET calls in `handlers.py` by replacing them with the synchronous `channel.get_partial_message()`. Removed `_fetch_message_for_refresh()` helper, refactored `_fetch_channel_and_message()` into a synchronous `_get_channel_and_partial_message()`, and inlined `get_partial_message` in `_archive_game_announcement()`.

## Added

## Modified

- `tests/unit/services/bot/events/test_handlers.py` — added three `@pytest.mark.xfail(strict=True)` tests for the not-yet-implemented `_get_channel_and_partial_message` method (success, channel not in cache, wrong channel type); removed xfail markers after implementation; deleted six obsolete `_fetch_message_for_refresh` and `_fetch_channel_and_message` tests; updated `test_refresh_game_message_success`, `test_refresh_game_message_channel_validation_fails`, `test_refresh_game_message_message_not_found`, archive announcement tests, and player-removal tests to use `get_partial_message`; updated all `_handle_game_cancelled` tests to patch `_get_channel_and_partial_message` (synchronous)
- `services/bot/events/handlers.py` — removed `_fetch_message_for_refresh` and `_fetch_channel_and_message`; added synchronous `_get_channel_and_partial_message` returning `tuple[discord.TextChannel, discord.PartialMessage] | None`; inlined `channel.get_partial_message` in `_refresh_game_message` and `_archive_game_announcement`; updated three call sites in `_update_message_for_player_removal`, `_handle_game_cancelled`, and `_try_edit_game_message`
- `tests/unit/bot/events/test_handlers_misc.py` — replaced `_fetch_channel_and_message` patches with `_get_channel_and_partial_message`; replaced `fetch_message` mock calls with `get_partial_message` in all archive announcement tests
- `tests/unit/bot/events/test_handlers_lifecycle_events.py` — replaced `_fetch_channel_and_message` patch with `_get_channel_and_partial_message` in `test_game_cancelled_delete_general_exception_is_caught`
- `tests/unit/services/bot/events/test_channel_worker.py` — replaced all seven `_fetch_channel_and_message` patch references with `_get_channel_and_partial_message`

## Removed

## Phase Status

- [x] Phase 1: RED — Add xfail tests for `_get_channel_and_partial_message`
- [x] Phase 2: GREEN — Implement refactoring and update all tests
