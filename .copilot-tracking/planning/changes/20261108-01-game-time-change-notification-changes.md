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
- tests/integration/test_game_change_notification.py - integration tests through `PUT /api/v1/games/{id}` and `bot_action_queue` on an announced max_players=1 game: a time change enqueues exactly one `game_updated` send_dm per confirmed and waitlisted participant (message shows old and new `<t:...:F>`, payload carries the new `game_time_unix`); resubmitting the same time and a title-only edit enqueue none
- tests/e2e/test_game_update.py - `test_game_time_change_sends_dm`: the real test user (via `test_user_discord_user_id`, which owns cleanup of that `users` row) is a participant on an announced game; moving `scheduled_at` by one hour delivers a `game_updated` DM containing the old and new `<t:...:F>` and the game's jump URL

### Modified

- shared/message_formats.py - added `DMFormats.game_updated` and `DMPredicates.game_updated` (matches "The host updated **{title}**", so it never matches join/promotion DMs for the same game)
- tests/e2e/helpers/discord.py - added `DMType.GAME_UPDATED` and registered it in `wait_for_recent_dm`
- tests/unit/shared/test_message_formats.py - `DMPredicates.game_updated` tests: matches a game_updated DM; rejects a promotion DM for the same title, a different title and `None` content
- docs/PLAYER-GUIDE.md - "Game Updates" now states the exact rule (announced games only; one DM per edit to confirmed and waitlisted participants when start time, expected duration, location or signup instructions change, listing old and new values with a game link; title/description/rewards edits send none; max-players/signup-method waitlist moves send the existing promotion/waitlist DMs); "What if the game time changes?" adds old/new times and that waitlisted players are notified
- shared/utils/games.py - added public `build_jump_url` (moved from waitlist_transitions; log message no longer says "waitlist")
- shared/services/waitlist_transitions.py - uses `shared.utils.games.build_jump_url`
- services/api/services/games.py - `update_game` captures a `GameNotifySnapshot` before `_update_game_fields` and, for announced games only, awaits `notify_participants_of_changes` after the reload (so resolved `where`/`signup_instructions` are compared) and before `_publish_game_updated`; the `clear_post_at` announce-now path returns before it
- tests/unit/services/api/services/test_games_service.py - regression tests: announced time change awaits the helper with the OLD-value snapshot; helper runs before the update event is published; unannounced and `clear_post_at` announce-now edits do not call it (the two negative cases are guards that already passed, so they carry no xfail marker)

### Removed

- shared/services/waitlist_transitions.py - private `_build_jump_url` (moved to shared/utils/games.py)
