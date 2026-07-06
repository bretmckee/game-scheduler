<!-- markdownlint-disable-file -->

# Task Details: Remove Scheduler Service

## Research Reference

**Source Research**: #file:../research/20260706-01-remove-scheduler-research.md

---

## Phase 1: Move event builders to shared/

### Task 1.1: Create `shared/services/event_builders.py`

Create `shared/services/event_builders.py` by copying the content of `services/scheduler/event_builders.py` verbatim (the content already imports only from `shared.models`, so no other changes are needed).

- **Files**:
  - `shared/services/event_builders.py` — new file, copy of `services/scheduler/event_builders.py`
- **Success**:
  - `from shared.services.event_builders import build_notification_event, build_status_transition_event` resolves
  - `uv run mypy shared/` passes on the new file
- **Research References**:
  - #file:../research/20260706-01-remove-scheduler-research.md (Lines 30-45) — event builder content and dependencies
- **Dependencies**:
  - None

### Task 1.2: Create `shared/services/participant_action_event_builder.py`

Create `shared/services/participant_action_event_builder.py` by copying the content of `services/scheduler/participant_action_event_builder.py` verbatim.

- **Files**:
  - `shared/services/participant_action_event_builder.py` — new file, copy of `services/scheduler/participant_action_event_builder.py`
- **Success**:
  - `from shared.services.participant_action_event_builder import build_participant_action_event` resolves
  - `uv run mypy shared/` passes on the new file
- **Research References**:
  - #file:../research/20260706-01-remove-scheduler-research.md (Lines 27-29) — participant action event builder location
- **Dependencies**:
  - Task 1.1 (establishes pattern)

### Task 1.3: Update `scheduler_daemon_wrapper.py` and unit tests; delete originals

Update `services/scheduler/scheduler_daemon_wrapper.py` to replace the two relative imports:

```python
# Before
from .event_builders import build_notification_event, build_status_transition_event
from .participant_action_event_builder import build_participant_action_event

# After
from shared.services.event_builders import build_notification_event, build_status_transition_event
from shared.services.participant_action_event_builder import build_participant_action_event
```

Update `tests/unit/services/scheduler/test_event_builders.py` line 27:

```python
# Before
from services.scheduler.event_builders import (
    build_notification_event,
    build_status_transition_event,
)
# After
from shared.services.event_builders import (
    build_notification_event,
    build_status_transition_event,
)
```

Update `tests/unit/services/test_participant_action_event_builder.py` line 26:

```python
# Before
from services.scheduler.participant_action_event_builder import (
# After
from shared.services.participant_action_event_builder import (
```

Delete:

- `services/scheduler/event_builders.py`
- `services/scheduler/participant_action_event_builder.py`

- **Files**:
  - `services/scheduler/scheduler_daemon_wrapper.py` — updated imports
  - `tests/unit/services/scheduler/test_event_builders.py` — updated import path
  - `tests/unit/services/test_participant_action_event_builder.py` — updated import path
  - `services/scheduler/event_builders.py` — deleted
  - `services/scheduler/participant_action_event_builder.py` — deleted
- **Success**:
  - `uv run pytest tests/unit` passes
  - `uv run mypy shared/ services/` passes
- **Research References**:
  - #file:../research/20260706-01-remove-scheduler-research.md (Lines 175-195) — implementation guidance on moving event builders
- **Dependencies**:
  - Tasks 1.1 and 1.2 complete

---

## Phase 2: RED — SchedulerLoop stub + xfail unit tests

### Task 2.1: Create `services/bot/scheduler_loop.py` stub

Create `services/bot/scheduler_loop.py` with a minimal stub class so the test file can import it without `ImportError`:

```python
"""Async scheduler loop running inside the bot service."""
from __future__ import annotations

from collections.abc import Callable
from typing import Any


class SchedulerLoop:
    """Async replacement for SchedulerDaemon — one per schedule table."""

    def __init__(
        self,
        db_url: str,
        notify_channel: str,
        model_class: type,
        time_field: str,
        status_field: str,
        event_builder: Callable[..., Any],
        max_timeout: int = 900,
    ) -> None:
        raise NotImplementedError

    async def run(self) -> None:
        raise NotImplementedError
```

- **Files**:
  - `services/bot/scheduler_loop.py` — new file, stub only
- **Success**:
  - `from services.bot.scheduler_loop import SchedulerLoop` resolves
  - `uv run pytest tests/unit` still passes (no new test file yet)
- **Research References**:
  - #file:../research/20260706-01-remove-scheduler-research.md (Lines 96-130) — SchedulerLoop constructor signature and run() outline
- **Dependencies**:
  - Phase 1 complete

### Task 2.2: Create `tests/unit/services/bot/test_scheduler_loop.py` with xfail tests

Create `tests/unit/services/bot/test_scheduler_loop.py` covering the following behaviours (all marked `@pytest.mark.xfail(strict=True, reason="SchedulerLoop not yet implemented")`):

1. **Construction** — `SchedulerLoop` stores all seven constructor params without raising
2. **`_process_item` writes BotActionQueue row** — given a due model instance, calls `event_builder(item)`, adds the returned `BotActionQueue` to the session, and commits
3. **`_process_item` marks status_field True** — the model instance has `status_field=True` after `_process_item`
4. **`_process_item` is atomic** — write and mark happen in a single `db.commit()` (commit called exactly once)
5. **`run` skips when item is not due** — does not call `_process_item` when `time_field` is in the future
6. **`run` calls `_process_item` when item is due** — calls `_process_item` when `time_field` is in the past
7. **`run` handles no items** — does not raise when no schedule rows exist

Use `AsyncMock` / `MagicMock` for database sessions and asyncpg connections. Import models from `shared.models`.

- **Files**:
  - `tests/unit/services/bot/test_scheduler_loop.py` — new file, xfail tests
- **Success**:
  - `uv run pytest tests/unit` passes (xfail tests count as expected failures)
- **Research References**:
  - #file:../research/20260706-01-remove-scheduler-research.md (Lines 96-130) — algorithm: query next item, check due, write row + mark executed, commit
- **Dependencies**:
  - Task 2.1 (stub must exist for import to succeed)

---

## Phase 3: GREEN — Implement SchedulerLoop

### Task 3.1: Implement `SchedulerLoop` and lift xfail markers

Implement `SchedulerLoop` in `services/bot/scheduler_loop.py` following the algorithm from the research:

1. `__init__` stores all params; initialises `self._notified = asyncio.Event()`
2. `run()` opens an asyncpg connection, calls `await conn.add_listener(self.notify_channel, self._on_notify)`, then enters the loop
3. Loop body:
   a. `item = await self._get_next_due_item()` — async sqlalchemy query for the earliest unprocessed row (status_field is False) ordered by time_field ASC, limit 1
   b. If `item` and `is_due(item)`: call `await self._process_item(item)`
   c. Else: compute `wait = time_until_due(item) or self.max_timeout`; `contextlib.suppress(asyncio.TimeoutError)`: `await asyncio.wait_for(self._notified.wait(), timeout=wait)`; `self._notified.clear()`
4. `_process_item(item)` opens an async DB session, calls `event_builder(item)`, `db.add(queue_row)`, sets `setattr(item, self.status_field, True)`, `await db.commit()`
5. `_on_notify(conn, pid, channel, payload)` sets `self._notified`
6. Helper `is_due(item)` returns `getattr(item, self.time_field) <= utc_now()`
7. Helper `time_until_due(item)` returns seconds until due (or `None` if no item)

Use `shared.database.get_db_session` for async sessions. Use `asyncpg.connect` for the NOTIFY listener (strip `postgresql+asyncpg://` → `postgresql://` as shown in research). Import `utc_now` from `shared.models.base`.

Remove `@pytest.mark.xfail` from tests that now pass. Any test that remains genuinely untestable keeps its marker with an updated reason.

- **Files**:
  - `services/bot/scheduler_loop.py` — full implementation replacing stub
  - `tests/unit/services/bot/test_scheduler_loop.py` — xfail markers removed where tests now pass
- **Success**:
  - `uv run pytest tests/unit` passes (no unexpected xfail)
  - `uv run mypy shared/ services/` passes
- **Research References**:
  - #file:../research/20260706-01-remove-scheduler-research.md (Lines 96-155) — full SchedulerLoop algorithm and code sketch
- **Dependencies**:
  - Phase 2 complete

### Task 3.2: Create `tests/integration/test_scheduler_loop.py`

Create `tests/integration/test_scheduler_loop.py` with three integration tests — one per schedule table — that directly exercise `SchedulerLoop` against real PostgreSQL. The bot container does not run SchedulerLoop in integration test mode (`BOT_SKIP_STARTUP=1` skips `on_ready`), so these tests replace the scheduler container tests that are deleted in Phase 5.

**Test pattern for each table:**

1. Insert a due schedule row via `admin_db_sync` (set the time field to `utcnow() - 1 minute` and the status field to `False`/`0`)
2. Instantiate `SchedulerLoop` with the `bot_db_url` fixture, the correct channel/model/field/builder args
3. Run `await asyncio.wait_for(scheduler_loop.run(), timeout=5.0)` wrapped in `contextlib.suppress(asyncio.TimeoutError)` — the item is already due so the first loop iteration processes it immediately without waiting for NOTIFY
4. Assert via `admin_db_sync` that a `bot_action_queue` row now exists with the expected `action_type` and `game_id`
5. Assert via `admin_db_sync` that the schedule row has `status_field=True` / `processed=True`

**Three test cases:**

- `test_notification_schedule_due_item_enqueued`: `NotificationSchedule` row → `bot_action_queue.action_type = "notification_due"`, `notification_schedule.sent = True`
- `test_status_transition_due_item_enqueued`: `GameStatusSchedule` row → `bot_action_queue.action_type = "status_transition_due"`, `game_status_schedule.executed = True`
- `test_participant_action_due_item_enqueued`: `ParticipantActionSchedule` row → `bot_action_queue.action_type = "participant_drop_due"`, `participant_action_schedule.processed = True`

Use `pytestmark = pytest.mark.integration`. Import `SchedulerLoop` from `services.bot.scheduler_loop`. Import event builders from `shared.services.*`. Reuse `test_game_environment` fixture for the `game_id` foreign key.

Each test cleans up its own inserted rows (delete from `bot_action_queue` and the schedule table) in a `finally` block or via a fixture, so tests remain independent.

- **Files**:
  - `tests/integration/test_scheduler_loop.py` — new file, three integration tests
- **Success**:
  - Tests pass when run inside the integration Docker environment (`scripts/run-integration-tests.sh`)
  - Each test verifies a different schedule path (notification, status transition, participant action)
- **Research References**:
  - #file:../research/20260706-01-remove-scheduler-research.md (Lines 96-130) — schedule table names, field names, action_type values
- **Dependencies**:
  - Task 3.1 complete (SchedulerLoop implemented)
  - Phase 1 complete (event builders in `shared.services.*`)

---

## Phase 4: Wire SchedulerLoop into bot.py

### Task 4.1: Import and start three `SchedulerLoop` tasks in `bot.py` `on_ready`

Add to `services/bot/bot.py`:

**New imports** (alongside existing bot imports):

```python
from services.bot.scheduler_loop import SchedulerLoop
from shared.models import GameStatusSchedule, NotificationSchedule, ParticipantActionSchedule
from shared.services.event_builders import build_notification_event, build_status_transition_event
from shared.services.participant_action_event_builder import build_participant_action_event
```

**In `on_ready`**, after the existing `_announcement_loop_started` guard block, add:

```python
if not hasattr(self, "_scheduler_loops_started"):
    self._scheduler_loops_started = True
    asyncio.create_task(
        SchedulerLoop(
            db_url=self.config.database_url,
            notify_channel="notification_schedule_changed",
            model_class=NotificationSchedule,
            time_field="notification_time",
            status_field="sent",
            event_builder=build_notification_event,
        ).run()
    )
    asyncio.create_task(
        SchedulerLoop(
            db_url=self.config.database_url,
            notify_channel="game_status_schedule_changed",
            model_class=GameStatusSchedule,
            time_field="transition_time",
            status_field="executed",
            event_builder=build_status_transition_event,
        ).run()
    )
    asyncio.create_task(
        SchedulerLoop(
            db_url=self.config.database_url,
            notify_channel="participant_action_schedule_changed",
            model_class=ParticipantActionSchedule,
            time_field="action_time",
            status_field="processed",
            event_builder=build_participant_action_event,
        ).run()
    )
    logger.info("Started scheduler loop tasks")
```

- **Files**:
  - `services/bot/bot.py` — add imports and three `SchedulerLoop` create_task calls
- **Success**:
  - `uv run mypy shared/ services/` passes
  - Bot starts without error (scheduler loop tasks created)
- **Research References**:
  - #file:../research/20260706-01-remove-scheduler-research.md (Lines 138-155) — three-instance wiring pattern from research code sketch
- **Dependencies**:
  - Phase 3 complete

### Task 4.2: Add unit tests for SchedulerLoop wiring in `test_bot.py`

Add a test to `tests/unit/services/bot/test_bot.py` verifying that `on_ready` creates three `SchedulerLoop` tasks when called the first time and does not create them on a second call.

Use `patch("services.bot.bot.SchedulerLoop")` and `patch("services.bot.bot.asyncio.create_task")`. Assert that `SchedulerLoop` is instantiated exactly three times with the correct `notify_channel` values (`notification_schedule_changed`, `game_status_schedule_changed`, `participant_action_schedule_changed`).

- **Files**:
  - `tests/unit/services/bot/test_bot.py` — new test class or test method for SchedulerLoop wiring
- **Success**:
  - `uv run pytest tests/unit` passes
- **Research References**:
  - #file:../research/20260706-01-remove-scheduler-research.md (Lines 138-155) — three channel names and model classes
- **Dependencies**:
  - Task 4.1 complete

---

## Phase 5: Delete scheduler service

### Task 5.1: Move `PostgresNotificationListener` to `tests/shared/sync_pg_listener.py`

Create `tests/shared/sync_pg_listener.py` containing the content of `services/scheduler/postgres_listener.py`. This file is only needed by integration tests for synchronous LISTEN/NOTIFY verification.

Update `tests/integration/test_message_refresh_queue.py` line 37:

```python
# Before
from services.scheduler.postgres_listener import PostgresNotificationListener
# After
from tests.shared.sync_pg_listener import PostgresNotificationListener
```

- **Files**:
  - `tests/shared/sync_pg_listener.py` — new file, content from `services/scheduler/postgres_listener.py`
  - `tests/integration/test_message_refresh_queue.py` — import path updated
- **Success**:
  - `uv run pytest tests/unit` still passes
  - The class is importable by the integration test runner inside Docker
- **Research References**:
  - #file:../research/20260706-01-remove-scheduler-research.md (Lines 19-21) — postgres_listener description
- **Dependencies**:
  - Phase 4 complete

### Task 5.2: Delete scheduler unit tests and integration tests for scheduler container

Delete the entire `tests/unit/services/scheduler/` directory (7 files: `test_daemon_runner_run.py`, `test_daemon_runner_signals.py`, `test_event_builders.py`, `test_generic_scheduler_daemon.py`, `test_postgres_listener.py`, `test_scheduler_daemon_wrapper.py`, `test_scheduler_status_transitions.py` plus `__init__.py`).

Delete these integration test files (they test the running scheduler container; the behaviour is now covered by `test_scheduler_loop.py` unit tests and existing e2e tests):

- `tests/integration/test_notification_daemon.py`
- `tests/integration/test_status_transitions.py`
- `tests/integration/test_participant_action_daemon.py`
- `tests/integration/test_clone_confirmation_notification.py`

Also delete:

- `tests/unit/services/test_participant_action_event_builder.py` — imports `shared.services.participant_action_event_builder`; will be replaced by tests already in `test_scheduler_loop.py` for the event builder behaviour

Wait — `tests/unit/services/test_participant_action_event_builder.py` was updated in Phase 1 to import from `shared.services.*`, so it still tests event builder logic independently. Keep it. Do NOT delete it.

- **Files**:
  - `tests/unit/services/scheduler/` — entire directory deleted
  - `tests/integration/test_notification_daemon.py` — deleted
  - `tests/integration/test_status_transitions.py` — deleted
  - `tests/integration/test_participant_action_daemon.py` — deleted
  - `tests/integration/test_clone_confirmation_notification.py` — deleted
- **Success**:
  - No file under `tests/` imports from `services.scheduler`
  - `uv run pytest tests/unit` passes
- **Research References**:
  - #file:../research/20260706-01-remove-scheduler-research.md (Lines 160-180) — which tests are scheduler-container-specific
- **Dependencies**:
  - Task 5.1 complete

### Task 5.3: Delete `services/scheduler/` directory

Delete the entire `services/scheduler/` directory. At this point no production code or test imports from it.

Verify before deleting: `grep -r "from services.scheduler" services/ tests/` returns no matches.

- **Files**:
  - `services/scheduler/` — entire directory deleted
- **Success**:
  - `services/scheduler/` does not exist
  - `uv run pytest tests/unit` passes
  - `uv run mypy shared/ services/` passes
- **Research References**:
  - #file:../research/20260706-01-remove-scheduler-research.md (Lines 186-188) — delete scheduler directory
- **Dependencies**:
  - Tasks 5.1 and 5.2 complete

### Task 5.4: Remove `scheduler` from all compose files and delete `scheduler.Dockerfile`

**`compose.yaml`**: remove the `scheduler:` service stanza (lines 242-289 approx).

**`compose.int.yaml`**:

- Remove the `scheduler:` service stanza
- Remove `scheduler: condition: service_started` from the `system-ready` `depends_on` block

**`compose.e2e.yaml`**:

- Remove the `scheduler:` service stanza
- Remove `scheduler: condition: service_started` (or similar) from `system-ready` `depends_on`

**`compose.prod.yaml`**: remove the `scheduler:` service stanza.

**`compose.staging.yaml`**: remove the `scheduler:` service stanza.

Delete `docker/scheduler.Dockerfile`.

Do NOT remove `psycopg2-binary` from `pyproject.toml`.

- **Files**:
  - `compose.yaml` — scheduler stanza removed
  - `compose.int.yaml` — scheduler stanza and system-ready dependency removed
  - `compose.e2e.yaml` — scheduler stanza and system-ready dependency removed
  - `compose.prod.yaml` — scheduler stanza removed
  - `compose.staging.yaml` — scheduler stanza removed
  - `docker/scheduler.Dockerfile` — deleted
- **Success**:
  - `grep -r "scheduler" compose*.yaml` returns only comments (if any)
  - `docker/scheduler.Dockerfile` does not exist
  - `uv run pytest tests/unit` passes
  - Integration tests pass (run `scripts/run-integration-tests.sh`)
- **Research References**:
  - #file:../research/20260706-01-remove-scheduler-research.md (Lines 186-195) — list of compose files to update
- **Dependencies**:
  - Task 5.3 complete

---

## Dependencies

- asyncpg (already a bot dependency)
- SQLAlchemy async (already a bot dependency)
- `shared.models.NotificationSchedule`, `GameStatusSchedule`, `ParticipantActionSchedule` (already in `shared.models`)

## Success Criteria

- `services/scheduler/` does not exist
- `docker/scheduler.Dockerfile` does not exist
- No compose file references the scheduler service
- `uv run pytest tests/unit` passes
- `uv run mypy shared/ services/` passes
- `scripts/run-integration-tests.sh` passes
- `scripts/run-e2e-tests.sh` passes (bot handles schedule processing end-to-end)
