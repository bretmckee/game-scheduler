<!-- markdownlint-disable-file -->

# Task Research Notes: Remove Scheduler Service

## Research Executed

### File Analysis

- `services/scheduler/generic_scheduler_daemon.py`
  - Pattern: query next unprocessed item; if due, call `event_builder(item)` to construct `BotActionQueue` row; `db.add(row)`, mark `status_field=True`, `db.commit()` atomically
  - Wait is bounded by `max_timeout` (default 900s) or time until next item
  - Wakes early via `PostgresNotificationListener.wait_for_notification()` (psycopg2 + `select()`)
  - Three daemon instances in `scheduler_daemon_wrapper.py`: notification, status-transition, participant-action
- `services/scheduler/event_builders.py` / `participant_action_event_builder.py`
  - Build `BotActionQueue(action_type=..., game_id=..., payload={...})` rows from schedule records
  - `build_notification_event` → `action_type="notification_due"`
  - `build_status_transition_event` → `action_type="status_transition_due"`
  - `build_participant_action_event` → `action_type="participant_drop_due"`
- `services/scheduler/postgres_listener.py`
  - Synchronous psycopg2 LISTEN using `select()` — scheduler-only; the bot uses asyncpg
- `services/bot/bot_action_listener.py`
  - `BotActionListener` — asyncpg LISTEN on `bot_action_queue_changed`; drains queue on NOTIFY; deletes row atomically with dispatch; already handles `notification_due`, `status_transition_due`, `participant_drop_due`
- `services/bot/bot.py`
  - Starts `BotActionListener` as an asyncio task in `on_ready` (alongside `MessageRefreshListener`, `AnnouncementLoop`)
  - Pattern: `asyncio.create_task(SomeListener(self.config.database_url, ...).start())`
- `services/bot/events/handlers.py`
  - `_handle_notification_due(data: dict)` — already callable with plain dict, no RabbitMQ wrapping
  - `_handle_status_transition_due(data: dict)` — same
  - `_handle_participant_drop_due(data: dict)` — same

### Code Search Results

- `psycopg2` usage in non-scheduler services
  - `services/init/database_users.py`, `services/init/verify_schema.py`, `services/init/wait_postgres.py` all import and use psycopg2 directly — it cannot be removed when the scheduler is deleted
- `compose.yaml` scheduler service
  - Environment: `DATABASE_URL`, `LOG_LEVEL`, OTEL vars only — `RABBITMQ_URL` already absent
- `bot_action_queue` action types in `BotActionListener._dispatch`
  - API flows: `game_created`, `game_cancelled`, `player_removed`, `send_dm`
  - Scheduler flows: `notification_due`, `status_transition_due`, `participant_drop_due`
  - All scheduler flows pass through `_build_handler_data(row)` which extracts payload fields into a `dict`

### Project Conventions

- Bot uses `asyncio.create_task(SomeClass(db_url, ...).start())` in `on_ready` for all background listeners
- asyncpg LISTEN pattern established in `MessageRefreshListener` and `BotActionListener`
- Schedule tables use `status_field=True` marking (not delete-on-process)

## Key Discoveries

### Current Data Flow (post-RabbitMQ removal)

```
Schedule table  ──NOTIFY──►  SchedulerDaemon (psycopg2 thread)
                              │ writes BotActionQueue row
                              │ marks schedule_row.status=True
                              │ db.commit() ──► NOTIFY bot_action_queue_changed
                              ▼
                          BotActionListener (asyncpg, bot process)
                              │ reads + deletes BotActionQueue row
                              │ _build_handler_data(row) → dict
                              ▼
                          EventHandlers._handle_*_due(data)
```

### RabbitMQ Removal Is Complete

All 9 phases of the RabbitMQ removal (`20260704-01`) are done. `shared/messaging/` is deleted. The scheduler already writes to `bot_action_queue` (not RabbitMQ). No prerequisite work remains.

### `bot_action_queue` Is Also Used by API Flows

The table is NOT scheduler-only. API flows (game_created, game_cancelled, player_removed, send_dm) write to it. It will survive scheduler removal regardless of which option is chosen below.

### `psycopg2` Cannot Be Removed

The `services/init/` service (database_users.py, verify_schema.py, wait_postgres.py) uses psycopg2 for synchronous setup tasks. Removing the scheduler does not change this.

### Handler Functions Accept Plain Dicts

`_handle_notification_due`, `_handle_status_transition_due`, and `_handle_participant_drop_due` all accept `dict[str, Any]`. The `_build_handler_data` function in `BotActionListener` translates `BotActionQueue` columns to this dict format. Either implementation option can call these handlers.

## Recommended Approach: Option B — Async Rewrite of Daemon as Bot Task

Keep `bot_action_queue` as the intermediary for scheduler-originated events. The `SchedulerLoop` is an asyncio rewrite of `SchedulerDaemon`: LISTEN on channel, query next due item, when due → write `BotActionQueue` row + mark `status_field=True` atomically. `BotActionListener` dispatches as it does today.

```python
class SchedulerLoop:
    """
    Async replacement for SchedulerDaemon — one per schedule table.

    Listens on notify_channel; on wake (or timeout), queries for next
    unexecuted item; when due, writes a BotActionQueue row and marks
    the schedule item processed in the same transaction.
    """

    def __init__(
        self,
        db_url: str,
        notify_channel: str,
        model_class: type,
        time_field: str,
        status_field: str,
        event_builder: Callable,
        max_timeout: int = 900,
    ) -> None: ...

    async def run(self) -> None:
        db_url = self._db_url.replace("postgresql+asyncpg://", "postgresql://")
        conn = await asyncpg.connect(db_url)
        await conn.add_listener(self.notify_channel, self._on_notify)
        while True:
            item = await self._get_next_due_item()
            if item and is_due(item):
                await self._process_item(item)  # write queue row + mark executed, commit
            else:
                wait = time_until_due(item) or self.max_timeout
                with contextlib.suppress(asyncio.TimeoutError):
                    await asyncio.wait_for(self._notified.wait(), timeout=wait)
                self._notified.clear()
```

Three instances started in `bot.py` `on_ready`, same pattern as `BotActionListener`:

```python
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
```

### Why Option B Over Option A

Option A calls `EventHandlers` directly from `SchedulerLoop`, bypassing `bot_action_queue` for scheduler flows.

|                             | Option A (direct call)                                                   | Option B (via queue)                                              |
| --------------------------- | ------------------------------------------------------------------------ | ----------------------------------------------------------------- |
| Latency                     | ~1 DB op                                                                 | ~3 DB ops (write, NOTIFY, read+delete)                            |
| Crash safety                | Weaker: mark-then-call; crash between the two loses the event            | Stronger: row survives crash until `BotActionListener` deletes it |
| Architectural consistency   | Two entry paths to handlers                                              | All events enter through `bot_action_queue`                       |
| Scope of change             | Larger: `SchedulerLoop` needs `EventHandlers` ref, data format alignment | Minimal: `event_builders.py` reused unchanged                     |
| `BotActionListener` changes | Remove 3 action-type cases from `_dispatch`                              | None                                                              |

Option A is a valid future refinement once Option B is validated in production. Taking Option B first preserves crash safety and reduces the surface of change.

## Addendum: Future Refactoring — Shared Schedule Base Class

Now that `SchedulerLoop` is implemented (Phase 3), a follow-on refactoring could eliminate the `time_field`, `status_field`, and `event_builder` constructor parameters entirely by unifying the three schedule models under a shared abstract base class.

### Why the Parameters Exist Now

The three schedule tables have different column names for the same conceptual fields:

| Model                       | "when is it due"    | "has it been dispatched" |
| --------------------------- | ------------------- | ------------------------ |
| `NotificationSchedule`      | `notification_time` | `sent`                   |
| `GameStatusSchedule`        | `transition_time`   | `executed`               |
| `ParticipantActionSchedule` | `action_time`       | `processed`              |

Because the names differ, `SchedulerLoop` currently accesses them via `getattr`/`setattr` with runtime strings, which prevents static type-checking. `event_builder` is a `Callable` for the same reason: each model needs different logic to produce a `BotActionQueue` row.

### Proposed Unified Names

**Time field** — rename all three to `due_at`. This is more precise than `scheduled_at` (which already appears on `GameSession` with a different meaning) and more direct than `fire_at`.

**Status field** — rename all three to `dispatched`. The common semantic is "was this row dispatched to `bot_action_queue`?". This is more accurate than the generic `processed` (which `ParticipantActionSchedule` already uses), and avoids the action-specific connotations of `sent` and `executed`.

**Event-building** — replace the `event_builder: Callable` parameter with an abstract method declared on the base class.

### What the Refactoring Would Look Like

```python
# shared/models/schedule_base.py
class ScheduleBase(Base):
    __abstract__ = True

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    game_id: Mapped[str] = mapped_column(ForeignKey("game_sessions.id", ondelete="CASCADE"))
    due_at: Mapped[datetime] = mapped_column(nullable=False, index=True)
    dispatched: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=utc_now, server_default=func.now())

    @abstractmethod
    def to_bot_action(self) -> BotActionQueue: ...
```

```python
# SchedulerLoop constructor shrinks to three params
class SchedulerLoop:
    def __init__(
        self,
        db_url: str,
        notify_channel: str,
        model_class: type[ScheduleBase],
        max_timeout: int = 900,
    ) -> None: ...
```

`_process_item` and `_is_due` become fully typed:

```python
async def _process_item(self, item: ScheduleBase) -> None:
    async with get_db_session() as db:
        db.add(item.to_bot_action())
        db.add(item)
        item.dispatched = True
        await db.commit()

def _is_due(self, item: ScheduleBase) -> bool:
    return item.due_at <= utc_now()
```

### Scope and Dependencies

This requires:

1. **Three Alembic migrations** — column renames in `notification_schedule`, `game_status_schedule`, and `participant_action_schedule` (PostgreSQL supports `ALTER TABLE ... RENAME COLUMN`)
2. **Model updates** — add `ScheduleBase`, update all three subclasses, implement `to_bot_action()` on each
3. **Wide reference updates** — every query, test, and service that references `notification_time`, `transition_time`, `action_time`, `sent`, or `executed` by name
4. **`event_builders.py` absorbed** — `build_*_event` functions move into `to_bot_action()` methods; `shared/services/event_builders.py` and `participant_action_event_builder.py` can be deleted

This is a worthwhile improvement but is a separate task from the remove-scheduler plan. The current `SchedulerLoop` is already committed and tested; this refactoring should be filed independently once Phase 5 (scheduler deletion) is complete.

---

## Implementation Guidance

- **Objectives**: Eliminate the `scheduler` container; bot runs three `SchedulerLoop` tasks internally
- **Key Tasks**:
  1. Implement `SchedulerLoop` in `services/bot/` (async, asyncpg LISTEN, same algorithm as `SchedulerDaemon`)
  2. Wire three `SchedulerLoop` instances in `services/bot/bot.py` `on_ready`, same guard pattern as `BotActionListener`
  3. Import `event_builders` and `participant_action_event_builder` from `services/scheduler/` into the bot (or move them to `shared/` first — see note below)
  4. Delete `services/scheduler/` directory
  5. Remove `scheduler` service from all compose files (`compose.yaml`, `compose.int.yaml`, `compose.e2e.yaml`, `compose.prod.yaml`, `compose.staging.yaml`)
  6. Remove `scheduler.Dockerfile` from `docker/`
  7. Do NOT remove `psycopg2-binary` from `pyproject.toml` — it is still used by `services/init/`
- **Note on event builders**: `services/scheduler/event_builders.py` and `participant_action_event_builder.py` are needed by the bot after the scheduler is deleted. Options: (a) move them to `shared/services/event_builders.py` before deleting the scheduler directory, or (b) copy them into `services/bot/` as part of this work.
- **Dependencies**: None — RabbitMQ removal is complete.
- **Success Criteria**:
  - All existing scheduler integration and e2e tests pass with bot handling schedule processing
  - `services/scheduler/` directory deleted
  - `scheduler` service absent from all compose files
  - Reminder DMs, status transitions, and participant drops continue to fire at correct times
