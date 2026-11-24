<!-- markdownlint-disable-file -->

# Changes: Clone Game — Keep Source Date

## Phase 1: Replace fixed-past test dates with relative future dates

### Task 1.1: Convert Python unit test fixtures to relative future dates

#### Modified

- tests/unit/shared/schemas/test_game_schema.py - `VALID_SCHEDULED_AT` is now `now + 30 days`; the `post_at` test derives its value from it (one day earlier).
- tests/unit/services/api/routes/test_games_routes.py - Added `FUTURE_SCHEDULED_AT` / `FUTURE_SCHEDULED_AT_ISO` constants; `sample_game_data`, `_pydantic_error_for`, and every `create_game`/`clone_game` route call use them instead of fixed 2026 dates.
- tests/unit/services/api/services/test_games_service.py - Added `FUTURE_SCHEDULED_AT` (`now + 30 days`); all `GameCreateRequest` constructions use it (or `now + 1 day`) instead of fixed dates or bare `now()`; equality assertions in the timezone-normalization and `post_at` tests derive their expected values from the same variables; the EST conversion test builds 10:00 EST on a future date.

#### Outside the plan

- tests/unit/services/api/routes/test_games_endpoint_errors.py - Not listed in the plan; its `create_game` calls used past ISO strings that the Phase 2 validator would reject, so they now use `FUTURE_SCHEDULED_AT_ISO` (clone calls were converted too for consistency).
- tests/unit/services/test_clone_game.py - Not listed in the plan; `clone_game` builds a `GameCreateRequest` from `CLONE_AT` (2026-10-01, already past), so `SCHEDULED_AT`/`CLONE_AT`/`DEADLINE` are now relative to now, keeping their original ordering.
- test_games_service.py had many more affected constructions than the plan listed (bare `now()` values, which are not strictly in the future by the time the validator runs).

**How the scope was found**: temporarily added the Phase 2 validator to `GameCreateRequest`, ran `uv run pytest tests/unit` (68 failed, 21 errors in the 5 files above), fixed the fixtures, re-ran with the probe (2756 passed), then reverted the probe.

**Verification**: `uv run pytest tests/unit` — 2756 passed; `uv run mypy shared/ services/` — clean; `ruff check` / `ruff format` — clean.

### Task 1.2: Convert integration (and check e2e) fixtures to relative future dates

#### Modified

- None. Diverges from the plan's expectation: every listed file already used relative future dates.
  - tests/integration/services/api/services/test_game_image_integration.py - all `scheduled_at` are `now + 1–2 days`.
  - tests/integration/test_clone_game_endpoint.py - `clone_at` is `now + 14 days`; source games are `now + 7 days`.
  - tests/integration/test_games_crud.py - all creates use `now + 2–3 hours`.
  - tests/e2e/test_clone_game_e2e.py - source is `now + 2 hours`, clone is `now + 7 days`, sent explicitly. It does not depend on the frontend +14-day offset, so it is unchanged and needs no e2e run.
- Swept all of tests/integration and tests/e2e for fixed dates, negative offsets and bare `now()` values. The only past `scheduled_at` values are direct DB inserts of completed-game fixtures (test_join_game.py, test_leave_game.py), which bypass `GameCreateRequest`.

**Verification**: Full `scripts/run-integration-tests.sh |& tee output-integration.txt` with the Phase 2 validator temporarily applied — 396 passed (exit 0); the probe was reverted afterwards.

## Phase 2: Server-side guard — reject past `scheduled_at` on create/clone

### Task 2.1: RED — xfail regression tests (schema, route, integration create + clone)

#### Added

- tests/unit/shared/schemas/test_game_schema.py - `TestGameCreateRequestScheduledAt`: past aware, past naive, and past-in-a-non-UTC-zone values raise `ValidationError` on `scheduled_at` (xfail strict); future aware and future naive values are accepted unchanged (plain tests, already passing).
- tests/unit/services/api/routes/test_games_routes.py - `TestCreateGameRoutePastScheduledAt`: the create route returns 422 `"Scheduled at: must be in the future"` and never calls the service (xfail strict).
- tests/integration/test_games_crud.py - `test_create_game_past_scheduled_at_returns_422_and_persists_nothing`: POST create with a past date → 422 with that detail, and no `game_sessions` row for the guild (xfail strict).
- tests/integration/test_clone_game_endpoint.py - `test_clone_game_endpoint_past_scheduled_at_returns_422_and_persists_nothing`: clone with a past date → 422 with that detail, and no new row (xfail strict).

#### Outside the plan

- Added a non-UTC-zone case (+10:00) to prove the validator normalizes to UTC before comparing.

**Verification**: unit — 4 xfailed; scoped `scripts/run-integration-tests.sh tests/integration/test_games_crud.py tests/integration/test_clone_game_endpoint.py` — 48 passed, 2 xfailed.

### Task 2.2: GREEN — add `scheduled_at` field validator to `GameCreateRequest`

#### Modified

- shared/schemas/game.py - Added `GameCreateRequest.validate_scheduled_at_in_future`: aware values are converted to naive UTC (naive values are taken as UTC), and anything `<=` the server's UTC now is rejected; the original value is returned unchanged. Imported `UTC`. `GameUpdateRequest` is not touched.
- Removed only the six `xfail` decorators added in Task 2.1. No assertions changed. Before removal, all four unit tests reported strict XPASS.

#### Outside the plan

- The error message is `"must be in the future"`, not the planned `"scheduled_at must be in the future"`. `_format_field_errors` already prefixes the field label, so the planned text would have reached users as `"Scheduled at: scheduled_at must be in the future"`; the API now returns `"Scheduled at: must be in the future"`.

**Verification**: `uv run pytest tests/unit` — 2762 passed; `uv run mypy shared/ services/` — clean; ruff — clean; full `scripts/run-integration-tests.sh |& tee output-integration.txt` — 398 passed (includes recurrence clone tests). No e2e run needed: tests/e2e/test_clone_game_e2e.py is unchanged, and the shortest e2e lead time (test_game_rewards.py, `now + 15s`) is computed immediately before its POST.

## Phase 3: GameForm — show past-date error at form open and at submit (create mode)

### Task 3.1: RED — `it.fails` tests for initial and submit-time validation

#### Added

- `frontend/src/components/__tests__/GameForm.validation.test.tsx` - New `initial and submit-time validation` block:
  - create mode with a past `initialData.scheduled_at` shows "Date must be in the future" on render (`it.fails`)
  - edit mode with a past `initialData.scheduled_at` (IN_PROGRESS game) shows no error (plain `it`, regression guard)
  - create mode with a date that is valid on open, then `Date` advanced past it, then submit → the error is shown and `onSubmit` is not called (`it.fails`)
  - Only `Date` is faked (`vi.useFakeTimers({ toFake: ['Date'] })`), so `userEvent` and `waitFor` keep real timers.

**Verification**: before marking them, ran both create-mode tests as plain `it` and confirmed they failed for the bug ("Unable to find … Date must be in the future"), not for a setup error; with `it.fails`, the suite reports 17 passed.

### Task 3.2: GREEN — validate initial `scheduledAt` and re-validate at submit

#### Modified

- frontend/src/components/GameForm.tsx - Added module helper `initialScheduledAtError(mode, initialData)`: returns the `validateFutureDate` error for a prefilled date in create mode, and `null` in edit mode or when there is no prefilled date.
  - `scheduledAtError` uses it as a lazy `useState` initializer.
  - The `initialData` effect calls it after resetting `formData`; `mode` was added to the effect's dependencies.
  - `handleSubmit` (create mode only) re-runs `validateFutureDate(formData.scheduledAt)` before the stale-state guard. On failure it sets `scheduledAtError` plus the existing "Please fix all validation errors before submitting." banner, and returns.
- `frontend/src/components/__tests__/GameForm.validation.test.tsx` - Changed `it.fails` → `it` only; both tests had first reported "Expect test to fail".

#### Outside the plan

- `frontend/src/pages/__tests__/CloneGame.test.tsx` - The `mockGame.scheduled_at` fixture change from Task 4.1 was pulled forward into this phase. The fixed `2026-09-01T18:00:00Z` source, plus the current +14-day offset, gives a past clone date. Once the form flagged it, 12 clone submit tests failed, so the fixture is now `sourceScheduledAt = now + 7 days`. Task 4.1 still adds the new same-date tests.

**Verification**: `npm run test` — 628 passed (54 files); `npm run build` — OK; `eslint`, `prettier --check`, and `tsc --noEmit` — clean on the changed files. No Python changes in this phase.
