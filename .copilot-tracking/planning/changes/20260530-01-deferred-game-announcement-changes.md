# Changes: Deferred Game Announcement

## Summary

Add an `AnnouncementLoop` bot task that polls for deferred game sessions whose
`post_at` time has arrived, posts the Discord announcement, and sets up game
schedules (reminders, status transitions). Wire it into `bot.on_ready` alongside
the existing `MessageRefreshListener`.

## Added

- `services/bot/announcement_loop.py` — asyncpg-backed loop that queries for
  unannounced games with `post_at <= now()`, posts the Discord announcement via
  the existing handler helpers, commits `message_id`, then calls
  `_setup_game_schedules` to create reminder and status-transition schedules
- `tests/unit/bot/test_announcement_loop.py` — unit tests for
  `AnnouncementLoop._process_due` and `AnnouncementLoop._announce`
- `tests/e2e/test_deferred_game_announcement.py` — e2e tests covering
  visibility gating, time-based announcement, post-announcement visibility,
  and `clear_post_at` immediate announcement

## Modified

- `services/bot/bot.py` — added `AnnouncementLoop` import and startup block in
  `on_ready`, mirroring the `MessageRefreshListener` guard pattern
- `tests/unit/bot/test_bot_ready.py` — added tests verifying `AnnouncementLoop`
  is started exactly once in `on_ready` and not restarted on subsequent calls

## Phase 4 Progress

### Task 4.1: AnnouncementLoop implementation

### Task 4.2: Wire into bot.on_ready

### Task 4.3: E2e tests
