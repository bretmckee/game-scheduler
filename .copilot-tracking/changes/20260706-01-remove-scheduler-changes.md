<!-- markdownlint-disable-file -->

# Changes: Remove Scheduler Service

## Overview

Replace the standalone scheduler container with `SchedulerLoop` asyncio tasks running inside the bot service, then delete the scheduler service entirely.

## Status

In Progress

---

## Phase 1: Move event builders to shared/

### Added

- `shared/services/event_builders.py` — verbatim copy of `services/scheduler/event_builders.py`; provides `build_notification_event` and `build_status_transition_event` from shared package
- `shared/services/participant_action_event_builder.py` — verbatim copy of `services/scheduler/participant_action_event_builder.py`; provides `build_participant_action_event` from shared package

### Modified

- `services/scheduler/scheduler_daemon_wrapper.py` — updated two relative imports (`from .event_builders` and `from .participant_action_event_builder`) to use `shared.services.*` absolute paths
- `tests/unit/services/scheduler/test_event_builders.py` — updated import from `services.scheduler.event_builders` to `shared.services.event_builders`
- `tests/unit/services/test_participant_action_event_builder.py` — updated import from `services.scheduler.participant_action_event_builder` to `shared.services.participant_action_event_builder`
- `docker/scheduler.Dockerfile` — **outside plan**: removed two `COPY` lines for `event_builders.py` and `participant_action_event_builder.py` (now deleted files); the shared/ directory copy already includes the moved files

### Removed

- `services/scheduler/event_builders.py` — deleted after moving to `shared/services/`
- `services/scheduler/participant_action_event_builder.py` — deleted after moving to `shared/services/`

---

## Phase 2: RED — SchedulerLoop stub + xfail unit tests

### Added

- `services/bot/scheduler_loop.py` — minimal stub with `SchedulerLoop.__init__` and `run()` both raising `NotImplementedError`; satisfies imports without providing any behaviour
- `tests/unit/services/bot/test_scheduler_loop.py` — 7 xfail tests covering construction, `_process_item` (writes queue row, marks status field, commits once), and `run` (skips when not due, calls `_process_item` when due, handles no items)

---

## Phase 3: GREEN — Implement SchedulerLoop

### Modified

- `services/bot/scheduler_loop.py` — full async implementation replacing the stub:
  - `__init__` stores all seven constructor params and initialises `self._notified = asyncio.Event()`
  - `run()` opens an asyncpg LISTEN connection and loops: query → process if due, else wait
  - `_process_item(item)` writes a BotActionQueue row and marks the schedule item processed in a single commit via `get_db_session()`
  - `_on_notify(conn, pid, channel, payload)` sets `self._notified`
  - `_get_next_due_item()` queries the earliest unprocessed row ordered by time_field ASC
  - `_is_due(item)` and `_time_until_due(item)` helpers using `utc_now()`
  - Added `await asyncio.sleep(0)` after `_process_item` for cooperative multitasking
- `tests/unit/services/bot/test_scheduler_loop.py` — lifted all 7 `@pytest.mark.xfail` markers; removed the Phase 2 stub test (`test_run_stub_raises_not_implemented`); added `mock_session.add = MagicMock()` to three `_process_item` test setups (SQLAlchemy `AsyncSession.add()` is synchronous)

### Added

- `tests/integration/test_scheduler_loop.py` — three integration tests exercising SchedulerLoop against real PostgreSQL: `test_notification_schedule_due_item_enqueued`, `test_status_transition_due_item_enqueued`, `test_participant_action_due_item_enqueued`
