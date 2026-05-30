---
applyTo: '.copilot-tracking/changes/20260530-01-host-selected-waitlist-changes.md'
---

<!-- markdownlint-disable-file -->

# Task Checklist: HOST_SELECTED_WITH_WAITLIST signup mode

## Overview

Add a new `HOST_SELECTED_WITH_WAITLIST` signup mode that lets players self-join a waitlist
while the host promotes them to confirmed slots by dragging in the edit form, with full DM
notifications for promotions and demotions.

## Objectives

- Players can join a game as waitlisted (SELF_ADDED lands in overflow under the new mode)
- Host promotes waitlisted players by dragging them in the edit form (SELF_ADDED → HOST_ADDED upsert)
- Promoted players receive a promotion DM; demoted players receive a demotion DM (all modes)
- Bot join button enabled for the new mode (players can click Join)
- Bot embed and frontend display "open slot" placeholders for unfilled confirmed slots (all modes)
- Frontend GameForm shows a checkbox sub-option to enable the new mode under HOST_SELECTED

## Research Summary

### Project Files

- `shared/models/signup_method.py` — StrEnum base; new value requires only code change (no migration)
- `shared/utils/participant_sorting.py` — single partition choke point for all downstream views
- `shared/message_formats.py` — DM format strings; needs 2 new formats
- `services/api/services/games.py` — 4 partition callers, \_update_prefilled_participants, \_detect_and_notify_promotions
- `services/bot/events/handlers.py` — 4 partition callers, \_format_join_notification_message
- `services/bot/views/game_view.py` — join button disable guard
- `services/bot/game_message.py` — \_add_participant_fields (open slot padding)
- `frontend/src/types/index.ts` — TypeScript SignupMethod enum mirror
- `frontend/src/components/GameForm.tsx` — signup method UI
- `frontend/src/components/EditableParticipantList.tsx` — participant display

### External References

- #file:../research/20260530-01-host-selected-waitlist-research.md — full analysis with specs

### Standards References

- #file:../../.github/instructions/python.instructions.md — Python conventions
- #file:../../.github/instructions/test-driven-development.instructions.md — TDD RED/GREEN/REFACTOR
- #file:../../.github/instructions/unit-tests.instructions.md — unit test quality standards
- #file:../../.github/instructions/typescript-5-es2022.instructions.md — TypeScript conventions
- #file:../../.github/instructions/reactjs.instructions.md — React/frontend standards

## Implementation Checklist

### [x] Phase 1: Enum Additions

- [x] Task 1.1: Add `HOST_SELECTED_WITH_WAITLIST` to Python `SignupMethod` enum with display_name and description
  - Details: .copilot-tracking/planning/details/20260530-01-host-selected-waitlist-details.md (Lines 13-37)

- [x] Task 1.2: Mirror new enum value in `frontend/src/types/index.ts` with SIGNUP_METHOD_INFO entry
  - Details: .copilot-tracking/planning/details/20260530-01-host-selected-waitlist-details.md (Lines 38-60)

### [x] Phase 2: Core Partition Logic + Demotion Detection (TDD)

- [x] Task 2.1 (RED): Add `signup_method` param stub + `entered_waitlist()` stub to participant_sorting.py; write 5 xfail tests
  - Details: .copilot-tracking/planning/details/20260530-01-host-selected-waitlist-details.md (Lines 63-111)

- [x] Task 2.2 (GREEN): Implement HOST_ADDED-only partition logic and `entered_waitlist()`; remove xfail markers
  - Details: .copilot-tracking/planning/details/20260530-01-host-selected-waitlist-details.md (Lines 112-151)

### [x] Phase 3: New DM Formats (TDD)

- [x] Task 3.1 (RED): Stub `join_waitlist` and `waitlist_demotion` in DMFormats; write 6 xfail tests
  - Details: .copilot-tracking/planning/details/20260530-01-host-selected-waitlist-details.md (Lines 154-187)

- [x] Task 3.2 (GREEN): Implement `join_waitlist` and `waitlist_demotion`; remove xfail markers
  - Details: .copilot-tracking/planning/details/20260530-01-host-selected-waitlist-details.md (Lines 188-219)

### [ ] Phase 4: Backend Services — Callers + Upsert + Transitions (TDD)

- [ ] Task 4.1: Update all 10 `partition_participants` callers to pass `signup_method=game.signup_method`
  - Details: .copilot-tracking/planning/details/20260530-01-host-selected-waitlist-details.md (Lines 222-240)

- [ ] Task 4.2 (RED): Add SELF_ADDED upsert stub in `_update_prefilled_participants`; write 1 xfail test
  - Details: .copilot-tracking/planning/details/20260530-01-host-selected-waitlist-details.md (Lines 241-266)

- [ ] Task 4.3 (GREEN): Implement SELF_ADDED → HOST_ADDED upsert; remove xfail marker
  - Details: .copilot-tracking/planning/details/20260530-01-host-selected-waitlist-details.md (Lines 267-296)

- [ ] Task 4.4 (RED): Rename `_detect_and_notify_promotions` → `_detect_and_notify_transitions`; add demotion stub; write 2 xfail tests
  - Details: .copilot-tracking/planning/details/20260530-01-host-selected-waitlist-details.md (Lines 297-317)

- [ ] Task 4.5 (GREEN): Implement `_notify_demoted_users`; remove stubs and xfail markers
  - Details: .copilot-tracking/planning/details/20260530-01-host-selected-waitlist-details.md (Lines 320-334)

- [ ] Task 4.6: Integration tests — DB round-trip, upsert persistence, demotion notification chain
  - Details: .copilot-tracking/planning/details/20260530-01-host-selected-waitlist-details.md (Lines 335-363)

### [ ] Phase 5: Bot Changes (TDD)

- [ ] Task 5.1: Fix join button disable guard so `HOST_SELECTED_WITH_WAITLIST` does not disable the button; add 1 direct test
  - Details: .copilot-tracking/planning/details/20260530-01-host-selected-waitlist-details.md (Lines 366-386)

- [ ] Task 5.2 (RED): Add waitlist DM dispatch stub in `_format_join_notification_message`; write 1 xfail test
  - Details: .copilot-tracking/planning/details/20260530-01-host-selected-waitlist-details.md (Lines 387-409)

- [ ] Task 5.3 (GREEN): Implement `join_waitlist` DM dispatch; remove stub and xfail marker
  - Details: .copilot-tracking/planning/details/20260530-01-host-selected-waitlist-details.md (Lines 410-428)

- [ ] Task 5.4: E2E tests — join button state, waitlist DM content, promotion drag full chain
  - Details: .copilot-tracking/planning/details/20260530-01-host-selected-waitlist-details.md (Lines 429-460)

### [ ] Phase 6: Open Slot Placeholders — Bot (TDD)

- [ ] Task 6.1 (RED): Stub open slot padding in `_add_participant_fields`; write 2 xfail tests
  - Details: .copilot-tracking/planning/details/20260530-01-host-selected-waitlist-details.md (Lines 463-483)

- [ ] Task 6.2 (GREEN): Implement open slot padding; remove stubs and xfail markers
  - Details: .copilot-tracking/planning/details/20260530-01-host-selected-waitlist-details.md (Lines 484-506)

### [ ] Phase 7: Frontend Changes (TypeScript)

- [ ] Task 7.1: GameForm checkbox sub-option for `HOST_SELECTED_WITH_WAITLIST` with Vitest TDD
  - Details: .copilot-tracking/planning/details/20260530-01-host-selected-waitlist-details.md (Lines 509-532)

- [ ] Task 7.2: Open slot placeholder rows in participant display components with Vitest TDD
  - Details: .copilot-tracking/planning/details/20260530-01-host-selected-waitlist-details.md (Lines 533-576)

## Dependencies

- Python 3.12+ (StrEnum, match/case)
- `uv` for Python dependency management
- `vitest` for frontend tests
- No Alembic migration required
- No new RabbitMQ message types

## Success Criteria

- SELF_ADDED players land in overflow when `signup_method == HOST_SELECTED_WITH_WAITLIST`
- Players who join receive waitlist DM (not confirmed DM) under the new mode
- Host drag-promotes SELF_ADDED player → player becomes HOST_ADDED + receives promotion DM
- Any confirmed → overflow transition (all modes) triggers demotion DM
- All 10 `partition_participants` callers pass `signup_method` explicitly
- Bot join button enabled for `HOST_SELECTED_WITH_WAITLIST`
- Bot embed shows "open slot" placeholders for unfilled confirmed slots (all game types)
- GameForm shows checkbox sub-option when HOST_SELECTED is selected
- Frontend participant display shows open slot placeholder rows
- `uv run pytest tests/unit` — all pass
- `uv run mypy shared/ services/` — no errors
- `cd frontend && npm run build && npm run test` — all pass
