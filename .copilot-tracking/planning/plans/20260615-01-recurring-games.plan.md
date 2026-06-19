---
applyTo: '.copilot-tracking/changes/20260615-01-recurring-games-changes.md'
---

<!-- markdownlint-disable-file -->

# Task Checklist: Recurring Games

## Overview

Add recurring game support: when a game with a `recur_rule` (RFC 5545 RRULE string) completes, automatically clone it to the next occurrence with host DM confirmation, zombie-game prevention, and a frontend RRULE builder.

## Objectives

- Add `recur_rule VARCHAR(200) NULL` column to `game_sessions` and expose it in all relevant schemas
- Implement `_system_clone_for_recurrence()` to create post-completion clones (`post_at=None`, invisible to announcement loop)
- Implement `RecurrenceConfirmationView` (Confirm/Decline Discord buttons) and `DMFormats.recurrence_confirmation`
- Trigger recurrence clone at COMPLETED status transition; schedule host DM confirmation
- Cancel unconfirmed zombie clones when their IN_PROGRESS transition fires
- Add integration and e2e tests covering the full confirmation and zombie-cancel lifecycles
- Add `RecurrenceSelector` frontend component and wire it into the game create/edit forms

## Research Summary

### Project Files

- `shared/models/game.py` — `GameSession` model; `recur_rule` field goes here
- `services/api/services/games.py` — `clone_game()` and new `_system_clone_for_recurrence()`
- `services/api/schemas/game.py` — `GameCreateRequest`, `GameUpdateRequest`, `GameResponse`
- `shared/message_formats.py` — `DMFormats`; `recurrence_confirmation` format goes here
- `services/bot/views/clone_confirmation_view.py` — pattern for `RecurrenceConfirmationView`
- `services/bot/events/handlers.py` — `_handle_post_transition_actions`, `_handle_status_transition_due`, `_handle_notification_due`
- `services/bot/announcement_loop.py` — only picks up games with `post_at IS NOT NULL`; no changes needed
- `frontend/src/components/DurationSelector.tsx` — pattern for `RecurrenceSelector`

### External References

- #file:../research/20260615-01-recurring-games-research.md — Full research findings, zombie-prevention design, API confirmation path, RRULE UI spec

## Implementation Checklist

### [x] Phase 1: DB Migration + Model + API Schemas + Clone Propagation

- [x] Task 1.1: Generate Alembic migration for `recur_rule VARCHAR(200) NULL`
  - Details: .copilot-tracking/planning/details/20260615-01-recurring-games-details.md (Lines 13-30)

- [x] Task 1.2: Add `recur_rule: Mapped[str | None]` to `GameSession` model
  - Details: .copilot-tracking/planning/details/20260615-01-recurring-games-details.md (Lines 31-49)

- [x] Task 1.3: Add `recur_rule: str | None = None` to `GameCreateRequest`, `GameUpdateRequest`, `GameResponse`
  - Details: .copilot-tracking/planning/details/20260615-01-recurring-games-details.md (Lines 50-68)

- [x] Task 1.4: Copy `recur_rule` in `clone_game()` + write `test_clone_game_propagates_recur_rule`
  - Details: .copilot-tracking/planning/details/20260615-01-recurring-games-details.md (Lines 69-95)

### [x] Phase 2: DM Format + `RecurrenceConfirmationView` Stubs + RED Unit Tests

- [x] Task 2.1: Add `DMFormats.recurrence_confirmation` stub (`NotImplementedError`) to `shared/message_formats.py`
  - Details: .copilot-tracking/planning/details/20260615-01-recurring-games-details.md (Lines 98-116)

- [x] Task 2.2: Create `services/bot/views/recurrence_confirmation_view.py` with stub `RecurrenceConfirmationView`
  - Details: .copilot-tracking/planning/details/20260615-01-recurring-games-details.md (Lines 117-140)

- [x] Task 2.3: Add xfail unit tests for `DMFormats.recurrence_confirmation` in `tests/unit/shared/test_message_formats.py`
  - Details: .copilot-tracking/planning/details/20260615-01-recurring-games-details.md (Lines 141-157)

- [x] Task 2.4: Create `tests/unit/services/bot/views/test_recurrence_confirmation_view.py` with xfail tests
  - Details: .copilot-tracking/planning/details/20260615-01-recurring-games-details.md (Lines 158-176)

### [x] Phase 3: DM Format + `RecurrenceConfirmationView` GREEN

- [x] Task 3.1: Implement `DMFormats.recurrence_confirmation` in `shared/message_formats.py`
  - Details: .copilot-tracking/planning/details/20260615-01-recurring-games-details.md (Lines 179-202)

- [x] Task 3.2: Implement full `RecurrenceConfirmationView` (Confirm/Decline buttons, NOTIFY, cancel)
  - Details: .copilot-tracking/planning/details/20260615-01-recurring-games-details.md (Lines 203-222)

- [x] Task 3.3: Remove xfail markers from Phase 2 tests; verify all pass
  - Details: .copilot-tracking/planning/details/20260615-01-recurring-games-details.md (Lines 223-233)

### [x] Phase 4: `_system_clone_for_recurrence` Stub + RED Unit Tests

- [x] Task 4.1: Add `_system_clone_for_recurrence` stub to `GameService` in `services/api/services/games.py`
  - Details: .copilot-tracking/planning/details/20260615-01-recurring-games-details.md (Lines 237-259)

- [x] Task 4.2: Create `tests/unit/services/test_system_clone_for_recurrence.py` with 6 xfail tests
  - Details: .copilot-tracking/planning/details/20260615-01-recurring-games-details.md (Lines 260-281)

### [x] Phase 5: `_system_clone_for_recurrence` GREEN

- [x] Task 5.1: Implement `_system_clone_for_recurrence` — copy fields, `post_at=None`, carry over participants, call `_create_game_status_schedules`
  - Details: .copilot-tracking/planning/details/20260615-01-recurring-games-details.md (Lines 284-307)

- [x] Task 5.2: Remove xfail markers from Phase 4 tests; verify all pass
  - Details: .copilot-tracking/planning/details/20260615-01-recurring-games-details.md (Lines 308-317)

### [x] Phase 6: Handler Modifications Stubs + RED Unit Tests

- [x] Task 6.1: Add `_handle_recurrence_confirmation` stub to `EventHandlers` in `services/bot/events/handlers.py`
  - Details: .copilot-tracking/planning/details/20260615-01-recurring-games-details.md (Lines 321-338)

- [x] Task 6.2: Create `tests/unit/services/bot/events/test_handlers_recurrence.py` with 6 xfail tests (trigger + zombie + dispatch)
  - Details: .copilot-tracking/planning/details/20260615-01-recurring-games-details.md (Lines 339-366)

### [x] Phase 7: Handler Modifications GREEN

- [x] Task 7.1: Modify `_handle_post_transition_actions` to call `_system_clone_for_recurrence` at COMPLETED + schedule notification
  - Details: .copilot-tracking/planning/details/20260615-01-recurring-games-details.md (Lines 370-398)

- [x] Task 7.2: Add zombie-clone cancel in `_handle_status_transition_due` (`message_id=None AND recur_rule IS NOT NULL` → CANCELLED)
  - Details: .copilot-tracking/planning/details/20260615-01-recurring-games-details.md (Lines 399-423)

- [x] Task 7.3: Implement `_handle_recurrence_confirmation` + add `recurrence_confirmation` dispatch to `_handle_notification_due`
  - Details: .copilot-tracking/planning/details/20260615-01-recurring-games-details.md (Lines 424-454)

- [x] Task 7.4: Remove xfail markers from Phase 6 tests; verify all pass
  - Details: .copilot-tracking/planning/details/20260615-01-recurring-games-details.md (Lines 455-465)

### [x] Phase 8: Integration Tests (Retrofitting)

- [x] Task 8.1: Fix `update_game` — handle `clear_post_at=true` when `post_at=NULL AND recur_rule IS NOT NULL`; write unit tests
  - Details: .copilot-tracking/planning/details/20260615-01-recurring-games-details.md (Lines 470-499)

- [x] Task 8.2: Create `tests/integration/test_recurrence_clone.py` with 4 integration tests; run suite
  - Details: .copilot-tracking/planning/details/20260615-01-recurring-games-details.md (Lines 501-521)

### [x] Phase 9: E2E Tests (Retrofitting)

- [x] Task 9.1: Create `tests/e2e/test_recurring_game.py` with 2 e2e tests (confirm via API + zombie cancel); run suite
  - Details: .copilot-tracking/planning/details/20260615-01-recurring-games-details.md (Lines 524-554)

### [ ] Phase 10: Frontend `RecurrenceSelector`

- [ ] Task 10.1: Write failing Vitest tests for `RecurrenceSelector` (RRULE computation, UI options)
  - Details: .copilot-tracking/planning/details/20260615-01-recurring-games-details.md (Lines 558-578)

- [ ] Task 10.2: Implement `RecurrenceSelector.tsx` — frequency dropdown, interval stepper, RRULE builder
  - Details: .copilot-tracking/planning/details/20260615-01-recurring-games-details.md (Lines 580-609)

- [ ] Task 10.3: Wire `RecurrenceSelector` into game create/edit forms; send `recur_rule` in request body
  - Details: .copilot-tracking/planning/details/20260615-01-recurring-games-details.md (Lines 611-635)

## Dependencies

- `python-dateutil` ≥ 2.9.0 (already installed as transitive dep of `icalendar~=6.0.0` — no new packages)
- No schema changes beyond `recur_rule` column

## Success Criteria

- Game with `recur_rule` set completes → clone exists in DB with `post_at=NULL, message_id=NULL`
- Host confirms via Discord button → clone announced immediately (Discord message posted)
- Host confirms via `PUT /{clone_id}` with `clear_post_at=true` → clone announced (e2e-testable path)
- Host ignores → clone status=CANCELLED when IN_PROGRESS transition fires
- Host declines via Discord → clone status=CANCELLED immediately
- Clone inherits `recur_rule` → chain continues each occurrence
- Games without `recur_rule` → zero change to existing behavior
- All unit, integration, and e2e tests pass with no regressions
