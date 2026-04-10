<!-- markdownlint-disable-file -->

# Task Research Notes: Remove Scheduler Service

## Research Executed

### File Analysis

- `services/scheduler/generic_scheduler_daemon.py`
  - Pattern: query `MIN(scheduled_time)` where `status=False`; if due, process; else wait
  - Wait is bounded by `max_timeout` (default 900s) or time until next item
  - Wakes early via `PostgresNotificationListener.wait_for_notification()`
  - `_mark_item_processed` sets `executed=True`; caller commits — atomic with publish step
  - Three daemon instances created by `scheduler_daemon_wrapper.py`: notification, status, participant-action
- `services/scheduler/event_builders.py`
  - `build_notification_event`: builds `NOTIFICATION_DUE` from `NotificationSchedule` row
  - Per-message TTL calculated as time remaining until game starts
- `services/scheduler/participant_action_event_builder.py`
  - `build_participant_action_event`: builds `PARTICIPANT_DROP_DUE` from `ParticipantActionSchedule`
- `services/scheduler/event_builders.py` (status)
  - `build_status_transition_event`: builds `GAME_STATUS_TRANSITION_DUE` from `GameStatusSchedule`
- `services/scheduler/postgres_listener.py`
  - Synchronous psycopg2-based LISTEN using `select()` for timeout-based waking
  - Used only by the scheduler (sync context)
- `services/bot/message_refresh_listener.py`
  - asyncpg async LISTEN — the pattern the bot already uses for DB notifications
- `services/bot/events/handlers.py`
  - `_handle_notification_due`: routes to `_handle_game_reminder`, `_handle_join_notification`, `_handle_clone_confirmation` based on `notification_type`
  - `_handle_status_transition_due`: transitions game status, archives Discord message
  - `_handle_participant_drop_due`: delegates to `services/bot/handlers/participant_drop.py`
  - All handler logic already lives in the bot — scheduler only does timing + dispatch

### Code Search Results

- Schedule table writes in API
  - `GameService._setup_game_schedules`: writes `notification_schedule`, `game_status_schedule`
  - `GameService._apply_deadline_carryover`: writes `participant_action_schedule`; calls `pg_notify('participant_action_schedule_changed', '')` directly
  - `GameService._update_status_schedules`: updates `game_status_schedule` on game edit
  - `GameService._schedule_join_notifications_for_game`: writes `notification_schedule` join entries
- DB triggers already in place
  - `notification_schedule` → `NOTIFY notification_schedule_changed` (confirmed by scheduler daemon config)
  - `game_status_schedule` → `NOTIFY game_status_schedule_changed`
  - `participant_action_schedule` → `NOTIFY participant_action_schedule_changed` (also called directly by API)
- `daemon_runner.py`
  - `run_daemon()` wraps `SchedulerDaemon.run()` with signal handlers and telemetry flush — thin wrapper
- `scheduler_daemon_wrapper.py`
  - Creates three `SchedulerDaemon` instances with different model/field/builder configs
  - Runs them in threads via `threading.Thread`

### Project Conventions

- Bot already has an asyncpg LISTEN loop (`MessageRefreshListener`)
- async-first: bot is fully async (discord.py + asyncio); sync psycopg2 listener is scheduler-specific
- Schedule tables use `executed: bool` field (not delete-on-process) — this is a difference from
  the `message_refresh_queue` / `bot_action_queue` pattern and needs consideration

## Key Discoveries

### Why the Scheduler Exists

The scheduler is a time-aware dispatcher: it knows the next due item and sleeps precisely until
it becomes due, waking early if a new item is inserted. This avoids polling.

The bot does not currently have this capability — it processes events reactively when notified.

### What Changes If the Scheduler Is Removed

The bot must gain the scheduler's timing logic. Specifically, for each schedule table, the bot needs:

1. A LISTEN connection on the table's NOTIFY channel
2. A query loop: `SELECT ... WHERE executed=False ORDER BY time ASC LIMIT 1`
3. Sleep until `scheduled_time` (or until notified, or until `max_timeout`)
4. When due: execute the action; mark `executed=True`; commit

This is exactly what `SchedulerDaemon.run()` does — the bot would absorb this logic.

### `executed` Flag vs Delete-on-Process

The schedule tables use `executed=True` marking rather than row deletion. This is intentional:
rows are reference data (they reflect what was scheduled) and may be useful for auditing/debugging.
The bot loop would preserve this pattern — mark executed and commit atomically with the action.

Alternatively, tables could be migrated to delete-on-process (like `message_refresh_queue`),
but that is a separate concern and not required for scheduler removal.

### Concurrency Model

Scheduler runs three daemons in threads. Bot is single-process asyncio.
Replacing threads with asyncio tasks is straightforward: one `asyncio.Task` per schedule table,
each running the same wait-loop logic using asyncpg for async LISTEN instead of psycopg2.

### Prerequisite Dependency

This research assumes the RabbitMQ removal (doc `20260408-02`) is completed first.
After that removal, the scheduler publishes to `bot_action_queue` (DB) instead of RabbitMQ.
The scheduler-removal step then eliminates the need for that intermediate table for scheduler flows —
the bot reads directly from `notification_schedule`, `game_status_schedule`, `participant_action_schedule`.

### Docker / Deployment

`services/scheduler` is its own Docker container (`scheduler.Dockerfile`).
Removing it means one fewer container in all compose files.

## Recommended Approach

Absorb the three scheduler daemon loops directly into the bot service as asyncio tasks.

### Bot changes

Add a `SchedulerLoop` abstraction in the bot (parallel to `MessageRefreshListener`):

```python
class SchedulerLoop:
    """
    Async LISTEN+poll loop replacing SchedulerDaemon for one schedule table.

    Listens on notify_channel; on wake (or timeout), queries for the next
    unexecuted item due now or in the past; processes it; marks executed=True
    and commits atomically.
    """
    def __init__(self, notify_channel, model_class, time_field, handler_fn, max_timeout=900):
        ...

    async def run(self) -> None:
        conn = await asyncpg.connect(db_url)
        await conn.add_listener(self.notify_channel, self._on_notify)
        while not shutdown:
            item = await self._get_next_due_item()
            if item and is_due(item):
                await self._process(item)
            else:
                wait = time_until_due(item) or self.max_timeout
                await asyncio.wait_for(self._notified.wait(), timeout=wait)
                self._notified.clear()
```

Three instances started as asyncio tasks in `bot/main.py`:

```python
asyncio.create_task(SchedulerLoop(
    notify_channel="notification_schedule_changed",
    model_class=NotificationSchedule,
    time_field="notification_time",
    handler_fn=event_handlers._handle_notification_due,
).run())
```

### Services removed

- `services/scheduler/` — entire service; Docker container removed from all compose files
- `scheduler.Dockerfile` removed
- `shared/messaging/sync_publisher.py` — already removed by RabbitMQ removal
- `services/scheduler/postgres_listener.py` — replaced by asyncpg in bot
- `psycopg2` scheduler-only dependency removed (if not used elsewhere)
- `RABBITMQ_URL` from scheduler config — already removed by RabbitMQ removal
- Scheduler env vars (`DATABASE_URL` for scheduler, `SCHEDULER_*`) removed

### What stays

- Schedule tables (`notification_schedule`, `game_status_schedule`, `participant_action_schedule`)
  and their DB triggers — unchanged
- All handler logic in `services/bot/events/handlers.py` — unchanged; just called directly
  by the new `SchedulerLoop` instead of via a RabbitMQ event payload

## Implementation Guidance

- **Objectives**: Eliminate scheduler container; bot runs scheduling loops internally as asyncio tasks
- **Key Tasks**:
  1. Implement `SchedulerLoop` class in `services/bot/` (async, asyncpg LISTEN, same algorithm as `SchedulerDaemon`)
  2. Wire three `SchedulerLoop` instances in `services/bot/main.py` startup
  3. Verify handler functions (`_handle_notification_due`, `_handle_status_transition_due`, `_handle_participant_drop_due`) are callable without RabbitMQ event wrapping
  4. Remove `services/scheduler/` directory
  5. Remove `scheduler` service from all compose files
  6. Remove `scheduler.Dockerfile`
  7. Remove `psycopg2` if no other service uses it
- **Dependencies**: Complete RabbitMQ removal (`20260408-02`) first; `bot_action_queue` table for
  scheduler flows can be skipped entirely if this work follows immediately
- **Success Criteria**:
  - All existing scheduler integration and e2e tests pass with bot handling schedule processing
  - `services/scheduler/` directory deleted
  - `scheduler` service absent from `compose.yaml`
  - Reminder DMs, status transitions, and participant drops continue to fire at correct times
