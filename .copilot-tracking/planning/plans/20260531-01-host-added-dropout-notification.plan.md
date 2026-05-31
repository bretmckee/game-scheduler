---
applyTo: '.copilot-tracking/changes/20260531-01-host-added-dropout-notification-changes.md'
---

<!-- markdownlint-disable-file -->

# Task Checklist: Host Notification When HOST_ADDED Player Drops Out

## Overview

Notify the game host via Discord DM whenever a HOST_ADDED participant voluntarily leaves a game,
covering both the Discord button leave path and the web UI (API) leave path.

## Objectives

- Add `DMFormats.host_added_dropout` and `DMPredicates.host_added_dropout` to `shared/message_formats.py`
- Extend `_validate_leave_game` in the bot handler to eager-load `GameSession.host` and `GameSession.channel`
- Send a host DM in `handle_leave_game` when the leaving participant's `position_type == HOST_ADDED`
- Publish a `NOTIFICATION_SEND_DM` event in `leave_game()` (API service) when the leaving participant is `HOST_ADDED`
- Full TDD coverage: unit tests, integration tests, and e2e tests

## Research Summary

### Project Files

- `shared/message_formats.py` — DM format and predicate definitions; new format goes here
- `services/bot/handlers/leave_game.py` — Discord button leave path; needs host and channel eager-loads
- `services/api/services/games.py` — Web UI leave path; needs HOST_ADDED detection and event publishing
- `tests/unit/shared/test_message_formats.py` — Unit tests for DM formats
- `tests/unit/bot/handlers/test_leave_game_handler.py` — Unit tests for bot leave handler
- `tests/unit/api/services/test_games.py` — Unit tests for API games service
- `tests/integration/test_leave_game.py` — Integration tests for API leave path
- `tests/e2e/helpers/discord.py` — `DMType` enum used by e2e tests

### External References

- #file:../research/20260531-01-host-added-dropout-notification-research.md — Full research findings

## Implementation Checklist

### [x] Phase 1: DM format stubs + RED unit tests

- [x] Task 1.1: Add `DMFormats.host_added_dropout` and `DMPredicates.host_added_dropout` stubs to `shared/message_formats.py`
  - Details: .copilot-tracking/planning/details/20260531-01-host-added-dropout-notification-details.md (Lines 13-29)

- [x] Task 1.2: Add xfail unit tests for format and predicate in `tests/unit/shared/test_message_formats.py`
  - Details: .copilot-tracking/planning/details/20260531-01-host-added-dropout-notification-details.md (Lines 30-55)

### [x] Phase 2: DM format implementation (GREEN)

- [x] Task 2.1: Implement `DMFormats.host_added_dropout` in `shared/message_formats.py`
  - Details: .copilot-tracking/planning/details/20260531-01-host-added-dropout-notification-details.md (Lines 58-89)

- [x] Task 2.2: Implement `DMPredicates.host_added_dropout` in `shared/message_formats.py`
  - Details: .copilot-tracking/planning/details/20260531-01-host-added-dropout-notification-details.md (Lines 90-116)

- [x] Task 2.3: Remove xfail markers from Phase 1 unit tests
  - Details: .copilot-tracking/planning/details/20260531-01-host-added-dropout-notification-details.md (Lines 117-129)

### [x] Phase 3: Bot handler RED unit tests

- [x] Task 3.1: Add xfail unit tests for HOST_ADDED leave host DM in `tests/unit/bot/handlers/test_leave_game_handler.py`
  - Details: .copilot-tracking/planning/details/20260531-01-host-added-dropout-notification-details.md (Lines 132-164)

### [x] Phase 4: Bot handler implementation (GREEN)

- [x] Task 4.1: Add `selectinload(GameSession.host)` and `selectinload(GameSession.channel)` to `_validate_leave_game`
  - Details: .copilot-tracking/planning/details/20260531-01-host-added-dropout-notification-details.md (Lines 167-193)

- [x] Task 4.2: Add host DM sending logic in `handle_leave_game` after participant deletion
  - Details: .copilot-tracking/planning/details/20260531-01-host-added-dropout-notification-details.md (Lines 194-232)

- [x] Task 4.3: Remove xfail markers from Phase 3 unit tests
  - Details: .copilot-tracking/planning/details/20260531-01-host-added-dropout-notification-details.md (Lines 233-245)

### [x] Phase 5: API service RED unit + integration tests

- [x] Task 5.1: Add xfail unit test for HOST_ADDED leave publishes `NOTIFICATION_SEND_DM` in `tests/unit/api/services/test_games.py`
  - Details: .copilot-tracking/planning/details/20260531-01-host-added-dropout-notification-details.md (Lines 248-274)

- [x] Task 5.2: Add xfail integration test for HOST_ADDED leave in `tests/integration/test_leave_game.py`
  - Details: .copilot-tracking/planning/details/20260531-01-host-added-dropout-notification-details.md (Lines 275-301)

### [x] Phase 6: API service implementation (GREEN)

- [x] Task 6.1: Capture `position_type` and `host_discord_id` before `db.delete(participant)` in `leave_game()`
  - Details: .copilot-tracking/planning/details/20260531-01-host-added-dropout-notification-details.md (Lines 304-326)

- [x] Task 6.2: After reload, publish `NOTIFICATION_SEND_DM` event if participant was `HOST_ADDED`
  - Details: .copilot-tracking/planning/details/20260531-01-host-added-dropout-notification-details.md (Lines 327-371)

- [x] Task 6.3: Remove xfail markers from unit and integration tests added in Phase 5
  - Details: .copilot-tracking/planning/details/20260531-01-host-added-dropout-notification-details.md (Lines 372-386)

### [x] Phase 7: E2E test + DMType enum

- [x] Task 7.1: Add `HOST_ADDED_DROPOUT = "host_added_dropout"` to `DMType` enum in `tests/e2e/helpers/discord.py`
  - Details: .copilot-tracking/planning/details/20260531-01-host-added-dropout-notification-details.md (Lines 389-402)

- [x] Task 7.2: Add e2e test for HOST_ADDED dropout notification via API path
  - Details: .copilot-tracking/planning/details/20260531-01-host-added-dropout-notification-details.md (Lines 403-450)

## Dependencies

- No schema migrations required
- No new RabbitMQ event types required
- No new environment variables required
- `DMFormats.host_added_dropout` must exist (Phase 2) before Phases 3–7 reference it

## Success Criteria

- HOST_ADDED player leaves via Discord button → host receives DM within seconds
- HOST_ADDED player leaves via web UI → host receives DM via RabbitMQ / `NOTIFICATION_SEND_DM`
- SELF_ADDED or ROLE_MATCHED player leaves → no host DM sent
- Host-forced removal (`update_game`) → no host DM sent
- `position_type` and discord_id captured before deletion in both paths
- All unit, integration, and e2e tests pass
