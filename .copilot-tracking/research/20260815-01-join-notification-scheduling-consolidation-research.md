<!-- markdownlint-disable-file -->

# Task Research Notes: Consolidate join-notification scheduling into a single shared implementation

## Research Executed

### File Analysis

- `services/api/services/games.py`
  - `_create_participant_records` (~L287-324): creates `GameParticipant` rows for a game's initial (pre-filled) participants at creation time. Does not schedule any notification itself — scheduling is deferred to `_setup_game_schedules`.
  - `_setup_game_schedules` (~L565-585): calls `self._schedule_join_notifications_for_game(game)` then `NotificationScheduleService(self.db).populate_schedule(game, reminder_minutes)`.
  - `create_game` (~L672-834): calls `_create_participant_records`, then conditionally (`if not deferred:`) calls `_setup_game_schedules`. For a deferred game (`post_at` in the future), join-notification scheduling is intentionally skipped here — no Discord message/jump_url exists yet — and is postponed until the bot's announcement loop actually posts the game.
  - `clone_game` (~L865-1001): manual clone-with-carryover. Builds new `GameParticipant` rows directly (~L960) for carried-over confirmed+waitlist participants, then calls `_setup_game_schedules(new_game, ...)` (~L982), reusing the same (now-fixed) path as creation.
  - `_add_new_mentions` (~L1498-1562): host adds one or more `@mention`s via the edit-game API. Loop creates new `GameParticipant` rows, appends each to `game.participants` (fix landed this session — the collection was already loaded earlier in the request and wasn't otherwise updated by `db.add()`), then calls `self._schedule_join_notifications_for_game(game)` **once, after the loop**.
    - Problem: this call sweeps **all** of `game.participants`, not just the newly-added ones. On a game that already has other, previously-scheduled/notified participants, this re-schedules (and will cause a duplicate DM for) everyone, every time the host adds even one more mention. Distinct from, and not fixed by, the confirmed/overflow bug fixed this session.
  - `_schedule_join_notifications_for_game` (~L1564-1583): iterates `game.participants`, calls `schedule_join_notification()` for each participant with a `user_id`. **Fixed this session** to iterate all of `game.participants` (previously only `partitioned.confirmed`, silently skipping waitlisted participants).
  - `join_game` (~L2169-2282): API self-join (web UI / any authenticated HTTP client). Creates exactly one participant, then calls `schedule_join_notification()` directly and unconditionally for that one participant — correctly scoped, was never affected by either bug found this session.
  - `_capture_old_state` / `_detect_and_notify_transitions` (~L1745-1774, ~L1845-1863): snapshot the pre-update partition state and, after the update, diff it against the new state via `waitlist_transitions.detect_and_notify_transitions`. This is the promotion/demotion subsystem — see below, out of scope for this consolidation.

- `services/api/services/notification_schedule.py`
  - `NotificationScheduleService` class: `populate_schedule`/`update_schedule`/`clear_schedule` — reminder-notification scheduling (a different `notification_type` than `join_notification`). Imports only from `shared/` (`shared.models.game`, `shared.models.notification_schedule`, `shared.models.base`) — nothing `services.api`-specific.
  - `schedule_join_notification()` module-level function (~L150-190): builds and adds one `NotificationSchedule(notification_type="join_notification", ...)` row, flushes to obtain its id, returns it. Also has zero `services.api`-specific dependencies. Despite living under `services/api/`, nothing about it requires the API service — it's a pure `shared/`-shaped helper that ended up in the wrong location.

- `shared/services/game_schedules.py`
  - Module docstring states the reason for its existence explicitly: _"Shared game schedule setup logic used by both the API service and the bot. Placing this in shared/ ensures the bot service can call it without importing from services.api, which is not included in the bot Docker image."_
  - `setup_game_schedules(db, game, reminder_minutes)` (public): calls `_schedule_join_notifications(db, game)` then `_populate_reminder_schedule(db, game, reminder_minutes)`.
  - `_schedule_join_notifications(db, game)` (~L68-87): **still has the exact confirmed-only bug already fixed in `games.py`'s copy** — iterates `partitioned.confirmed` only, silently skipping waitlisted participants. Constructs `NotificationSchedule(...)` inline directly (does not/cannot call `schedule_join_notification()`, since that lives under `services/api`, unreachable from the bot's Docker image).
  - `_populate_reminder_schedule(db, game, reminder_minutes)` (~L90-109): near-duplicate of `NotificationScheduleService.populate_schedule` — same logic (iterate `reminder_minutes`, compute `notification_time`, skip past times, create a `NotificationSchedule` row), minor differences in logging only. Not part of the join-notification bug family, but the same "shared/ reimplements an API-side class because the bot can't import it" pattern.
  - `clone_game_for_recurrence(db, source, next_at)` (~L142-208): the automatic weekly-recurrence clone. Copies only `partitioned.confirmed` participants (no waitlist carryover — a deliberate design choice, not investigated further here) via direct `GameParticipant(...)` construction (~L199). **Does not call `setup_game_schedules`/schedule any join notifications for the carried-over participants at all.** Only calls `_create_status_schedules`. This is a separate, distinct gap from the bug family fixed this session (carried-over participants arguably shouldn't get a fresh "you joined!" DM for an auto-recurrence at all — debatable, not investigated further) — flagged for awareness, explicitly **not** part of this consolidation's fix set.
  - Callers: `services/bot/announcement_loop.py:202` calls `setup_game_schedules` when posting a previously-deferred game. `services/api/services/games.py` (`_system_clone_for_recurrence`) and `services/bot/events/handlers.py:1239` (recurrence-confirmation flow) both call `clone_game_for_recurrence`.

- `services/bot/handlers/join_game.py`
  - `handle_join_game` (~L55-129): the Discord **"Join Game" button** interaction handler. Entirely separate implementation from the API's `join_game()` — writes directly to the database via `get_db_session()`, with its own validation (`_validate_join_game`) duplicating a subset of the API method's checks (game exists, status is SCHEDULED, `HOST_SELECTED` rejects self-joins, resolve/create user).
  - Creates the `GameParticipant` inline (~L90), commits, then constructs a `NotificationSchedule(...)` **inline directly** (~L104-114) rather than calling `schedule_join_notification()` — again because that helper lives under `services/api`, unreachable from the bot.
  - Schedules unconditionally (matches `join_game`'s correct behavior) — not affected by either bug found this session, but is a third independent copy of the "create participant + create its schedule row" pattern that has already partially drifted from the API version's exact field/logging choices.

- `shared/data_access/guild_queries.py`
  - `add_participant(db, guild_id, game_id, user_id, data)` (~L206-247): a third, guild-ownership-validating "add participant" function. Builds `GameParticipant(**data)`, adds, flushes. No notification scheduling at all.
  - No production callers found. `services/api/routes/channels.py`, `services/api/services/guild_service.py`, and `services/bot/guild_sync.py` all import the `guild_queries` module (for other functions), but grep across `services/` and `shared/` found zero call sites for `add_participant` itself. Only referenced from `tests/unit/shared/data_access/test_guild_queries_unit.py` and `tests/integration/test_guild_queries_integration.py`.

- `shared/services/waitlist_transitions.py`
  - `detect_and_notify_transitions(db, game, old_partitioned)`: diffs the pre-update partition snapshot against the post-update state and enqueues immediate `BotActionQueue` `send_dm` rows for anyone who was promoted (`overflow → confirmed`) or demoted (`confirmed → overflow`).
  - Already a single, correctly-centralized implementation (one function, one call site in `games.py::_detect_and_notify_transitions`, called from `update_game` on every edit).
  - Answers a fundamentally different question than the join-notification-scheduling subsystem: "did an _existing_ participant's status change as a side effect of this edit," not "does this _brand-new_ participant need to be told their status." Confirmed via `PartitionedParticipants.cleared_waitlist`/`entered_waitlist` (`shared/utils/participant_sorting.py` ~L61-96): both are set-intersections against the _previous_ snapshot's discord-id sets, so a participant with no previous entry (i.e. brand new) can never be counted as promoted or demoted — correctly out of this subsystem's scope by construction.

- `services/bot/events/handlers.py` (consumption side, already fixed this session)
  - `_should_send_join_notification` / `_format_join_notification_message`: the single place that reads a due `join_notification` `NotificationSchedule` row (60s after creation, via the scheduler daemon) and decides confirmed-welcome vs. waitlist-DM content, re-deriving status fresh at delivery time rather than trusting whatever was true at schedule-creation time.
  - This side of the system was already a single, centralized place — the bugs fixed here this session were in its _logic_ (only special-cased `HOST_SELECTED_WITH_WAITLIST`), not in its _structure_. Confirms the scattering problem is isolated to the scheduling (producer) side, not the delivery (consumer) side.

### Code Search Results

- `grep -rn "schedule_join_notification\b\|_schedule_join_notifications_for_game\|detect_and_notify_transitions" services/api/services/games.py shared/services/waitlist_transitions.py services/bot/events/handlers.py`
  - Confirms exactly the call sites listed above; no additional undiscovered call sites in these three files.
- `grep -rn "participant_model\.GameParticipant(\|GameParticipant(" services/ shared/ --include=*.py`
  - Found every `GameParticipant(...)` construction site in production code: `games.py` (×5: `_create_participant_records` ×2 branches, `clone_game`, `_add_new_mentions` ×2 branches, `_capture_old_state`'s detached-copy construction which is not a real "add"), `services/bot/handlers/join_game.py` (×1), `shared/data_access/guild_queries.py` (×1, dead code), `shared/services/game_schedules.py` (×1, `clone_game_for_recurrence`).
- `grep -rn "guild_queries.add_participant\|guild_queries.remove_participant" services/ tests/ --include=*.py`
  - Zero production callers found for `add_participant`; two test files reference it directly.
- `grep -rn "setup_game_schedules\|clone_game_for_recurrence" services/ shared/ --include=*.py`
  - Confirms the exact caller graph: `announcement_loop.py` → `setup_game_schedules`; `games.py` and `handlers.py` → `clone_game_for_recurrence`.

### Project Conventions

- Standards referenced: `.github/instructions/python.instructions.md` (imports, naming, ruff), `.github/instructions/test-driven-development.instructions.md` and `.github/instructions/unit-tests.instructions.md` (bug-fix TDD workflow: xfail regression test → fix → remove marker; falsifiable assertions), `.github/instructions/fastapi-transaction-patterns.instructions.md` (service-layer functions don't commit, caller commits — both `schedule_join_notification()` and `_schedule_join_notifications_for_game`/`_schedule_join_notifications` already follow this and it must be preserved).
- The `shared/` vs `services/api/` vs `services/bot/` split is itself a load-bearing project convention: `shared/` is importable by both services' Docker images; `services/api/` is not importable by the bot. Any consolidation target must live in `shared/`.

## Key Discoveries

### Project Structure

Two genuinely separate subsystems currently share the vocabulary "notify a participant about their game status," and only one of them is architecturally sound:

1. **Promotion/demotion detection** (`shared/services/waitlist_transitions.py`) — single implementation, single call site, correctly scoped to status _changes_ on existing participants. Not in scope for this work.
2. **New-participant join-notification scheduling** — the producer side is scattered across at least 4 independent call sites in 3 files across 2 services (`services/api/services/games.py` ×3 internal sites, `shared/services/game_schedules.py` ×1, `services/bot/handlers/join_game.py` ×1), two of which (`games.py`'s and `game_schedules.py`'s "sweep all participants" functions) are near-identical duplicates that have already drifted (one fixed, one not). The consumer side (`services/bot/events/handlers.py`) is already a single place.

### Implementation Patterns

Two distinct, non-interchangeable usage patterns exist for "schedule a join notification," and conflating them is itself a latent bug (found during this research, not previously identified):

- **Per-participant, immediate, unconditional**: exactly one new participant was just created live (self-join, host adds one `@mention`), so schedule exactly one row for exactly that participant, right now, regardless of whether they landed confirmed or waitlisted (the confirmed/waitlisted distinction only matters at _delivery_ time, already handled correctly by the bot's fixed consumer). Correctly used today by `join_game` and `handle_join_game`. **Incorrectly not used** by `_add_new_mentions`, which instead reaches for the bulk-sweep function below — see next point.
- **Bulk sweep, at a genuinely bulk "activation" moment**: an entire `game.participants` list is known to contain zero previously-scheduled rows, because the game itself (or its announcement) is brand new — initial non-deferred creation, a deferred game's first announcement, or a fresh clone. Safe _only_ under that precondition. `_add_new_mentions` violates the precondition: it calls the bulk-sweep function on an _existing_ game that may already have previously-scheduled/notified participants, risking duplicate notifications for them on every subsequent host edit that adds even one more mention.

### Complete Examples

Current (buggy) shared-module implementation, `shared/services/game_schedules.py` L68-87:

```python
async def _schedule_join_notifications(
    db: AsyncSession,
    game: game_model.GameSession,
) -> None:
    partitioned = partition_participants(
        game.participants, game.max_players, signup_method=game.signup_method
    )
    for participant in partitioned.confirmed:
        if participant.user_id:
            schedule = notification_schedule_model.NotificationSchedule(
                game_id=game.id,
                participant_id=participant.id,
                notification_type="join_notification",
                notification_time=utc_now() + timedelta(seconds=60),
                sent=False,
                game_scheduled_at=game.scheduled_at,
                reminder_minutes=None,
            )
            db.add(schedule)
            await db.flush()
```

Already-fixed API-side implementation, `services/api/services/games.py` (this session), for comparison — the target shape for the shared version, minus the `partitioned.confirmed` restriction:

```python
async def _schedule_join_notifications_for_game(self, game: game_model.GameSession) -> None:
    for participant in game.participants:
        if participant.user_id:
            await schedule_join_notification(
                db=self.db,
                game_id=game.id,
                participant_id=participant.id,
                game_scheduled_at=game.scheduled_at,
                delay_seconds=60,
            )
```

Bot's independently-duplicated per-participant scheduling, `services/bot/handlers/join_game.py` L104-114 (compare against `schedule_join_notification()` in `services/api/services/notification_schedule.py` L150-190 — same shape, hand-copied):

```python
schedule = NotificationSchedule(
    game_id=str(game_id),
    participant_id=participant.id,
    notification_type="join_notification",
    notification_time=utc_now() + timedelta(seconds=60),
    sent=False,
    game_scheduled_at=game.scheduled_at,
    reminder_minutes=None,
)
db.add(schedule)
```

### API and Schema Documentation

Not applicable — this is an internal-architecture consolidation, no external API or schema involved. `NotificationSchedule` model (`shared/models/notification_schedule.py`) is unchanged by this work; only which code constructs its rows changes.

### Configuration Examples

Not applicable.

### Technical Requirements

- Any consolidated implementation must live under `shared/` — the bot's Docker image does not include `services.api` (confirmed via `shared/services/game_schedules.py`'s own docstring, and via `compose.yaml`/Dockerfile boundaries implied by that constraint).
- `schedule_join_notification()` and `_schedule_join_notifications_for_game`/`_schedule_join_notifications` must remain non-committing (caller commits) — this is the existing, tested transaction pattern and both current copies already honor it.
- `game.participants` must be a fresh/consistent in-memory collection at the point any of these functions run — this was the root cause of a bug fixed this session (`_add_new_mentions` appending to `game.participants` explicitly rather than relying on relationship auto-refresh). Any new "create participant" helper must preserve that same explicit append.

## Recommended Approach

Consolidate into exactly two shared primitives, both relocated to `shared/services/game_schedules.py` (keeps them next to the existing `setup_game_schedules`/reminder logic rather than introducing a new module for a closely related concern):

1. **`schedule_join_notification(db, game_id, participant_id, game_scheduled_at, delay_seconds=60)`** — moved verbatim (pure relocation, no behavior change) from `services/api/services/notification_schedule.py`. Called directly, immediately, unconditionally, once per genuinely-new participant, from:
   - `GameService.join_game` (API self-join) — update its import.
   - `services/bot/handlers/join_game.py::handle_join_game` (Discord button self-join) — replaces its inline duplicate.
   - `GameService._add_new_mentions`'s participant-creation loop — replaces its current end-of-function bulk-sweep call; one call per newly-created participant, inside the loop, instead.

2. **`schedule_join_notifications_for_game(db, game)`** — renamed from private `_schedule_join_notifications` to public, fixed to iterate all of `game.participants` (not `partitioned.confirmed`-only), and to call primitive (1) internally instead of constructing `NotificationSchedule` inline. Called directly, once per game, only at genuinely-bulk moments where the whole participant list is known unscheduled:
   - `GameService._setup_game_schedules` (non-deferred creation; also reused as-is by `clone_game`).
   - `shared/services/game_schedules.py::setup_game_schedules` (a deferred game's eventual announcement, via `announcement_loop.py`) — same-module call, becomes simpler once (2) lives in this file already.

`GameService._schedule_join_notifications_for_game` is deleted outright — not kept as a wrapper. Both of its former callers (`_setup_game_schedules`, `_add_new_mentions`) call the appropriate shared function directly, imported from `shared.services.game_schedules`.

Explicitly out of scope, left untouched:

- `shared/services/waitlist_transitions.py` — different, already-correct, already-centralized subsystem (status-change diffing, not new-participant handling).
- `clone_game_for_recurrence`'s absence of join-notification scheduling for carried-over participants — a distinct, separately-debatable gap, not part of this bug family.
- `shared/services/game_schedules.py::_populate_reminder_schedule` vs. `NotificationScheduleService.populate_schedule` duplication — same root cause (bot can't import `services.api`), same shape of fix would apply, but it's reminder scheduling, not join-notification scheduling, and touching it wasn't asked for.

## Implementation Guidance

- **Objectives**: exactly one implementation each of "schedule one participant's join notification" and "schedule join notifications for a game's entire current participant list," both importable from the bot and the API service, so a future fix only needs to happen once.
- **Key Tasks**:
  1. Move `schedule_join_notification()` into `shared/services/game_schedules.py`; update `services/api/services/notification_schedule.py` and its callers' imports.
  2. Rename `_schedule_join_notifications` → public `schedule_join_notifications_for_game` in the same file; fix it to iterate all participants; have it call the moved primitive internally instead of constructing `NotificationSchedule` inline.
  3. Delete `GameService._schedule_join_notifications_for_game`; repoint `_setup_game_schedules` and `_add_new_mentions` at the shared functions directly (bulk-sweep for the former, per-participant-inside-the-loop for the latter).
  4. Update `GameService.join_game`'s import of `schedule_join_notification` to its new location.
  5. Update `services/bot/handlers/join_game.py::handle_join_game` to call the shared `schedule_join_notification()` instead of its inline duplicate.
  6. Follow the project's bug-fix TDD workflow (xfail regression test → fix → remove marker) for the `game_schedules.py` confirmed-only bug and for the `_add_new_mentions` duplicate-scheduling bug, both newly discovered during this research; straightforward relocations (steps 1, 4, 5) don't need the bug-fix workflow, just passing tests before/after per "retrofitting tests for correct code" guidance.
  7. Update all existing unit/integration/e2e tests whose patch targets reference the functions being moved, renamed, or deleted (`services.api.services.games.schedule_join_notification`, `services.api.services.games.GameService._schedule_join_notifications_for_game`, `shared.services.game_schedules._schedule_join_notifications`, and the bot-side inline construction in `join_game.py` tests).
  8. Separately (optional, low-risk cleanup): remove `shared/data_access/guild_queries.py::add_participant` and its two test files, since it has no production callers.
- **Dependencies**: none blocking — pure internal refactor, no schema/migration changes, no new third-party dependencies. Sequencing matters within the task: step 1 (move the primitive) should land before step 2 (fix + rename the sweep) since the sweep needs to call the already-relocated primitive; steps 3-5 depend on 1 and 2 both being in place.
- **Success Criteria**: `grep -rn "GameParticipant(" services/ shared/` shows exactly one non-test "create participant, then schedule" pattern per call site, all delegating to primitive (1) or (2); `_schedule_join_notifications_for_game` no longer exists anywhere; `game_schedules.py`'s sweep function schedules waitlisted participants too; a deferred-announcement game and a Discord-button self-join both exhibit the same fixed behavior as the already-fixed API paths; full unit + integration + e2e suites green.
