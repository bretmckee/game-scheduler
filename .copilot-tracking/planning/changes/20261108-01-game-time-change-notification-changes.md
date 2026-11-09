<!-- markdownlint-disable-file -->

# Release Changes: Notify participants when a game's details change

**Related Plan**: 20261108-01-game-time-change-notification.plan.md
**Implementation Date**: 2026-11-09

## Summary

Send one DM per edit to every confirmed and waitlisted participant when a host changes an announced game's time, expected duration, location or signup instructions.

## Changes

### Added

- shared/services/game_change_notifications.py - `GameNotifySnapshot`, `capture_notify_snapshot` and `notify_participants_of_changes` (one `send_dm` with `notification_type="game_updated"` per participant with a Discord user, listing each changed time/duration/location/signup-instructions field old -> new; empty and `None` text treated as equal)
- tests/unit/shared/services/test_game_change_notifications.py - unit tests for the snapshot, the helper (time, each other field, multiple fields, no-op, placeholder, excluded field) and `DMFormats.game_updated`

### Modified

- shared/message_formats.py - added `DMFormats.game_updated`
- shared/utils/games.py - added public `build_jump_url` (moved from waitlist_transitions; log message no longer says "waitlist")
- shared/services/waitlist_transitions.py - uses `shared.utils.games.build_jump_url`

### Removed

- shared/services/waitlist_transitions.py - private `_build_jump_url` (moved to shared/utils/games.py)
