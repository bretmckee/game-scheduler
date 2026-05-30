---
applyTo: '.copilot-tracking/changes/20260530-01-deferred-game-announcement-changes.md'
---

<!-- markdownlint-disable-file -->

# Task Checklist: Deferred Game Announcement

## Overview

Allow game creators to specify a future `post_at` timestamp so the Discord announcement is held until that time, with the `AnnouncementLoop` bot task firing it and setting up schedules only after the announcement posts.

## Objectives

- Add `post_at TIMESTAMPTZ NULL` to `game_sessions` and wire it through model, schemas, and API
- Gate `_setup_game_schedules` and `_publish_game_created` on whether `post_at` is in the future
- Suppress visibility and join access for pre-announced games from non-managers
- Add an `AnnouncementLoop` asyncio task in the bot that fires due games via asyncpg LISTEN
- Add a `post_at` DateTimePicker to the frontend create/edit forms and a pending-announcement badge

## Research Summary

### Project Files

- `shared/models/game.py` (line 61–85) — `GameSession` model; `scheduled_at` and `message_id` fields
- `shared/schemas/game.py` (lines 41–246) — `GameCreateRequest`, `GameUpdateRequest`, `GameResponse`
- `services/api/services/games.py` (lines 765–815) — `_persist_and_publish`; schedule/publish calls
- `services/api/services/games.py` (lines 1919–2028) — `update_game`; `_publish_game_updated` call
- `services/api/services/games.py` (line 2101) — `join_game`
- `services/api/routes/games.py` (lines 311–415) — `create_game` form route
- `services/api/routes/games.py` (lines 417–500) — `list_games` authorization loop
- `services/api/routes/games.py` (lines 547–650) — `update_game` form route and `_parse_update_form_data`
- `services/api/routes/games.py` (lines 707–780) — `join_game` route
- `services/bot/bot.py` (lines 174–230) — `on_ready`; `MessageRefreshListener` startup pattern
- `services/bot/message_refresh_listener.py` — asyncpg LISTEN pattern to mirror in `AnnouncementLoop`
- `frontend/src/types/index.ts` (lines 86–132) — `GameSession` TypeScript interface

### External References

- #file:../research/20260530-01-deferred-game-announcement-research.md — full research with code patterns

## Implementation Checklist

### [x] Phase 1: Database foundation — migration, model, schema

- [x] Task 1.1: Add `post_at TIMESTAMPTZ NULL` to `game_sessions` via Alembic migration with NOTIFY trigger
  - Details: .copilot-tracking/planning/details/20260530-01-deferred-game-announcement-details.md (Lines 13–31)

- [x] Task 1.2: Add `post_at: Mapped[datetime | None]` to `GameSession` model
  - Details: .copilot-tracking/planning/details/20260530-01-deferred-game-announcement-details.md (Lines 32–41)

- [x] Task 1.3: Add `post_at` field to `GameCreateRequest`, `GameUpdateRequest`, and `GameResponse` schemas
  - Details: .copilot-tracking/planning/details/20260530-01-deferred-game-announcement-details.md (Lines 42–77)

### [x] Phase 2: API create path — parse and gate on `post_at`

- [x] Task 2.1: Add `post_at` form parameter to the `create_game` route and pass it through to the service
  - Details: .copilot-tracking/planning/details/20260530-01-deferred-game-announcement-details.md (Lines 80–93)

- [x] Task 2.2: Validate `post_at < scheduled_at` in `create_game` service and gate `_persist_and_publish` schedule/publish calls
  - Details: .copilot-tracking/planning/details/20260530-01-deferred-game-announcement-details.md (Lines 94–132)

### [x] Phase 3: API update path, join guard, and list visibility

- [x] Task 3.1: Extend `update_game` route and `_parse_update_form_data` with `post_at` / `clear_post_at` form fields
  - Details: .copilot-tracking/planning/details/20260530-01-deferred-game-announcement-details.md (Lines 135–149)

- [x] Task 3.2: Handle `post_at` in `update_game` service — clear-to-announce-immediately, change-time, and `_publish_game_updated` guard
  - Details: .copilot-tracking/planning/details/20260530-01-deferred-game-announcement-details.md (Lines 150–178)

- [x] Task 3.3: Guard `join_game` route — return 404 for pre-announced games
  - Details: .copilot-tracking/planning/details/20260530-01-deferred-game-announcement-details.md (Lines 179–199)

- [x] Task 3.4: Filter pending-announcement games in `list_games` route for non-managers
  - Details: .copilot-tracking/planning/details/20260530-01-deferred-game-announcement-details.md (Lines 200–230)

- [x] Task 3.5: Integration tests for join guard and list visibility
  - Details: .copilot-tracking/planning/details/20260530-01-deferred-game-announcement-details.md (Lines 231–248)

### [x] Phase 4: AnnouncementLoop bot task

- [x] Task 4.1: Create `services/bot/announcement_loop.py` with asyncpg LISTEN + `SKIP_LOCKED` query loop
  - Details: .copilot-tracking/planning/details/20260530-01-deferred-game-announcement-details.md (Lines 251–337)

- [x] Task 4.2: Wire `AnnouncementLoop` into `bot.on_ready` under `_announcement_loop_started` hasattr guard
  - Details: .copilot-tracking/planning/details/20260530-01-deferred-game-announcement-details.md (Lines 338–360)

- [x] Task 4.3: E2e tests for deferred announcement flow
  - Details: .copilot-tracking/planning/details/20260530-01-deferred-game-announcement-details.md (Lines 361–379)

### [x] Phase 5: Frontend — `post_at` field and pending-announcement badge

- [x] Task 5.1: Add `post_at` to `GameSession` TypeScript interface and API call helpers
  - Details: .copilot-tracking/planning/details/20260530-01-deferred-game-announcement-details.md (Lines 382–392)

- [x] Task 5.2: Add `post_at` DateTimePicker to `CreateGame` and `EditGame` forms
  - Details: .copilot-tracking/planning/details/20260530-01-deferred-game-announcement-details.md (Lines 393–409)

- [x] Task 5.3: Add pending-announcement badge to `MyGames` and `GameDetails`
  - Details: .copilot-tracking/planning/details/20260530-01-deferred-game-announcement-details.md (Lines 410–438)

## Dependencies

- asyncpg (already used in `MessageRefreshListener`)
- Alembic (existing migration tooling)
- No new third-party dependencies

## Success Criteria

- Game created with future `post_at` does not post to Discord until that time
- Reminder DMs do not fire before the Discord announcement appears
- Pending-announcement game visible in "My Games" to host/manager; hidden from other users' lists
- Joining a pre-announced game via API returns 404
- Clearing `post_at` on edit causes immediate announcement
- All existing game creation / announcement tests continue to pass (`post_at=None` = immediate, unchanged behavior)
