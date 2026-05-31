---
applyTo: '.copilot-tracking/changes/20260531-01-host-added-dropout-notification-changes.md'
---

<!-- markdownlint-disable-file -->

# Changes: Host Notification When HOST_ADDED Player Drops Out

## Summary

Adds host DM notification when a HOST_ADDED participant voluntarily leaves a game, covering both
the Discord button leave path and the web UI (API) leave path.

---

## Added

<!-- New files created during implementation -->

### Phase 1

### Phase 2

### Phase 3

### Phase 4

### Phase 5

### Phase 6

### Phase 7

- `tests/e2e/test_host_added_dropout_notification.py` — new e2e test file

---

## Modified

<!-- Existing files changed during implementation -->

### Phase 1

- `shared/message_formats.py` — added `DMFormats.host_added_dropout` and `DMPredicates.host_added_dropout` stubs (raise `NotImplementedError`)
- `tests/unit/shared/test_message_formats.py` — added `import pytest`

### Phase 2

- `shared/message_formats.py` — implemented `DMFormats.host_added_dropout` and `DMPredicates.host_added_dropout`
- `tests/unit/shared/test_message_formats.py` — removed xfail markers from all 8 host_added_dropout tests

### Phase 3

- `tests/unit/bot/handlers/test_leave_game_handler.py` — added `DMPredicates` and `ParticipantType` imports; added 3 HOST_ADDED leave tests (1 xfail, 2 immediately-passing negative tests)

### Phase 4

- `services/bot/handlers/leave_game.py` — added `DMFormats` and `ParticipantType` imports; added `selectinload(GameSession.host/channel)` to `_validate_leave_game`; added host DM block in `handle_leave_game`
- `tests/unit/bot/handlers/test_leave_game_handler.py` — removed xfail from `test_host_added_leave_sends_dm_to_host`

### Phase 5

- `tests/unit/api/services/test_games.py` — added `messaging_events` import; added `test_host_added_leave_publishes_notification_send_dm` (xfail) and `test_non_host_added_leave_does_not_publish_notification` to `TestLeaveGame`
- `tests/integration/test_leave_game.py` — added `DMPredicates` import, `dataclass` import; added `test_host_added_leave_sends_dm_to_host`

### Phase 6

- `services/api/services/games.py` — captured `position_type` and `host_discord_id` before `db.delete`; published `NOTIFICATION_SEND_DM` event after reload when `HOST_ADDED`
- `tests/unit/api/services/test_games.py` — removed xfail from `test_host_added_leave_publishes_notification_send_dm`; added `uuid` import; added `game.id = str(uuid.uuid4())`, `game.title`, `game.message_id` setup

### Phase 7

- `tests/e2e/helpers/discord.py` — added `HOST_ADDED_DROPOUT = "host_added_dropout"` to `DMType` enum; added `DMType.HOST_ADDED_DROPOUT: DMPredicates.host_added_dropout(game_title)` to `wait_for_recent_dm` predicates dict
- `tests/e2e/test_host_added_dropout_notification.py` — new file; `test_host_added_dropout_sends_dm_to_host` creates game with `discord_user_id` as host and Player A as HOST_ADDED participant, Player A leaves via API, verifies host receives `HOST_ADDED_DROPOUT` DM via `main_bot_helper`

---

## Removed

<!-- Files or code deleted during implementation -->

---

## Release Summary

<!-- Filled in when all phases complete -->
