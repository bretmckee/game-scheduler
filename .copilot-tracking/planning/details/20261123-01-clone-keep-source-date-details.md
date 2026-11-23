<!-- markdownlint-disable-file -->

# Task Details: Clone Game — Keep Source Date

## Research Reference

**Source Research**: .copilot-tracking/research/20261122-01-clone-keep-source-date-research.md

## Phase 1: Replace fixed-past test dates with relative future dates

Retrofit only. No production change, so these tests pass right away. This phase comes first so that the Phase 2 validator doesn't break tests that build `GameCreateRequest` with dates that are already in the past.

### Task 1.1: Convert Python unit test fixtures to relative future dates

Replace hard-coded `datetime(2026, ...)` values passed to `GameCreateRequest` with `now + timedelta(days=N)`. Where a test asserts exact equality against the date (for example test_games_service.py:1148–1174, which checks aware→naive conversion), compute the expected value from the same variable instead of a second literal.

- **Files**:
  - tests/unit/shared/schemas/test_game_schema.py - `VALID_SCHEDULED_AT` (:34) → relative future
  - tests/unit/services/api/routes/test_games_routes.py - `sample_game_data` (:55)
  - tests/unit/services/api/services/test_games_service.py - :1015, :1072, :1110, :1148–1174
- **Success**:
  - grep for `datetime(20` in these files shows no fixed date that reaches a `GameCreateRequest`
  - `uv run pytest tests/unit` and `uv run mypy shared/ services/` pass
- **Research References**:
  - research (Lines 41-45) - which tests build `GameCreateRequest` with fixed dates
- **Dependencies**: none

### Task 1.2: Convert integration test fixtures to relative future dates

Do the same for integration tests that create or clone games with fixed dates.

- **Files**:
  - tests/integration/services/api/services/test_game_image_integration.py
  - tests/integration/test_clone_game_endpoint.py, tests/integration/test_games_crud.py - check, and convert any fixed past `scheduled_at`
  - tests/e2e/test_clone_game_e2e.py - check only; convert if it sends a past `scheduled_at` or depends on +14 days
- **Success**:
  - `scripts/run-integration-tests.sh |& tee output-integration.txt` passes for the touched files (use scoping args; follow `.github/instructions/test-execution.instructions.md`)
- **Research References**:
  - research (Lines 45, 55-56) - integration/e2e files to check
- **Dependencies**: none

## Phase 2: Server-side guard — reject past `scheduled_at` on create/clone

TDD bug-fix flow (`.github/instructions/test-driven-development.instructions.md`, "TDD for Bug Fixes"): write the regression tests with `xfail(strict=True)`, confirm they are xfailed, add the validator, then remove only the markers.

### Task 2.1: RED — xfail regression tests for schema, route, and integration

- **Files**:
  - tests/unit/shared/schemas/test_game_schema.py - add: past aware `scheduled_at` raises `ValidationError`; past naive raises; future aware and future naive pass
  - tests/unit/services/api/routes/test_games_routes.py - add: create with past `scheduled_at` → 422 and the service is not called
  - tests/integration/test_games_crud.py - add: POST create with past `scheduled_at` → 422, no row in `game_sessions`
  - tests/integration/test_clone_game_endpoint.py - add: clone with past `scheduled_at` → 422, no new row
- **Success**:
  - New tests report as `xfailed`; nothing else changes
- **Research References**:
  - research (Lines 52-55) - unit and integration test matrix
- **Dependencies**: Phase 1

### Task 2.2: GREEN — add `scheduled_at` field validator to `GameCreateRequest`

Add `@field_validator("scheduled_at")` to `GameCreateRequest` (shared/schemas/game.py:42; field at :47). Reject `value <= now` using the server's UTC clock. Normalize aware and naive values the way `CloneGameRequest._check_deadline` does (services/api/schemas/clone_game.py:88–103): aware → `astimezone(UTC).replace(tzinfo=None)`, compared against a naive UTC now. Raise `ValueError("scheduled_at must be in the future")`. Return the original value unchanged. Do NOT touch `GameUpdateRequest` (edit is out of scope on purpose).

Then remove only the `xfail` markers added in Task 2.1.

- **Files**:
  - shared/schemas/game.py - new validator next to the existing ones (:115, :184, :192)
  - tests added in Task 2.1 - delete only the `xfail` decorators
- **Success**:
  - Every Task 2.1 test passes without changes to its assertions
  - Create and clone routes return 422 via `_handle_game_operation_errors` (routes/games.py:358–363), with no route changes needed
  - Recurrence (`clone_game_for_recurrence`) and edit are unaffected; their existing tests still pass
  - All Python gates plus the scoped integration tests pass
- **Research References**:
  - research (Lines 41-44) - placement rationale, error mapping, paths that are unaffected
- **Dependencies**: Task 2.1

## Phase 3: GameForm — show past-date error at form open and at submit (create mode only)

TDD bug-fix flow for TypeScript: write the regression tests as Vitest `it.fails(...)` (the TS equivalent of strict xfail), confirm they fail as expected, fix, then change `it.fails` → `it` with no other test edits.

### Task 3.1: RED — `it.fails` tests for GameForm initial and submit-time validation

- **Files**:
  - frontend/src/components/**tests**/GameForm.validation.test.tsx - add:
    - create mode + past `initialData.scheduled_at` → "Date must be in the future" shown on render
    - edit mode + past `initialData.scheduled_at` → no error shown (regression guard; plain `it`, since it passes today)
    - create mode, date valid on render, fake timers advanced past it, submit → error shown and `onSubmit` not called
- **Success**:
  - The new create-mode tests fail as expected; the suite stays green
- **Research References**:
  - research (Lines 12-16) - why the error never fires for initial values today
  - research (Lines 46-48, 54) - required UX and tests
- **Dependencies**: Phase 2 (ordering only; no code dependency)

### Task 3.2: GREEN — validate initial `scheduledAt` and re-validate at submit

In frontend/src/components/GameForm.tsx, and only when `mode === 'create'`:

- Initial state (:385) and the `initialData` `useEffect` (:420): after setting `scheduledAt`, run `validateFutureDate` (imported at :73) and set `scheduledAtError` from the result. Use a lazy `useState` initializer for `scheduledAtError` (:357), or set it inside the effect, whichever fits the existing pattern.
- `handleSubmit` (:767): re-run `validateFutureDate(formData.scheduledAt)` before the guard at :770–787. If it fails, set `scheduledAtError` and return, using the result of this fresh check rather than the stale state value.
- Change `it.fails` → `it` in the Task 3.1 tests.

- **Files**:
  - frontend/src/components/GameForm.tsx - initial and submit validation
  - frontend/src/components/**tests**/GameForm.validation.test.tsx - remove `.fails`
- **Success**:
  - Task 3.1 tests pass; existing GameForm tests pass (check edit-mode and create-mode suites that use fixed past dates, and move them to future dates if they now fail)
  - `cd frontend && npm run build` and `npm run test` pass
- **Research References**:
  - research (Lines 12-17, 46-48)
- **Dependencies**: Task 3.1

## Phase 4: CloneGame — copy the source date unchanged

### Task 4.1: RED — `it.fails` tests for same-date clone behaviour

Change the CloneGame fixture `scheduled_at` (CloneGame.test.tsx:98, `2026-09-01T18:00:00Z`, already past) to a future date computed relative to now, so existing click-through-to-submit tests keep working. Then add:

- future source → picker shows the source date; POST payload `scheduled_at` equals the source value (`it.fails` until Task 4.2)
- past source → "Date must be in the future" is shown and submit makes no POST (passes once Phase 3 is in; plain `it`)

- **Files**:
  - frontend/src/pages/**tests**/CloneGame.test.tsx - fixture :98; pre-population test :177; payload test :573/:632
- **Success**:
  - The future-source test fails as expected; everything else is green
- **Research References**:
  - research (Lines 54, 58) - CloneGame test impact and the past fixture
- **Dependencies**: Phase 3

### Task 4.2: GREEN — drop the +14-day offset

In frontend/src/pages/CloneGame.tsx, `buildStage2InitialData` (:109): set `scheduled_at: sourceGame.scheduled_at`. Remove `DEFAULT_DAYS_AHEAD` (:82) and the `addDays` import (:40), which has no other users. Change `it.fails` → `it`.

- **Files**:
  - frontend/src/pages/CloneGame.tsx
  - frontend/src/pages/**tests**/CloneGame.test.tsx - remove `.fails`
- **Success**:
  - All CloneGame tests pass; `npm run build` reports no unused imports
  - Scoped e2e run `scripts/run-e2e-tests.sh |& tee output-e2e.txt` for test_clone_game_e2e.py passes (only needed if Task 1.2 changed it)
- **Research References**:
  - research (Lines 9-11, 40)
- **Dependencies**: Task 4.1

## Dependencies

- pytest, pydantic v2 `field_validator`, Vitest (`it.fails`, fake timers), React Testing Library
- scripts/run-integration-tests.sh, scripts/run-e2e-tests.sh

## Success Criteria

- Future source game → clone has the identical `scheduled_at`
- Past source game → inline "Date must be in the future" error on open; Submit blocked
- API returns 422 for any create or clone whose `scheduled_at` is past at request time, including when the date expires while the user is editing
- Edit of a past or in-progress game is not blocked
