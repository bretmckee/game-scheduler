<!-- markdownlint-disable-file -->

# Task Research Notes: Recurring Games

## Research Executed

### File Analysis

- `services/api/schemas/clone_game.py`
  - `CloneGameRequest` holds `scheduled_at`, `player_carryover` (`YES`/`YES_WITH_DEADLINE`/`NO`), optional deadlines
  - `CarryoverOption` enum already covers YES / YES_WITH_DEADLINE / NO
- `services/api/services/games.py`
  - `clone_game()` requires `CurrentUser` + `RoleVerificationService` (permission check)
  - `_persist_and_publish()`: sets `deferred = game.post_at is not None and game.post_at > now`; skips `_setup_game_schedules` and `_publish_game_created` when deferred
  - `_create_game_status_schedules()`: always called at creation regardless of deferral
  - `_apply_deadline_carryover()`: creates `ParticipantActionSchedule` rows + `clone_confirmation` notification schedule entries
  - `post_at < scheduled_at` enforced in `create_game()`; **not** in `_persist_and_publish()` directly
- `services/api/routes/games.py`
  - `PUT /{game_id}` accepts `clear_post_at: bool` — sets `post_at = utcnow()` and sends `NOTIFY game_announcement_changed`
  - `_is_pending_announcement()`: `post_at is not None AND post_at > now AND message_id is None`
- `services/bot/announcement_loop.py`
  - Queries: `post_at IS NOT NULL AND post_at <= now AND message_id IS NULL AND status = SCHEDULED`
  - `_announce()`: posts Discord message, sets `message_id`, then calls `setup_game_schedules()` (reminders + join notifications)
  - Games with `post_at = NULL` are **invisible to the loop entirely**
- `services/bot/events/handlers.py`
  - `_handle_post_transition_actions()`: fires after each status transition commit; currently handles rewards-reminder DM at COMPLETED
  - `_handle_status_transition_due()`: validates transition, commits, calls `_handle_post_transition_actions()`, refreshes Discord message
  - `_handle_clone_confirmation()`: handles the `clone_confirmation` notification type — sends DM with `CloneConfirmationView`
  - `_send_dm()`: consistent error-handling wrapper used by all DM paths
- `services/bot/views/clone_confirmation_view.py`
  - `CloneConfirmationView`: Confirm deletes `ParticipantActionSchedule`; Decline triggers drop handler
  - Pattern for the new `RecurrenceConfirmationView`
- `shared/models/game.py`
  - `GameSession` fields: `recur_rule` — **does not exist yet** (new column needed)
  - `post_at: datetime | None` already exists
  - `message_id: str | None` already exists
- `shared/message_formats.py`
  - `DMFormats.clone_confirmation()` exists as model for the new recurrence DM format
- `shared/models/participant_action_schedule.py`
  - `ParticipantActionSchedule`: `game_id`, `participant_id` (UNIQUE), `action`, `action_time`, `processed`
- `tests/e2e/test_deferred_game_announcement.py`
  - Confirmed `clear_post_at=true` via `PUT /{game_id}` triggers immediate announcement — the exact mechanism for host confirmation via API/frontend
  - Pattern for recurrence confirmation e2e test

### Code Search Results

- `post_at` usage
  - `AnnouncementLoop._process_due`: `post_at IS NOT NULL AND post_at <= now AND message_id IS NULL AND status = SCHEDULED` — games with `post_at = NULL` are never touched
  - `_is_pending_announcement`: `post_at is not None AND post_at > now AND message_id is None`
- `_handle_post_transition_actions`
  - Called at every status transition; currently only acts at `COMPLETED` (rewards reminder)
  - Direct injection point for recurrence clone trigger
- `clear_post_at` → `game_announcement_changed` NOTIFY flow
  - Already wires `PUT /{game_id}` → announcement loop wake → Discord post
  - Recurrence host confirmation reuses this exact path

### External Research

- `#fetch:https://dateutil.readthedocs.io/en/stable/rrule.html`
  - `rrulestr(rule_string, dtstart=dt)` parses RFC 5545 RRULE strings
  - `.after(dt)` returns the next occurrence strictly after `dt`
  - Handles: `FREQ=WEEKLY;BYDAY=SA`, `FREQ=MONTHLY;BYMONTHDAY=6`, `FREQ=MONTHLY;BYDAY=1FR`, `FREQ=MONTHLY;BYDAY=-1MO`, `FREQ=WEEKLY;INTERVAL=2;BYDAY=TU`

### Project Conventions

- Standards referenced: `python.instructions.md`, `unit-tests.instructions.md`, `integration-tests.instructions.md`, `fastapi-transaction-patterns.instructions.md`, `test-driven-development.instructions.md`
- Instructions followed: TDD (RED→GREEN→REFACTOR), no permission bypass without explicit auth, deferred publish pattern, `DMFormats` for all bot DM text

## Key Discoveries

### Library

`python-dateutil` (version 2.9.0.post0) is already installed as a transitive dependency of `icalendar~=6.0.0`. **No new dependencies required.**

Verified working:

```python
from dateutil.rrule import rrulestr
import datetime

dtstart = datetime.datetime(2026, 6, 6, 19, 0)
rrulestr('FREQ=WEEKLY;BYDAY=SA', dtstart=dtstart).after(dtstart)
# → datetime.datetime(2026, 6, 13, 19, 0)
rrulestr('FREQ=MONTHLY;BYDAY=1FR', dtstart=dtstart).after(dtstart)
# → datetime.datetime(2026, 7, 3, 19, 0)
```

### Zombie-Game Prevention Mechanism

The zombie check belongs in `_handle_status_transition_due` (the IN_PROGRESS handler), using the discriminator `message_id is None AND recur_rule is not None`. This is precise: it only fires for recurrence clones that were never announced. Regular games with broken announcements are not affected.

`post_at = None` is the correct sentinel for the pending recurrence clone:

- The announcement loop ignores it entirely (requires `post_at IS NOT NULL`)
- No race condition between the loop and the transition handler is possible
- No changes to `AnnouncementLoop` are needed
- No relaxation of `post_at < scheduled_at` validation is needed

### API Confirmation Path

`PUT /{game_id}` with `clear_post_at=true` already:

1. Sets `post_at = utcnow()`
2. Sends `NOTIFY game_announcement_changed`
3. Wakes the announcement loop
4. Loop announces the game

This is the exact mechanism needed for host confirmation via the frontend/API, bypassing the need to click a Discord button for e2e testing.

### Recurrence State Machine

```
Game COMPLETES (status_transition_due fires)
  ↓ _handle_post_transition_actions
  ↓ recur_rule is not None?
  ├─ No → existing behavior (rewards DM only)
  └─ Yes →
      next_at = rrulestr(game.recur_rule, dtstart=game.scheduled_at).after(game.scheduled_at)
      clone = _system_clone_for_recurrence(game, next_at)
        → post_at=None, recur_rule copied, player carryover=YES, no GAME_CREATED event
      host DM with RecurrenceConfirmationView buttons

RecurrenceConfirmationView (Discord button):
  Confirm → game.post_at = utcnow(), NOTIFY → loop announces
  Decline → cancel game

PUT /{clone_id} clear_post_at=true (API/frontend path):
  → same effect as Confirm button

game_status_transition_due fires for clone (IN_PROGRESS):
  → game.message_id is None AND game.recur_rule is not None
  → cancel game (host did not respond in time)
```

### Frontend RRULE UI

A `RecurrenceSelector` component, following the same `FormControl` + `Select` + conditional `TextField` pattern as the existing `DurationSelector` component.

**Frequency selector** (top-level `Select`):

- No recurrence → `recur_rule = null`
- Every N weeks on same day → reveals a numeric stepper (1–8)
- Every N months on same date → reveals a numeric stepper (1–12)
- Every N months on same weekday position (e.g. every 2 months on the first Friday) → reveals a numeric stepper (1–12)

**RRULE computed from `scheduledAt`** (all day-of-week and ordinal values derived automatically):

| Selection                      | Computed RRULE                               |
| ------------------------------ | -------------------------------------------- |
| Every N weeks                  | `FREQ=WEEKLY;INTERVAL={N};BYDAY={DOW}`       |
| Every N months on same date    | `FREQ=MONTHLY;INTERVAL={N};BYMONTHDAY={DAY}` |
| Every N months on same weekday | `FREQ=MONTHLY;INTERVAL={N};BYDAY={ORD}{DOW}` |

Where `DOW` = two-letter day abbreviation (MO/TU/WE/TH/FR/SA/SU), `DAY` = day-of-month (1–28), `ORD` = weekday ordinal (+1/+2/+3/+4/-1 for last).

The interval stepper (`TextField type="number"`, min=1, max depends on frequency) appears inline below the frequency dropdown when any recurring option is selected, identical to `DurationSelector`'s custom-hours field.

`recur_rule` is stored as a plain string on `GameSession`; frontend sends it as a form field on create/update.

## Key Discoveries (continued)

### Reminders and Unconfirmed Recurrence Clones

`setup_game_schedules()` (which creates both join-notification and reminder `NotificationSchedule` rows) is called **only from `AnnouncementLoop._announce()`**, after the Discord message is posted. It is never called at clone creation time when the game is unconfirmed (`post_at=None`).

Therefore: **no `NotificationSchedule` rows exist for a recurrence clone until the host confirms**. The reminder daemon has nothing to fire. No additional `message_id` guard is needed in the reminder handler.

`_validate_game_for_reminder` already skips games that have started or are not `SCHEDULED`, but the primary protection is structural: rows simply do not exist until `_announce()` creates them.

The implementation of `_system_clone_for_recurrence` must **not** call `_setup_game_schedules()` — consistent with how `_persist_and_publish()` skips it for deferred games.

## Known Limitations

### DST and Timezone Shifts

All internal timestamps are stored as naive UTC. `rrulestr(rule, dtstart=game.scheduled_at).after(game.scheduled_at)` operates entirely in UTC, so a game stored at `23:00 UTC` (7pm US Eastern summer) will always produce the next occurrence at `23:00 UTC`. When DST ends, `23:00 UTC` becomes `6pm` local time — the game shifts silently by one hour.

For guilds that coordinate in UTC this is not an issue. For guilds that mean "every Saturday at 7pm local time" it is a surprise.

The correct fix is a `recur_timezone: str | None` column (IANA tz name, e.g. `"America/New_York"`) and passing a timezone-aware `dtstart` to `rrulestr`:

```python
from zoneinfo import ZoneInfo  # stdlib Python 3.9+
tz = ZoneInfo(game.recur_timezone)
dtstart = game.scheduled_at.replace(tzinfo=ZoneInfo("UTC")).astimezone(tz)
next_at_utc = rrulestr(game.recur_rule, dtstart=dtstart).after(dtstart) \
                  .astimezone(ZoneInfo("UTC")).replace(tzinfo=None)
```

This is deferred to v2. V1 documents the UTC-only behavior and the host confirmation step (which occurs before the next game is announced) provides a natural opportunity to notice and correct any off-by-one-hour issue manually.

## Recommended Approach

### Schema Changes (1 migration, 1 new column)

Add `recur_rule: Mapped[str | None] = mapped_column(String(200), nullable=True)` to `GameSession`.

No boolean flag needed. No new tables needed.

### New Internal Clone Path

`GameService._system_clone_for_recurrence(source_game, next_at)`:

- Copies all source fields including `recur_rule` (chain continues)
- Sets `post_at = None` (invisible to announcement loop)
- Sets `message_id = None`
- Sets `status = SCHEDULED`, `rewards = None`
- Calls `_create_game_status_schedules()` (status transitions set up immediately)
- Does **not** call `_setup_game_schedules()` (reminders deferred until announcement)
- Does **not** call `_publish_game_created()` (no Discord announcement yet)
- Carries over confirmed players (carryover=YES by default)
- Does **not** require `CurrentUser` or permission check (system-initiated)

### New Bot Components

**`DMFormats.recurrence_confirmation(game_title, next_at_unix)`** in `shared/message_formats.py`:

```
🔁 **{game_title}** has ended! The next session is scheduled for <t:{next_at_unix}:F>.

Confirm to announce it to players, or decline to cancel it. If you don't respond before the game starts, it will be automatically cancelled.
```

**`RecurrenceConfirmationView`** in `services/bot/views/`:

- Confirm button → `game.post_at = utcnow()`, commit, `NOTIFY game_announcement_changed`
- Decline button → cancel game (existing cancel flow)
- Simpler than `CloneConfirmationView`: no `ParticipantActionSchedule` involvement

**`_handle_recurrence_confirmation`** in `services/bot/events/handlers.py`:

- New `notification_type = "recurrence_confirmation"` branch in `_handle_notification_due`
- Sends host DM with `RecurrenceConfirmationView`

### Modified Components

**`_handle_post_transition_actions`** additions:

```python
if target_status == GameStatus.COMPLETED.value and game.recur_rule:
    next_at = rrulestr(game.recur_rule, dtstart=game.scheduled_at).after(game.scheduled_at)
    if next_at:
        clone = await self._system_clone_for_recurrence(game, next_at)
        # schedule recurrence_confirmation notification for host
        # (fires via notification_schedule daemon → bot DM)
```

**`_handle_status_transition_due`** zombie check (before transitioning to IN_PROGRESS):

```python
if target_status == GameStatus.IN_PROGRESS.value \
        and game.message_id is None \
        and game.recur_rule is not None:
    # Host did not confirm — cancel silently
    await self._cancel_unconfirmed_recurrence(game)
    return
```

**`clone_game()`** API path:

- Copy `recur_rule` from source to clone (recurrence propagates through manual clones too)

**`PUT /{game_id}`** (frontend confirmation path):

- No changes needed — `clear_post_at=true` already does exactly what's needed

## Implementation Guidance

- **Objectives**: Add recurring game support with zombie-game prevention via host DM confirmation
- **Key Tasks**:
  1. Alembic migration: add `recur_rule VARCHAR(200) NULL` to `game_sessions`
  2. Update `GameSession` model: add `recur_rule` field
  3. Update `CloneGameRequest` / `clone_game()`: propagate `recur_rule`
  4. Add `GameService._system_clone_for_recurrence()`
  5. Add `DMFormats.recurrence_confirmation()`
  6. Add `RecurrenceConfirmationView` (Confirm/Decline buttons)
  7. Add `_handle_recurrence_confirmation` handler + notification schedule entry
  8. Modify `_handle_post_transition_actions`: trigger recurrence clone at COMPLETED
  9. Modify `_handle_status_transition_due`: zombie cancel at IN_PROGRESS
  10. Expose `recur_rule` in `GameCreateRequest`, `GameUpdateRequest`, `GameResponse` schemas
  11. Frontend: preset dropdown RRULE builder on create/edit game form
- **Dependencies**: `python-dateutil` (already installed), no new pip packages
- **Success Criteria**:
  - Game with `recur_rule` set → after COMPLETED, clone exists with `post_at=NULL`, host receives DM
  - Host confirms via Discord button → clone announced immediately
  - Host confirms via `PUT clear_post_at=true` → clone announced immediately (e2e testable)
  - Host ignores → clone cancelled when IN_PROGRESS transition fires
  - Host declines → clone cancelled immediately
  - Clone inherits `recur_rule` → chain continues each occurrence
  - Game without `recur_rule` → no change to existing behavior

## Test Plan

### Unit Tests (TDD: write failing tests first)

**`tests/unit/shared/test_message_formats.py`** (new tests):

- `test_recurrence_confirmation_format_contains_title`: DMFormats.recurrence_confirmation includes game title
- `test_recurrence_confirmation_format_contains_timestamp`: includes Discord timestamp

**`tests/unit/services/test_clone_game.py`** (extend):

- `test_clone_game_propagates_recur_rule`: `clone_game()` copies `recur_rule` from source

**`tests/unit/services/test_system_clone_for_recurrence.py`** (new):

- `test_system_clone_sets_post_at_none`: `_system_clone_for_recurrence()` creates game with `post_at=None`
- `test_system_clone_copies_recur_rule`: clone inherits source `recur_rule`
- `test_system_clone_carries_over_confirmed_players`: confirmed players copied to clone
- `test_system_clone_does_not_publish_game_created`: no `GAME_CREATED` event published
- `test_system_clone_creates_status_schedules`: IN_PROGRESS + COMPLETED schedules created

**`tests/unit/services/bot/events/test_handlers_recurrence.py`** (new):

- `test_post_transition_triggers_recurrence_clone_when_recur_rule_set`: at COMPLETED, clone created and host DM scheduled
- `test_post_transition_skips_recurrence_when_no_recur_rule`: no clone when `recur_rule=None`
- `test_in_progress_transition_cancels_unannounced_recurrence`: zombie clone cancelled when `message_id=None AND recur_rule is not None`
- `test_in_progress_transition_proceeds_for_announced_recurrence`: normal game with `recur_rule` set proceeds normally once announced
- `test_in_progress_transition_proceeds_for_regular_game_no_announce`: regular game without `recur_rule` and `message_id=None` is NOT cancelled (guards against false positive)

**`tests/unit/services/bot/views/test_recurrence_confirmation_view.py`** (new):

- `test_confirm_sets_post_at_to_now`: Confirm callback sets `post_at` to approximately now
- `test_confirm_sends_pg_notify`: Confirm callback sends `game_announcement_changed` NOTIFY
- `test_decline_cancels_game`: Decline callback cancels the game

### Integration Tests

**`tests/integration/test_recurrence_clone.py`** (new):

- `test_recurrence_clone_created_with_null_post_at`: after manual status → COMPLETED via API, game with `recur_rule` gets a clone with `post_at=NULL` in DB (inject COMPLETED transition via direct DB update to avoid waiting)
- `test_recurrence_clone_invisible_to_players`: clone with `post_at=NULL` does not appear in `GET /api/v1/games` for non-host user
- `test_recurrence_clone_visible_to_host`: clone appears in host's game list
- `test_clear_post_at_announces_recurrence_clone`: `PUT /{clone_id}` with `clear_post_at=true` → `post_at` updated, `NOTIFY` sent (DB-level verification)
- `test_zombie_clone_cancelled_on_in_progress`: clone with `post_at=NULL` and `recur_rule` set is cancelled when its IN_PROGRESS transition fires (inject transition via direct scheduler invocation)
- `test_recur_rule_stored_and_returned`: `POST /api/v1/games` with `recur_rule` field → `GET /api/v1/games/{id}` returns it

### E2E Tests

**`tests/e2e/test_recurring_game.py`** (new — uses real stack, real Discord):

```
test_recurring_game_host_confirms_via_api:
  1. Create game with recur_rule="FREQ=WEEKLY;BYDAY={today_dow}" scheduled 2min from now with 1min duration
  2. Wait for COMPLETED status (via wait_for_db_condition, ~3min)
  3. Assert recurrence clone exists in DB with post_at=NULL, message_id=NULL
  4. Assert clone NOT visible to Player A (GET /api/v1/games)
  5. Admin calls PUT /{clone_id} clear_post_at=true
  6. Wait for clone message_id to become non-NULL (wait_for_game_message_id, 60s timeout)
  7. Assert Discord message posted (message_id set)
  8. Assert Player A can now see the clone in GET /api/v1/games

test_recurring_game_zombie_cancelled_when_unconfirmed:
  1. Create game with recur_rule set, scheduled 2min from now with 1min duration
  2. Wait for COMPLETED → clone created with post_at=NULL
  3. Do NOT confirm (do not call clear_post_at)
  4. Wait for clone's scheduled_at to arrive (clone scheduled 1 week out by default,
     so override: create clone directly in DB with scheduled_at=2min, recur_rule set, post_at=NULL)
  5. Wait for IN_PROGRESS transition to fire on clone
  6. Assert clone status=CANCELLED in DB
  7. Assert no Discord message posted for clone (message_id=NULL)

test_recurring_game_host_confirms_via_discord_button:
  NOTE: Bot test users cannot click Discord UI buttons. This test is intentionally
  omitted from the automated e2e suite. Manual verification is required for the
  Discord button path. The API/clear_post_at path above covers the same code path
  in RecurrenceConfirmationView._confirm_callback.
```

**Timeout guidance for e2e**:

- `test_recurring_game_host_confirms_via_api`: ~4-5 minutes (2min to COMPLETED + 30s processing + 60s announcement)
- `test_recurring_game_zombie_cancelled_when_unconfirmed`: ~4-5 minutes
- Use `@pytest.mark.timeout(360)` for both tests
- Use `tee` output capture: `scripts/run-e2e-tests.sh |& tee output-e2e-recurrence.txt`
