<!-- markdownlint-disable-file -->

# Task Research Notes: Consolidate reminder-schedule population into a single shared implementation

## Research Executed

### File Analysis

- `shared/services/game_schedules.py`
  - `schedule_join_notification` (L45-85) and `schedule_join_notifications_for_game` (L111-139) are now public — the join-notification consolidation from `.copilot-tracking/planning/plans/20260815-01-join-notification-scheduling-consolidation.plan.md` has already landed. This confirms that plan is complete and the codebase has moved since the `20260815-01` research doc was written.
  - `_populate_reminder_schedule(db, game, reminder_minutes)` (L142-161) still exists, still private, and is **not** the name used in the earlier research doc verbatim any differently — same name, same location, still exactly the function flagged as out-of-scope. It has no `update`/delete counterpart anywhere in this file or module: `shared/services/game_schedules.py` never imports `sqlalchemy.delete` and contains zero `DELETE` statements.
  - `setup_game_schedules(db, game, reminder_minutes)` (L88-108) calls `schedule_join_notifications_for_game(db, game)` then `_populate_reminder_schedule(db, game, reminder_minutes)`. Its only caller is `services/bot/announcement_loop.py:202` (a deferred game's first announcement — create-only, once per game, never re-invoked for the same game).
  - `clone_game_for_recurrence` (L194-261) calls neither `setup_game_schedules` nor `_populate_reminder_schedule` — only `_create_status_schedules`. Confirms recurrence clones get no reminder schedule at all (a separate, already-flagged gap, not investigated further here).

- `services/api/services/notification_schedule.py`
  - `NotificationScheduleService.populate_schedule` (L51-99): iterates `reminder_minutes`, computes `notification_time = game.scheduled_at - timedelta(minutes=reminder_min)`, adds a `NotificationSchedule(game_id, reminder_minutes, notification_time, game_scheduled_at, sent=False)` row via `self.db.add()` when `notification_time > now`. Adds `logger.debug`/`logger.info` calls not present in the shared twin.
  - `NotificationScheduleService.update_schedule` (L101-134): deletes existing `notification_type == "reminder"` rows for the game (L125-130, **the now-fixed scope from commit `311e6c48`**), then calls `self.populate_schedule(game, reminder_minutes)` (L134). This is the only "delete-then-repopulate" reminder path in the entire codebase.
  - `NotificationScheduleService.clear_schedule` (L136-153): deletes **all** `notification_schedule` rows for a `game_id`, unscoped by `notification_type`. Zero production callers (`grep -rn "clear_schedule" services/ shared/` → only the class definition itself); referenced only by unit tests. Pre-existing dead code, same pattern as `shared/data_access/guild_queries.py::add_participant` flagged in the prior research doc.

- `services/api/services/games.py`
  - `_setup_game_schedules` (L568-588): calls the **shared** `schedule_join_notifications_for_game(self.db, game)` (L584) directly, then constructs its own `NotificationScheduleService(self.db)` and calls `.populate_schedule(...)` (L587-588) — it does **not** call `shared.services.game_schedules.setup_game_schedules`, it re-implements that bundling inline, mixing one shared-module call with one API-only-module call. Callers: `create_game` (non-deferred path, L827-831), `clone_game` (L985), and the "clear `post_at`, announce immediately" branch of `update_game` (L2085-2088).
  - `_process_game_update_schedules` (L1811-1833): the **only** call site of `NotificationScheduleService.update_schedule` (L1829-1830), invoked from `update_game` (L2058-2060) when `schedule_needs_update` is true (i.e., the host's edit-form request touched `scheduled_at` or `reminder_minutes`).
  - Confirmed the exact bug scenario from commit `311e6c48`'s commit message by reading the code order in `update_game` (L2023-2096): `_update_prefilled_participants` (L2055, which internally can call `_add_new_mentions` → `schedule_join_notification`, L1571, creating a fresh `join_notification` row) runs **before** `_process_game_update_schedules` (L2058, which runs `update_schedule`'s DELETE) in the same request/transaction — this is the exact collateral-deletion window the fix closed. Both steps operate on `self.db` with no intermediate commit, confirming they share one transaction.

### Code Search Results

- `grep -rn "NotificationScheduleService" services/ shared/` (excluding tests)
  - Only two call sites, both in `services/api/services/games.py` (`_setup_game_schedules` L587, `_process_game_update_schedules` L1829) plus the class definition itself. `NotificationScheduleService` is never imported by `services/bot/` or `shared/`.
- `grep -rn "setup_game_schedules\|schedule_join_notifications_for_game\|_populate_reminder_schedule" services/ shared/` (excluding tests)
  - `services/bot/announcement_loop.py` imports and calls `setup_game_schedules` only.
  - `services/api/services/games.py` imports `schedule_join_notifications_for_game` directly from `shared.services.game_schedules` but never imports/calls `setup_game_schedules` or `_populate_reminder_schedule`.
  - `_populate_reminder_schedule` has exactly one caller: `setup_game_schedules` in the same file.
- `grep -rln "from services.api\|import services.api" services/bot/`
  - Zero matches. The bot never imports anything from `services.api` today.
- `grep -n "services.api" shared/database.py shared/discord/client.py shared/services/game_schedules.py`
  - Two real lazy imports exist in `shared/database.py` (`get_db_with_user_guilds`, L131 and L139) and one in `shared/discord/client.py` (L569), all local imports inside functions only ever invoked from FastAPI-route dependency chains — never reachable from `services/bot/`'s call graph. `shared/services/game_schedules.py`'s only match is the plain-text mention of "services.api" in its module docstring, not an actual import.
  - `docker/bot.Dockerfile` production stage (L82-86) copies only `pyproject.toml`, `shared/`, `services/__init__.py`, and `services/bot/` into the image — `services/api/` is never present. Confirms the "bot can't import services.api" constraint is still real at the production-image level (a dev-mode volume mount could technically expose it, but the production build cannot).
- `grep -rln "reminder_minutes" services/bot/` (excluding tests)
  - Only `services/bot/announcement_loop.py` (populate-once, deferred-announcement path) and `services/bot/events/handlers.py` (an unrelated `_reminder_minutes` parameter, always `0`, in the recurrence-confirmation DM helper — not a scheduling call). The bot has no game-edit capability at all; editing a game (which is the only thing that can trigger `update_schedule`) is web-UI/API-only. Confirms the shared module never needs, and could never trigger, a delete-then-repopulate reminder path.
- `grep -rn "notification_schedule\|NotificationSchedule\|delete(" services/bot/` (excluding tests)
  - All bot-side deletes/queries against `NotificationSchedule` are scoped by `participant_id` (`leave_game.py` L83-85, `participant_drop.py` L81-83) — narrow, single-row, correctly-scoped operations unrelated to the bulk reminder-refresh pattern. No bulk `DELETE ... WHERE game_id = ...` exists anywhere under `services/bot/`.
- `grep -rn "clear_schedule" services/ shared/` (excluding tests)
  - Zero production callers.

### Project Conventions

- Standards referenced: `.github/instructions/fastapi-transaction-patterns.instructions.md` (non-committing service functions/methods, `flush()` only for immediate IDs, docstring transaction notes) — both `_populate_reminder_schedule` and `NotificationScheduleService.populate_schedule`/`update_schedule` already comply and must continue to.
- Instructions followed: `.github/instructions/unit-tests.instructions.md` (falsifiable assertions, no coverage theater) when evaluating existing test quality below; `.github/instructions/test-driven-development.instructions.md` referenced for how any follow-up fix/consolidation should be sequenced if a real bug were found (none was, in this module).

## Key Discoveries

### Project Structure

The join-notification consolidation (`20260815-01`) is fully landed: `schedule_join_notification` and `schedule_join_notifications_for_game` are public in `shared/services/game_schedules.py`, used by both `services/api/services/games.py` and (per that plan) the bot's `join_game.py` handler. The reminder-scheduling side was explicitly left untouched and remains exactly as flagged: a private `_populate_reminder_schedule` in `shared/services/game_schedules.py` duplicating `NotificationScheduleService.populate_schedule` in `services/api/services/notification_schedule.py`.

Critically, the two "populate" duplicates are **not symmetric siblings of an update-capable pair** — only the API side has an `update_schedule` (delete-then-repopulate). The shared/bot side has no delete path for reminders at all, because the bot has no game-editing feature; the bot only ever populates reminders once, at first announcement of a previously-deferred game.

### Implementation Patterns

**Duplication confirmed, not diverged (question 1 answer):** `_populate_reminder_schedule` (`shared/services/game_schedules.py` L142-161) and `NotificationScheduleService.populate_schedule` (`services/api/services/notification_schedule.py` L51-99) implement byte-for-byte identical business logic — same early-return-on-empty-list guard, same `now = datetime.now(UTC).replace(tzinfo=None)`, same `notification_time = game.scheduled_at - timedelta(minutes=reminder_min)` computation, same `if notification_time > now` gate, same five-field `NotificationSchedule(...)` construction. The only differences are cosmetic: `db.add(...)` vs `self.db.add(...)`, and the API version has `logger.info`/`logger.debug` calls the shared version lacks entirely. This is exactly the same duplication shape as `schedule_join_notification` before it was consolidated, and none of the "has it diverged" risk that would complicate a merge — a straight extract-and-delegate is safe.

**No collateral-deletion bug class exists in the shared/bot path (question 2 answer — no live bug found here):** The bug fixed in commit `311e6c48` required a _delete_ (unscoped by `notification_type`) running in the same transaction as a _newly-created_ `join_notification` row. `shared/services/game_schedules.py` contains no `DELETE` statement anywhere — `_populate_reminder_schedule` only ever creates rows, mirroring `populate_schedule`, never `update_schedule`. Structurally, this isn't "the shared module has the bug but scoped correctly" — it never had the _opportunity_ for this bug class, because the bot (the only consumer of `setup_game_schedules`/`_populate_reminder_schedule`) has no game-edit feature to trigger a reminder refresh. `setup_game_schedules` runs exactly once per game, at first announcement, when no `join_notification` rows can yet exist for that game's participants in a conflicting way (join notifications for a deferred game's pre-filled participants are scheduled inside the same `setup_game_schedules` call via `schedule_join_notifications_for_game`, which runs _before_ `_populate_reminder_schedule` and only _adds_ rows — never deletes).

**Caller graph and the "bot can't import services.api" constraint (question 3 answer — still real):**

- `services/bot/announcement_loop.py:202` → `shared.services.game_schedules.setup_game_schedules` (bundles join-notification + reminder population) — this is the shared module's only live caller, confirmed reachable (fires on every deferred game's scheduled announcement).
- `services/api/services/games.py::_setup_game_schedules` (L568-588) → calls the shared `schedule_join_notifications_for_game` directly, but calls `NotificationScheduleService(self.db).populate_schedule(...)` for reminders instead of the shared bundler or the shared reminder function. Called from `create_game`, `clone_game`, and one branch of `update_game`.
- `services/api/services/games.py::_process_game_update_schedules` (L1811-1833) → `NotificationScheduleService.update_schedule` — the sole delete-then-repopulate reminder path, API-only, invoked from `update_game`.
- `grep -rln "from services.api\|import services.api" services/bot/` returns zero matches — the bot genuinely never imports `services.api` today. `docker/bot.Dockerfile`'s production stage (L82-86) only copies `shared/` and `services/bot/`, confirming the constraint is enforced at the image level, not just by convention.
- Both paths are live and reachable — this is not a dead-code situation. `_populate_reminder_schedule` fires on every deferred-game announcement; `NotificationScheduleService.populate_schedule`/`update_schedule` fire on every non-deferred game creation, clone, and host edit that touches `scheduled_at`/`reminder_minutes`.

### Complete Examples

Current shared-module implementation, `shared/services/game_schedules.py` L142-161 (verbatim, current):

```python
async def _populate_reminder_schedule(
    db: AsyncSession,
    game: game_model.GameSession,
    reminder_minutes: list[int],
) -> None:
    if not reminder_minutes:
        return
    now = datetime.now(UTC).replace(tzinfo=None)
    for reminder_min in reminder_minutes:
        notification_time = game.scheduled_at - timedelta(minutes=reminder_min)
        if notification_time > now:
            db.add(
                notification_schedule_model.NotificationSchedule(
                    game_id=game.id,
                    reminder_minutes=reminder_min,
                    notification_time=notification_time,
                    game_scheduled_at=game.scheduled_at,
                    sent=False,
                )
            )
```

Current API-side implementation, `services/api/services/notification_schedule.py` L51-99 (verbatim, current — the same logic, plus logging):

```python
    async def populate_schedule(
        self,
        game: game_model.GameSession,
        reminder_minutes: list[int],
    ) -> None:
        if not reminder_minutes:
            logger.info("No reminder minutes configured for game %s", game.id)
            return

        now = datetime.now(UTC).replace(tzinfo=None)
        scheduled_at = game.scheduled_at

        for reminder_min in reminder_minutes:
            notification_time = scheduled_at - timedelta(minutes=reminder_min)

            if notification_time > now:
                schedule_entry = notification_schedule_model.NotificationSchedule(
                    game_id=game.id,
                    reminder_minutes=reminder_min,
                    notification_time=notification_time,
                    game_scheduled_at=game.scheduled_at,
                    sent=False,
                )
                self.db.add(schedule_entry)
                logger.debug(...)
            else:
                logger.debug(...)
```

The (already-fixed, unrelated to this consolidation) `update_schedule`, `services/api/services/notification_schedule.py` L101-134 — kept exactly as-is by the recommended approach below, only its internal call to `populate_schedule` changes shape:

```python
    async def update_schedule(
        self,
        game: game_model.GameSession,
        reminder_minutes: list[int],
    ) -> None:
        await self.db.execute(
            delete(notification_schedule_model.NotificationSchedule).where(
                notification_schedule_model.NotificationSchedule.game_id == game.id,
                notification_schedule_model.NotificationSchedule.notification_type == "reminder",
            )
        )
        logger.debug("Deleted existing reminder schedule for game %s", game.id)
        await self.populate_schedule(game, reminder_minutes)
```

### API and Schema Documentation

Not applicable — internal-architecture-only, no external API/schema change. `NotificationSchedule` model is unchanged; only which code constructs `notification_type="reminder"` rows changes.

### Configuration Examples

Not applicable.

### Technical Requirements

- Any canonical implementation must live in `shared/services/game_schedules.py` — same constraint as the join-notification consolidation, verified still real (bot Docker image excludes `services/api/`).
- Must remain non-committing (`flush()` never needed here since no caller reads the reminder row's generated ID before commit — neither current implementation calls `flush()` for reminder rows, unlike `schedule_join_notification`, which does).
- Logging: the API version's `logger.info`/`logger.debug` calls have no test assertions depending on them (confirmed via `grep -n "caplog\|logger" tests/unit/services/api/services/test_notification_schedule.py` → no matches) — safe to either drop or port into the shared function; porting preserves existing operational log visibility with no test risk either way.
- `update_schedule`'s DELETE scoping (the `311e6c48` fix) is independent of this consolidation and must not be touched — it stays in `NotificationScheduleService`, which is the only class with any delete-then-repopulate reminder logic.

## Recommended Approach

Consolidate the reminder-population duplication using the exact same "shared canonical primitive, thin delegating wrapper" pattern already used for `schedule_join_notification`:

1. Rename `_populate_reminder_schedule` → public `populate_reminder_schedule(db, game, reminder_minutes)` in `shared/services/game_schedules.py`. Behavior unchanged (pure rename plus optional logging parity — port the API version's `logger.info`/`logger.debug` calls in so no operational visibility is lost). Update `setup_game_schedules`'s internal call to the new public name.
2. Change `NotificationScheduleService.populate_schedule` to a thin delegating wrapper:
   ```python
   async def populate_schedule(self, game, reminder_minutes) -> None:
       await populate_reminder_schedule(self.db, game, reminder_minutes)
   ```
   `update_schedule` is untouched — it still calls `self.populate_schedule(...)` (L134), which now delegates transitively; its DELETE-scoping fix from `311e6c48` is completely orthogonal and stays exactly as-is.
3. Optionally (low-risk, matches the prior consolidation's style of also tidying up nearby call sites): have `services/api/services/games.py::_setup_game_schedules` call `shared.services.game_schedules.setup_game_schedules(self.db, game, reminder_minutes)` directly instead of manually re-implementing the two-step bundling with one shared call plus one `NotificationScheduleService` call — this removes the current inconsistency where `_setup_game_schedules` mixes a shared-module call and an API-only-module call for what is conceptually one bundled operation. Not required for the core consolidation; flag as a nice-to-have, not a blocker.
4. Delete the now-dead `NotificationScheduleService.clear_schedule` and its test (zero production callers) as a separate, optional, low-risk cleanup item — same pattern as `guild_queries.add_participant` flagged (and deferred) in the prior research doc; do not bundle into this change unless requested.

No live bug exists in the reminder-scheduling shared/bot path today — flag this clearly to the user so expectations are set correctly: **this is a pure duplication-cleanup follow-up, not a bug fix.** Unlike the join-notification consolidation (which fixed two real behavioral bugs) and the `311e6c48` collateral-deletion fix (a real production bug), this reminder-population duplication has never diverged and cannot currently produce incorrect behavior, because the only "risky" operation (delete-then-repopulate) exists solely on the API side, is already correctly scoped, and has no shared-module counterpart to also need fixing.

## Implementation Guidance

- **Objectives**: exactly one implementation of "populate reminder-notification rows for a game," importable from both the bot and the API service, so any future change to reminder-population logic (e.g., a new field, a changed skip-condition) only needs to happen once.
- **Key Tasks**:
  1. Rename `_populate_reminder_schedule` → public `populate_reminder_schedule` in `shared/services/game_schedules.py`; port `logger.info`/`logger.debug` calls from `NotificationScheduleService.populate_schedule` for parity (no functional change, log-message text is free to differ slightly if desired).
  2. Update `setup_game_schedules`'s internal call to the renamed function.
  3. Replace `NotificationScheduleService.populate_schedule`'s body with a delegating call to `populate_reminder_schedule(self.db, game, reminder_minutes)`; leave `update_schedule` and `clear_schedule` structurally untouched.
  4. Update `services/api/services/notification_schedule.py`'s imports to bring in `populate_reminder_schedule` from `shared.services.game_schedules`.
  5. Update `tests/unit/shared/services/test_game_schedules.py`'s three `_populate_reminder_schedule`-targeting tests (`test_populate_reminder_schedule_skips_empty_list`, `test_populate_reminder_schedule_adds_entry_for_future_reminder`, `test_populate_reminder_schedule_skips_past_reminder`) and its `test_setup_game_schedules_delegates_to_helpers` patch target, to reference the renamed public function.
  6. `tests/unit/services/api/services/test_notification_schedule.py`'s existing `populate_schedule`-targeting tests (`test_populate_schedule_creates_future_notifications`, `test_populate_schedule_skips_past_notifications`, `test_populate_schedule_with_empty_reminders`) should continue to pass unchanged against a mock `db`, since they assert on `mock_db.add` call counts/fields, not on which function performed the add — but re-run them after the change to confirm, and consider adding one assertion-of-delegation test (patch `shared.services.game_schedules.populate_reminder_schedule` and assert it's awaited with `(self.db, game, reminder_minutes)`) matching the delegation-test pattern already used for `schedule_join_notification`'s consumers.
  7. `test_update_schedule_deletes_and_creates` and `test_update_schedule_delete_is_scoped_to_reminder_rows` (both already passing, from `311e6c48`) require no changes — `update_schedule`'s DELETE and its call to `self.populate_schedule` are untouched by this refactor.
  8. Straightforward rename/delegate/relocate — no bug-fix TDD workflow (RED/xfail) needed per "retrofitting tests for correct code" guidance in `.github/instructions/test-driven-development.instructions.md`; just keep tests green before/after.
  9. Optional, separate, lower-priority cleanups (confirm with user before bundling): (a) have `_setup_game_schedules` call the shared `setup_game_schedules` bundler instead of manually re-composing it; (b) delete dead `NotificationScheduleService.clear_schedule` and its test.
- **Dependencies**: none blocking — pure internal refactor, no schema/migration changes. No live bug is being fixed, so there is no urgency driving sequencing; can land independently of any other in-flight work.
- **Success Criteria**: `grep -rn "_populate_reminder_schedule\b" services/ shared/` finds no references (function renamed everywhere); `NotificationScheduleService.populate_schedule`'s body is a single delegating call; `_process_game_update_schedules`'s existing DELETE-scoping behavior (from `311e6c48`) is unchanged and its tests (`tests/unit/services/api/services/test_notification_schedule.py`, `tests/integration/test_notification_schedule.py`) remain green with zero modifications; full unit + integration test suites green.
