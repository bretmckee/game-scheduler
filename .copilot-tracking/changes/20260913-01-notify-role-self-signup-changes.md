<!-- markdownlint-disable-file -->

# Release Changes: Suppress Notify-Role Ping for HOST_SELECTED Games

**Related Plan**: 20260913-01-notify-role-self-signup.plan.md
**Implementation Date**: 2026-09-14

## Summary

Suppresses the `notify_role_ids` Discord role mention/ping in game announcements when a game's `signup_method` is `HOST_SELECTED` (no user can self-join, so pinging is pointless), while leaving the ping unchanged for every other `signup_method`.

## Changes

### Added

- tests/unit/services/bot/formatters/test_game_message.py - Added `test_format_game_announcement_host_selected_suppresses_role_mention` (Task 1.1/1.2 RED/GREEN)

### Modified

- services/bot/formatters/game_message.py - Imported `SignupMethod`; gated the role-mention loop on `signup_method != SignupMethod.HOST_SELECTED.value` (Task 1.2)

### Removed

## Release Summary

**Total Files Affected**: 2

### Files Created (0)

None

### Files Modified (2)

- services/bot/formatters/game_message.py
- tests/unit/services/bot/formatters/test_game_message.py

### Files Removed (0)

None

### Dependencies & Infrastructure

- **New Dependencies**: None
- **Updated Dependencies**: None
- **Infrastructure Changes**: None
- **Configuration Updates**: None

### Testing Requirements

- `uv run pytest tests/unit/services/bot/formatters/test_game_message.py -k host_selected_suppresses_role_mention -v` — RED confirmed `1 xfailed` before Task 1.2, GREEN confirmed `1 passed` after
- `uv run pytest tests/unit` — 2575 passed, no xfail markers remaining
- `uv run mypy shared/ services/` — clean
- `uv run ruff check services/bot/formatters/game_message.py tests/unit/services/bot/formatters/test_game_message.py` — clean
