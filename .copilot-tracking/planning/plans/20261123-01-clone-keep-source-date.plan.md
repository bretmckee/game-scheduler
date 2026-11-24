---
applyTo: '.copilot-tracking/planning/changes/20261123-01-clone-keep-source-date-changes.md'
---

<!-- markdownlint-disable-file -->

# Task Checklist: Clone Game — Keep Source Date

## Overview

Make Clone Game copy the source game's `scheduled_at` exactly instead of adding 14 days, and require the user to change any date that is in the past.

## Objectives

- A cloned game keeps the source `scheduled_at` unchanged when it is still in the future
- A past source date shows "Date must be in the future" as soon as the form opens, and Submit is blocked
- The API rejects (422) any create or clone whose `scheduled_at` is past at request time
- Editing past or in-progress games is not affected

## Research Summary

### Project Files

- frontend/src/pages/CloneGame.tsx - source of the +14-day offset (`DEFAULT_DAYS_AHEAD`, `addDays`)
- frontend/src/components/GameForm.tsx - `scheduledAtError` only set when the picker changes; never for initial values or at submit
- shared/schemas/game.py - `GameCreateRequest`, used by both create and clone; gets the new validator
- services/api/schemas/clone_game.py - `_check_deadline` aware/naive normalization pattern to copy
- services/api/routes/games.py - `_handle_game_operation_errors` maps `ValidationError` → 422

### External References

- .copilot-tracking/research/20261122-01-clone-keep-source-date-research.md - root-cause analysis, recommended approach, test matrix

### Standards References

- .github/instructions/test-driven-development.instructions.md - bug-fix xfail flow (pytest `xfail(strict=True)`, Vitest `it.fails`)
- .github/instructions/unit-tests.instructions.md - assertion and mock-verification rules
- .github/instructions/integration-tests.instructions.md - integration test conventions
- .github/instructions/test-execution.instructions.md - `tee` output capture for integration/e2e scripts

## Implementation Checklist

### [x] Phase 1: Replace fixed-past test dates with relative future dates

- [x] Task 1.1: Convert Python unit test fixtures to relative future dates
  - Details: .copilot-tracking/planning/details/20261123-01-clone-keep-source-date-details.md (Lines 13-27)

- [x] Task 1.2: Convert integration (and check e2e) fixtures to relative future dates
  - Details: .copilot-tracking/planning/details/20261123-01-clone-keep-source-date-details.md (Lines 28-41)

### [x] Phase 2: Server-side guard — reject past `scheduled_at` on create/clone

- [x] Task 2.1: RED — xfail regression tests (schema, route, integration create + clone)
  - Details: .copilot-tracking/planning/details/20261123-01-clone-keep-source-date-details.md (Lines 46-58)

- [x] Task 2.2: GREEN — add `scheduled_at` field validator to `GameCreateRequest`; remove xfail markers
  - Details: .copilot-tracking/planning/details/20261123-01-clone-keep-source-date-details.md (Lines 59-76)

### [x] Phase 3: GameForm — show past-date error at form open and at submit (create mode)

- [x] Task 3.1: RED — `it.fails` tests for initial and submit-time validation
  - Details: .copilot-tracking/planning/details/20261123-01-clone-keep-source-date-details.md (Lines 81-94)

- [x] Task 3.2: GREEN — validate initial `scheduledAt` and re-validate in `handleSubmit`
  - Details: .copilot-tracking/planning/details/20261123-01-clone-keep-source-date-details.md (Lines 95-112)

### [x] Phase 4: CloneGame — copy the source date unchanged

- [x] Task 4.1: RED — future fixture date and `it.fails` same-date tests
  - Details: .copilot-tracking/planning/details/20261123-01-clone-keep-source-date-details.md (Lines 115-129)

- [x] Task 4.2: GREEN — drop the +14-day offset, `DEFAULT_DAYS_AHEAD`, and the `addDays` import
  - Details: .copilot-tracking/planning/details/20261123-01-clone-keep-source-date-details.md (Lines 130-143)

## Dependencies

- uv / pytest / mypy; pydantic v2 `field_validator`
- Vitest (`it.fails`, fake timers), React Testing Library
- scripts/run-integration-tests.sh, scripts/run-e2e-tests.sh

## Success Criteria

- Future source game → clone POST carries the identical `scheduled_at`
- Past source game → inline error on open; no POST until the date is changed
- Create or clone with a past `scheduled_at` → 422 and no row persisted
- Edit and recurrence paths unchanged; all phase gates green at every phase boundary
