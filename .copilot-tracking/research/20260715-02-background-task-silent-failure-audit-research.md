<!-- markdownlint-disable-file -->

# Task Research Notes: Bot/API background-task restart-forcing and silent-failure audit

## Research Executed

### File Analysis

- `shared/pg_listen.py` (36-97)
  - `listen_with_reconnect()` — the fix already shipped in `5f051fb3` for the original bug (silent hang in Postgres LISTEN reconnect). Opens `asyncpg.connect()`, registers `add_termination_listener` on the connection so a dropped connection (transient network blip, idle-timeout kill from a proxy/pooler, Postgres restart) is detected via an `asyncio.Event`, then reconnects after `retry_delay_seconds` (default 5s). Runs until cancelled; any exception during connect/listen is logged and retried, never propagates.
- `services/api/services/sse_bridge.py` (42, 75-83)
  - `SSEGameUpdateBridge.start_consuming()` delegates entirely to `listen_with_reconnect`. Already migrated — correct reference implementation.
- `services/bot/bot_action_listener.py` (33, 106-171)
  - `BotActionListener.start()` also delegates to `listen_with_reconnect`. `_process_one()` wraps dispatch in `try/except Exception` and always deletes the row (documented anti-infinite-retry-loop behavior). `_spawn_drain()` guards re-spawn with `task.done()`, so a drain task that dies from an unhandled exception self-heals on the next NOTIFY. Already migrated — correct reference implementation.
- `services/bot/message_refresh_listener.py` (29, 58-63)
  - `MessageRefreshListener.start()` also delegates to `listen_with_reconnect`. Already migrated — correct reference implementation.
- `services/bot/scheduler_loop.py` (65-79)
  - `SchedulerLoop.run()` — **not migrated**. Opens a raw `asyncpg.connect()` + `add_listener()` with no `add_termination_listener`/reconnect. Worse than the original bug: the `while True:` loop body (`_get_next_due_item()`, `_process_item()`, the `asyncio.wait_for`/`Event` wait) has **zero exception handling** — contrast with every migrated listener above, which either delegates entirely to `listen_with_reconnect` or wraps its own per-item work in `try/except`. Any transient error anywhere in the loop (DB blip during either query, `asyncpg.connect()` failing at that instant) propagates out of `run()` uncaught.
  - Instantiated 3 times in `services/bot/bot.py` (227-256): one `SchedulerLoop` per schedule table (`notification_schedule`, `game_status_schedule`, `participant_action_schedule`).
- `services/bot/announcement_loop.py` (63-107)
  - `AnnouncementLoop.start()` — **not migrated**. Same raw `asyncpg.connect()` + `add_listener()`, no reconnect-on-termination. Unlike `SchedulerLoop`, the per-iteration body (`_process_due()`, `_next_due_time()`, the wait) **is** wrapped in `try/except Exception: logger.exception(...)` inside the `while True:` loop — so a transient error during an iteration is caught and the loop continues. However: (1) if the LISTEN connection itself silently dies, the loop still only degrades to polling at `MAX_TIMEOUT` (56) = **3600 seconds**, silently, forever, until restart; (2) the _outer_ `try/except Exception: logger.exception("AnnouncementLoop failed: could not establish database connection")` (103-104) around the initial `asyncpg.connect()` swallows a startup connection failure and lets `start()` return for good — no retry.
- `services/bot/bot.py` (138-274, esp. 198-257)
  - `on_ready()` starts all four background tasks (`MessageRefreshListener`, `BotActionListener`, `AnnouncementLoop`, the 3 `SchedulerLoop`s) via `asyncio.create_task(...)`, each gated by `if not hasattr(self, "_X_started"): self._X_started = True; ...`. This flag is set exactly once per process lifetime and never cleared or checked against `task.done()`. For the two listeners that delegate to `listen_with_reconnect` this is harmless (that coroutine only returns on cancellation). For `SchedulerLoop`/`AnnouncementLoop`, which _can_ return/raise on an unhandled or initial-connect error, this guard means the task is **never restarted**, not even on a subsequent `on_ready` after a full Gateway reconnect.
  - Contrast: `_recover_pending_workers()` (581-603) and `_spawn_channel_worker()` (605-613) use a `task.done()` check (not a one-shot flag) and are called unconditionally on every `on_ready`/`on_resumed`, providing genuine self-healing for channel workers.
- `services/bot/events/handlers.py` (1408-1451, 1482-1512)
  - `_channel_worker()` (1408-1451): the `while True:` body (`_fetch_next_queued_game`, `redis.claim_channel_rate_limit_slot`, the final `delete(MessageRefreshQueue)` + commit) has **no try/except**; only a `finally` that pops the worker from `_channel_workers`. A transient DB error during the dequeue or delete step kills the task.
  - `_edit_with_backoff()` (1482-1512), called from within the same loop, by contrast **does** catch broadly (`except discord.HTTPException` with 429-specific retry, `except Exception` for everything else, both logging and returning `None` rather than raising) — showing the project's own established good pattern for this exact class of loop.
  - Because `_channel_worker` pops itself from `_channel_workers` in `finally`, and `_recover_pending_workers()` re-spawns any channel missing an active worker, a dead worker **does** self-heal — but only on the next `on_ready`/`on_resumed` Gateway event, which may be far apart for a long-lived, network-stable bot process.
- `shared/database.py` (65, 68, 71)
  - `create_async_engine(..., pool_pre_ping=True)` on all three engines (api, bot, sync). Confirms transient dead-pooled-connection recovery is already handled at the SQLAlchemy layer for connection checkout; does not cover a connection dying mid-query (the residual risk noted above for `SchedulerLoop`/`_channel_worker`).
- `shared/cache/client.py` (200-536)
  - `RedisClient` methods each independently `try/except Exception`, logging and returning a safe default (`None`/`False`) or, for the rate-limit `eval` helpers, a bounded backoff value — never propagate except for `redis.exceptions.NoPermissionError` (deliberately re-raised in `claim_global_and_channel_slot`/`claim_global_slot`, an auth-misconfiguration signal, not a transient-network case). Connection pooled via `redis.asyncio.ConnectionPool`. No restart-forcing gap found here.
- `shared/discord/client.py` (132-263)
  - `DiscordAPIClient._make_api_request` catches `aiohttp.ClientError` and converts to `DiscordAPIError`; no persistent connection/listener state to go stale. Confirmed aiohttp's own default timeout (`ClientTimeout(total=300, sock_connect=30)`, verified via `python -c "import aiohttp; print(aiohttp.client.DEFAULT_TIMEOUT)"`) is never overridden to something unbounded. No gap found here.
- `services/api/app.py` (78-114)
  - `lifespan()`'s only background task is the already-migrated SSE bridge. No other candidate found in the API service.
- `docker/backup-entrypoint.sh`, `docker/backup-script.sh`
  - Backups run via `supercronic` (cron), each invocation a fresh short-lived process — not exposed to the long-lived-process hang/silent-death class of bug being audited.
- `services/init/main.py` (83-99)
  - One-shot init container; `while True: time.sleep(SECONDS_PER_DAY)` at the end is a deliberate idle-forever healthy marker after migrations complete, not a task that does ongoing work. Not in scope.

### Code Search Results

- `grep -rn "asyncpg.connect\|add_listener\|add_termination_listener\|listen_with_reconnect"` (excluding tests)
  - Confirms exactly 3 migrated call sites (`sse_bridge.py`, `message_refresh_listener.py`, `bot_action_listener.py`) and exactly 2 unmigrated raw-connection call sites (`scheduler_loop.py`, `announcement_loop.py`).
- `grep -rn "asyncio.create_task"` (excluding tests)
  - Enumerated all ~13 fire-and-forget task spawn sites across `services/api/app.py`, `services/api/services/sse_bridge.py`, `services/bot/bot_action_listener.py`, `services/bot/bot.py`. None register a `done_callback` that surfaces an unexpected exception distinctly (aside from Python's own deferred "Task exception was never retrieved" warning, emitted only at GC time).
- `grep -rn "except.*:\s*$" -A1 | grep -B1 "pass$"` (excluding tests)
  - Only one bare-pass exception handler in the entire `services/`+`shared/` tree: `services/bot/events/handlers.py:961-962`, a `datetime.fromisoformat` parse fallback for DM-message formatting — benign, not a resilience issue.
- `find tests -iname "*scheduler_loop*" -o -iname "*announcement_loop*"`
  - `tests/unit/services/bot/test_scheduler_loop.py`, `tests/unit/bot/test_announcement_loop.py`, `tests/integration/test_scheduler_loop.py` exist but (per `grep -n "def test_"`) exercise only the due/not-due/notify-wakes-loop paths — no test exercises connection-loss/reconnect or exception-mid-loop behavior, unlike `tests/unit/shared/test_pg_listen.py` (230 lines added in `5f051fb3` specifically to cover reconnect behavior). Corroborates that these two components were out of scope for the original fix's test additions.

### External Research

Not applicable — this is an internal codebase audit (tracing the blast radius of an already-understood, already-fixed bug pattern) using project source and git history only.

### Project Conventions

- `shared/pg_listen.py`'s `listen_with_reconnect()` is the established, working pattern for any persistent asyncpg LISTEN connection; new/existing listeners should delegate to it rather than open `asyncpg.connect()` directly.
- Per-iteration `try/except Exception: logger.exception(...)` inside a `while True:` background loop (as in `AnnouncementLoop`'s loop body, `_edit_with_backoff`, `_projection_heartbeat`) is the project's established pattern for making a loop resilient to a single bad iteration without killing the task.
- `task.done()` re-spawn checks (as in `_recover_pending_workers`/`_spawn_channel_worker`) are the established pattern for self-healing a crashed per-entity worker task, in contrast to the one-shot `hasattr(self, "_X_started")` guard used for the four `on_ready`-started singleton tasks.

## Key Discoveries

### Project Structure

Background long-lived work in this system is split across four kinds of "persistent process" that must all survive for the process's entire (hopefully weeks-long) lifetime without a restart:

| Component                               | File                                       | Reconnects on dropped LISTEN?       | Survives exception mid-loop?                   | Restarts itself if killed?                                    |
| --------------------------------------- | ------------------------------------------ | ----------------------------------- | ---------------------------------------------- | ------------------------------------------------------------- |
| `SSEGameUpdateBridge`                   | `services/api/services/sse_bridge.py`      | Yes (`listen_with_reconnect`)       | Yes                                            | N/A (never exits)                                             |
| `BotActionListener`                     | `services/bot/bot_action_listener.py`      | Yes (`listen_with_reconnect`)       | Yes (per-row try/except + done-check re-spawn) | N/A (never exits)                                             |
| `MessageRefreshListener`                | `services/bot/message_refresh_listener.py` | Yes (`listen_with_reconnect`)       | Yes                                            | N/A (never exits)                                             |
| `SchedulerLoop` ×3                      | `services/bot/scheduler_loop.py`           | **No**                              | **No**                                         | **No** (one-shot `hasattr` guard)                             |
| `AnnouncementLoop`                      | `services/bot/announcement_loop.py`        | **No** (degrades to ≤3600s polling) | Yes (per-iteration)                            | **No** for initial-connect failure (one-shot `hasattr` guard) |
| `_channel_worker` (per Discord channel) | `services/bot/events/handlers.py`          | N/A (no LISTEN)                     | **No**                                         | Yes, but only on next `on_ready`/`on_resumed`                 |

### Findings Inventory

Numbered findings referenced throughout the rest of this document (severity as assessed during triage):

1. **`SchedulerLoop` (High)** — `services/bot/scheduler_loop.py`, all 3 instances. No reconnect on dropped LISTEN, no exception handling anywhere in `run()`, never restarted once killed (one-shot `hasattr` guard in `bot.py`). Same root cause as `5f051fb3`, with no fallback at all.
2. **`AnnouncementLoop` (High)** — `services/bot/announcement_loop.py`. No reconnect on dropped LISTEN (degrades silently to ≤3600s polling); initial-connect failure is swallowed with no retry; never restarted once killed (same one-shot guard).
3. **One-shot `hasattr` startup guard (Medium — deferred, not fixed in this pass)** — `services/bot/bot.py` `on_ready`. Prevents #1/#2 from ever being restarted even across a full Gateway reconnect. Becomes largely moot once #1/#2 are self-healing internally; generalizing it into a real supervisor/restart-policy for all four `on_ready` tasks is a separate design decision.
4. **`_channel_worker` (Medium)** — `services/bot/events/handlers.py:1408-1451`. No exception handling in the loop body; self-heals only on the next `on_ready`/`on_resumed`.
5. **No visibility into fire-and-forget task deaths (Low — deferred, not fixed in this pass)** — none of the ~13 `asyncio.create_task()` call sites report an unexpected exit distinctly; only Python's own deferred GC-time warning. A `spawn_supervised()`-style helper would need its own design pass (naming, and an alerting story that depends on Grafana alert rules outside this codebase).
6. **Checked and found sound (no fix needed)** — DB connection pool (`pool_pre_ping=True`), Redis client (pooled, all errors caught and degraded gracefully), Discord REST client (sane aiohttp timeouts, per-call error handling), SSE bridge (already migrated correctly), backup service (cron-triggered, short-lived, not exposed to this bug class).

### Implementation Patterns

The three migrated listeners and `AnnouncementLoop`'s loop body demonstrate the project's own correct pattern for this exact problem: either delegate the whole connection lifecycle to `listen_with_reconnect`, or wrap per-iteration work in a broad `try/except` that logs and continues. `SchedulerLoop.run()` has neither protection — it is a straight-line `while True:` with no defensive wrapping at all, making it strictly more fragile than the code the original bug report was about.

### Complete Examples

Unmigrated, unguarded loop — `services/bot/scheduler_loop.py:65-79`:

```python
async def run(self) -> None:
    """Open asyncpg LISTEN connection and run the scheduling loop."""
    pg_url = self._db_url.replace("postgresql+asyncpg://", "postgresql://")
    conn = await asyncpg.connect(pg_url)
    await conn.add_listener(self.notify_channel, self._on_notify)
    while True:
        item = await self._get_next_due_item()
        if item is not None and self._is_due(item):
            await self._process_item(item)
            await asyncio.sleep(0)
        else:
            wait = self._time_until_due(item) or self.max_timeout
            with contextlib.suppress(asyncio.TimeoutError):
                await asyncio.wait_for(self._notified.wait(), timeout=wait)
            self._notified.clear()
```

Reference (already-fixed) pattern — `services/bot/bot_action_listener.py:106-118`:

```python
async def start(self) -> None:
    """Maintain the LISTEN connection, reconnecting automatically on loss.

    Drains any pending bot_action_queue rows on every (re)connect, not
    just the first one, so rows written while the connection was down
    (or before the listener started) are picked up once LISTEN resumes.
    """
    await listen_with_reconnect(
        self._bot_db_url,
        "bot_action_queue_changed",
        self._on_notify,
        on_connected=lambda _conn: self._spawn_drain(),
    )
```

One-shot startup guard that prevents recovery — `services/bot/bot.py:225-257` (elided to the relevant guard):

```python
if not hasattr(self, "_scheduler_loops_started"):
    self._scheduler_loops_started = True
    self._notification_scheduler_task = asyncio.create_task(SchedulerLoop(...).run())
    self._game_status_scheduler_task = asyncio.create_task(SchedulerLoop(...).run())
    self._participant_action_scheduler_task = asyncio.create_task(SchedulerLoop(...).run())
```

### API and Schema Documentation

Not applicable — internal reliability audit, no API surface change.

### Configuration Examples

Not applicable — no configuration format changes anticipated; all fixes are Python control-flow changes within existing modules.

### Technical Requirements

- Any fix to `SchedulerLoop`/`AnnouncementLoop` must preserve documented behavior in `docs/developer/architecture.md` (sub-10-second NOTIFY latency, 900s/3600s polling ceilings as _fallback_ behavior, not the only recovery path).
- Per `CLAUDE.md`, all three fixes require RED→GREEN→REFACTOR unit tests (`.github/instructions/test-driven-development.instructions.md`, `.github/instructions/unit-tests.instructions.md`) before being considered complete; run via `uv run pytest tests/unit` (never `--testmon` manually).
- `tests/unit/shared/test_pg_listen.py` and `tests/unit/bot/test_bot_action_listener.py` (from `5f051fb3`) are the existing template for what reconnect-behavior test coverage should look like for `SchedulerLoop`/`AnnouncementLoop`.
- Must not change the one-shot `hasattr` guard's behavior for `MessageRefreshListener`/`BotActionListener` (still correct for those, since they never return).
- Items #3 (generalizing the `on_ready` startup guard into a supervisor/restart policy for all four tasks) and #5 (a `spawn_supervised()`-style task-death observability helper across all ~13 `create_task` sites) are explicitly **out of scope for this fix** — deferred as separate, deliberate design decisions rather than bundled into this pre-deploy reliability pass. Rationale: #3 becomes largely moot once `SchedulerLoop`/`AnnouncementLoop` are internally self-healing (they will then behave like the other two tasks, for which the guard is already correct); #5 is a new cross-cutting convention whose value (alerting) depends on Grafana alert-rule decisions outside this codebase, not something to design under deploy time pressure.

## Recommended Approach

Fix findings #1, #2, and #4 from the Findings Inventory above, each following the project's own established patterns — no new abstractions introduced:

- **#1 `SchedulerLoop` (`services/bot/scheduler_loop.py`)** — Refactor `run()` to delegate the connection lifecycle to `shared.pg_listen.listen_with_reconnect()` (matching `BotActionListener`/`MessageRefreshListener`/`SSEGameUpdateBridge`), and additionally wrap the due-item-check/process/wait body in a `try/except Exception: logger.exception(...)` per iteration (matching `AnnouncementLoop`'s loop body), since `listen_with_reconnect` only protects the LISTEN connection itself, not the DB work done in `_get_next_due_item`/`_process_item` on each wake.
- **#2 `AnnouncementLoop` (`services/bot/announcement_loop.py`)** — Migrate `start()`'s connection handling to `listen_with_reconnect()` the same way, replacing the raw `asyncpg.connect()`/manual reconnect-on-outer-exception with the shared helper (which already retries indefinitely on initial-connect failure, closing the "swallowed startup error, no retry" gap for free). Keep the existing per-iteration `try/except` body as-is — it already matches the target pattern.
- **#4 `_channel_worker` (`services/bot/events/handlers.py:1408-1451`)** — Wrap the loop body (`_fetch_next_queued_game` through the final delete/commit) in a `try/except Exception: logger.exception(...); continue`-style guard, matching the pattern `_edit_with_backoff` already uses one level deeper in the same call stack, so a transient DB error during dequeue/delete no longer kills the whole worker (it would currently only recover on the next Gateway `on_ready`/`on_resumed`).

Explicitly not fixed now (see Findings Inventory and Technical Requirements): #3 (generalized supervisor/restart-policy for the `on_ready` task-startup guards) and #5 (cross-cutting task-death observability helper).

## Implementation Guidance

- **Objectives**: Fix findings #1 (`SchedulerLoop`) and #2 (`AnnouncementLoop`) — the two remaining "transient error → permanent silent stop until process restart" gaps that share the exact root cause already fixed in `5f051fb3` for other listeners — plus finding #4, the analogous unguarded-loop gap in `_channel_worker`, without introducing new abstractions or touching the deferred findings #3/#5.
- **Key Tasks**:
  - `SchedulerLoop.run()`: replace the raw `asyncpg.connect()`/`add_listener()` pair with a call to `listen_with_reconnect(...)`, moving the due-item while-loop into the `on_notify`/main-body position expected by that helper (or into a coroutine passed via its callback hooks, following whatever shape best fits `_get_next_due_item`/`_process_item`/`_time_until_due`'s existing structure); add a per-iteration `try/except Exception: logger.exception(...)` around the body.
  - `AnnouncementLoop.start()`: same `listen_with_reconnect()` migration; keep `_process_due`/`_next_due_time`/the existing per-iteration try/except unchanged.
  - `_channel_worker()`: add a `try/except Exception: logger.exception(...); continue` around the loop body (dequeue → rate-limit claim → edit-with-backoff → delete/commit), being careful not to swallow the `finally`'s cleanup of `_channel_workers`.
  - Add reconnect/exception-mid-loop unit tests for `SchedulerLoop` and `AnnouncementLoop` modeled on `tests/unit/shared/test_pg_listen.py` and `tests/unit/bot/test_bot_action_listener.py`; add an exception-mid-loop test for `_channel_worker` in whatever test module covers `services/bot/events/handlers.py`.
  - Run `uv run pytest tests/unit` (never `--testmon` manually per `CLAUDE.md`) and the relevant integration tests (`tests/integration/test_scheduler_loop.py`) before committing.
- **Dependencies**: `shared/pg_listen.py` (`listen_with_reconnect`), `services/bot/bot.py`'s `on_ready` wiring (no change expected, but must keep working for the migrated tasks), existing test suites listed above.
- **Success Criteria**: All three components self-heal from (a) a dropped/terminated LISTEN connection and (b) an unhandled exception during a single iteration, without requiring a process restart; new unit tests cover both failure modes for each; `docs/developer/architecture.md`'s documented latency/polling-ceiling behavior is preserved as the fallback path, not the only recovery path; no changes to `#3`/`#5`-scoped code.
