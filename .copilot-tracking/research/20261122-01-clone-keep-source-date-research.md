<!-- markdownlint-disable-file -->

# Task Research Notes: Clone Game — keep the source game's date instead of +14 days

## Research Executed

### File Analysis

- frontend/src/pages/CloneGame.tsx
  - `DEFAULT_DAYS_AHEAD = 14` (line ~82); `buildStage2InitialData` sets `scheduled_at: addDays(new Date(sourceGame.scheduled_at), DEFAULT_DAYS_AHEAD)`. This is the only place the +2 weeks comes from. `addDays` import is used only here.
  - `handleSubmit` posts `formData.scheduledAt` verbatim; no date check of its own.
- frontend/src/components/GameForm.tsx
  - Initial `scheduledAt` = `new Date(initialData.scheduled_at)` (lines 385, 420) — would happily take the source date unchanged.
  - `scheduledAtError` is set **only** in `handleDateChange` (lines 600–604) via `validateFutureDate`. It is never computed for the initial value.
  - Submit guard (lines 770–787) only blocks on `scheduledAtError`, so an untouched past initial date passes.
  - Game-time `DateTimePicker` (lines 913–927) has `disablePast`, but its textField `error` is driven solely by `scheduledAtError` (no `onError` wired), so MUI's own past-date validation is not surfaced or enforced. `disablePast` only greys out past days in the calendar popup.
- frontend/src/utils/fieldValidation.ts:99 — `validateFutureDate(date)` returns `'Date must be in the future'` for past dates.
- services/api/routes/games.py:941–1030 (`clone_game`) and services/api/schemas/clone_game.py
  - `scheduled_at` is parsed and passed through. The only "must be in the future" validator is for carryover deadlines (clone_game.py:103). **No backend check that `scheduled_at` is in the future** — same for create (no matches for a scheduled_at-vs-now check under services/ or shared/schemas).

### Code Search Results

- `in the past|must be in the future|scheduled_at.*< now`
  - Only clone deadline validator (clone_game.py:103) and bot reminder skip (services/bot/events/handlers.py:360). Nothing rejects a past `scheduled_at`.
- `DEFAULT_DAYS_AHEAD|addDays` in CloneGame tests — no test asserts the +14 offset.

## Key Discoveries

### Answer to the question

- **Future source game**: leaving the date unchanged works fine — form pre-fills it, submit sends it, backend accepts.
- **Past source game**: it would **not** force the user to change it today. The form opens with the past date, shows no error, and submit goes through; the backend creates a game scheduled in the past (it would announce immediately, and reminders would be skipped by the bot's `scheduled_at < utc_now()` check). So "keep the same date" needs one small accompanying change to get the intended "must pick a new date" behavior.

### Pre-existing gap (affects create/edit too)

The "can't create games in the past" rule is frontend-only and only fires when the user touches the picker. Any path that pre-fills a past date (clone, or editing an old game) bypasses it, and the API never enforces it.

## Recommended Approach

1. **CloneGame.tsx**: drop the offset — `scheduled_at: sourceGame.scheduled_at` — and remove `DEFAULT_DAYS_AHEAD` and the `addDays` import.
2. **Server-side guard (the real fix, required)**: a `@field_validator("scheduled_at")` on `GameCreateRequest` (shared/schemas/game.py:42) rejecting `scheduled_at <= now` (server clock, UTC; normalize aware/naive the same way `CloneGameRequest._check_deadline` does). This is the only enforcement that can't be bypassed and doesn't depend on the browser clock; it also covers "valid when the editor opened, past by the time Submit landed".
   - **Why the schema is the right place**: `GameCreateRequest` is constructed in exactly two production places, both user-initiated — the create route (routes/games.py:461) and `GameService.clone_game` (services/games.py:974) — so one validator covers create and clone with no duplicated call sites. It follows existing precedent (`CloneGameRequest.validate_deadlines` already does a now-comparison in a schema, clone_game.py:78–103) and the class already has field validators (game.py:115, 184, 192).
   - **Error mapping comes for free**: both construction sites sit inside `try` blocks that send pydantic `ValidationError` to `_handle_game_operation_errors`, which returns **422** with field-formatted detail (routes/games.py:358–363). (A plain `ValueError` raised elsewhere would map to 403 — another reason not to hand-roll it in routes.)
   - **Unaffected paths**: recurrence (`_system_clone_for_recurrence` → `clone_game_for_recurrence`) never builds `GameCreateRequest`; edit (`update_game`) uses `GameUpdateRequest`, intentionally excluded.
   - **Test fallout is expected and correct to fix**: tests building `GameCreateRequest` with fixed dates that are now past must move to relative future dates (`now + timedelta(...)`) — tests/unit/shared/schemas/test_game_schema.py (`VALID_SCHEDULED_AT`, :34), tests/unit/services/api/routes/test_games_routes.py (:55), tests/unit/services/api/services/test_games_service.py (:1015+), tests/integration/services/api/services/test_game_image_integration.py. These fixed dates are latent time bombs regardless of this change.
3. **GameForm.tsx — UX only** (create mode, so editing a past/in-progress game isn't blocked):
   - Run `validateFutureDate` on the initial `scheduledAt` (initial-state path and the `initialData` `useEffect`) so a past cloned date shows "Date must be in the future" as soon as the form opens.
   - Re-run it in `handleSubmit` so the time-elapsed case gets an inline field error instead of a round trip to the server's 422.

### Testing Strategy

| Level       | Existing tests affected                                                                                                                                                                  | New tests needed                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              | What only this level proves                            |
| ----------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------ |
| Unit        | frontend/src/pages/**tests**/CloneGame.test.tsx:177 (pre-population), :573 (payload has `scheduled_at`); fixture date `2026-09-01T18:00:00Z` at :98 is now in the past relative to today | CloneGame: future source → picker shows same date, payload `scheduled_at` equals source; past source → error shown, submit blocked, no POST. GameForm: create-mode past initialData shows error; edit-mode does not; create-mode date valid on entry but past at submit (fake timers advance past it) → error shown, `onSubmit` not called. Schema (tests/unit/shared/schemas/test_game_schema.py): past `scheduled_at` raises, future passes, naive and aware both handled. Route (tests/unit/services/api/routes/test_games_routes.py): past `scheduled_at` on create → 422, service not called. Plus converting the fixed-past-date tests listed in step 2 | Form wiring, validator logic, error mapping            |
| Integration | tests/integration/test_clone_game_endpoint.py, tests/integration/test_games_crud.py                                                                                                      | One case each for create and clone: past `scheduled_at` → 422, no row created. Check existing cases use future dates                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          | Real route → HTTP status and that nothing is persisted |
| E2E         | tests/e2e/test_clone_game_e2e.py                                                                                                                                                         | None — check it doesn't rely on +14 days or a past source date                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                | Discord posting unchanged; no new external behavior    |

Note: the CloneGame test fixture's `scheduled_at` (2026-09-01) is already past, so after step 2 tests that click through to submit will need a future fixture date (or fake timers).

## Implementation Guidance

- **Objectives**: Clone copies the source date exactly; a past date must be changed before submit.
- **Key Tasks**: steps 1–3 above plus the tests in the table.
- **Dependencies**: none.
- **Success Criteria**: future source → cloned with identical `scheduled_at`; past source → inline "Date must be in the future" error and Submit blocked; API returns 422 for any create/clone whose `scheduled_at` is past at request time, including when the date expired during editing.
