<!-- markdownlint-disable-file -->

# Task Details: Background-Task Silent-Failure Fix (SchedulerLoop, AnnouncementLoop, _channel_worker)

## Research Reference

**Source Research**: .copilot-tracking/research/20260715-02-background-task-silent-failure-audit-research.md

## Phase 1: SchedulerLoop reconnect + per-iteration exception handling

### Task 1.1: Write failing regression tests for SchedulerLoop resilience (RED)

`SchedulerLoop.run()` currently opens a raw `asyncpg.connect()` with no
`add_termination_listener`/reconnect, and its `while True:` body has zero
exception handling — the same root cause already fixed in `5f051fb3` via
`shared/pg_listen.py`'s `listen_with_reconnect()`, but with no fallback at
all. This is a bug fix (the buggy code already exists), so there is no stub
to create — write regression tests asserting the correct (post-fix) behavior
and mark them `xfail(strict=True)` per
`.github/instructions/test-driven-development.instructions.md`'s "TDD for Bug
Fixes" workflow.

Add two new tests to `tests/unit/services/bot/test_scheduler_loop.py`:

1. `test_run_delegates_to_listen_with_reconnect` — patches
   `services.bot.scheduler_loop.listen_with_reconnect` (module-level import,
   not `asyncpg.connect`) with an `AsyncMock`, runs `run()` as a background
   task, and asserts `listen_with_reconnect` was awaited with
   `(loop._db_url, loop.notify_channel, loop._on_notify)` as positional args —
   model directly on `tests/unit/bot/test_bot_action_listener.py`'s
   `TestStart.test_start_delegates_to_listen_with_reconnect`. Cancel and await
   the task in a `finally`/`with pytest.raises(asyncio.CancelledError)` block
   the same way existing tests in this file already do.
2. `test_run_body_continues_after_exception_in_iteration` — patches
   `_get_next_due_item` with a `side_effect` list `[RuntimeError("transient
DB error"), None]` (mirroring
   `test_announcement_loop_start_retries_after_transient_error`'s pattern in
   `tests/unit/bot/test_announcement_loop.py`), patches
   `services.bot.scheduler_loop.listen_with_reconnect` to a no-op `AsyncMock`
   that blocks forever (e.g. `side_effect=lambda *a, **k:
asyncio.Event().wait()`) so only the due-item loop body is exercised, runs
   `run()` as a background task, and asserts `_get_next_due_item` was awaited
   at least twice (proving the loop survived the first exception and
   continued) and that `logger.exception` was called (patch
   `services.bot.scheduler_loop.logger`).

Mark both new tests `@pytest.mark.xfail(strict=True, reason="Bug:
SchedulerLoop.run() has no reconnect-on-dropped-LISTEN or per-iteration
exception handling — same root cause as 5f051fb3")`. Run `uv run pytest
tests/unit/services/bot/test_scheduler_loop.py -v` and confirm both show as
`xfailed` before proceeding (proves the tests actually detect the gap).

- **Files**:
  - tests/unit/services/bot/test_scheduler_loop.py - add the two new xfail tests described above
- **Success**:
  - Both new tests exist with real assertions (not `pytest.raises(NotImplementedError)`)
  - `uv run pytest tests/unit/services/bot/test_scheduler_loop.py -v` shows both new tests as `xfailed`, all pre-existing tests in this file still pass unchanged
- **Research References**:
  - .copilot-tracking/research/20260715-02-background-task-silent-failure-audit-research.md (Lines 17-19) - SchedulerLoop finding (not migrated, zero exception handling)
  - .copilot-tracking/research/20260715-02-background-task-silent-failure-audit-research.md (Lines 95-113) - complete example of the current unguarded `run()` implementation
  - .copilot-tracking/research/20260715-02-background-task-silent-failure-audit-research.md (Lines 151-157) - Technical Requirements: TDD required, `tests/unit/shared/test_pg_listen.py`/`tests/unit/bot/test_bot_action_listener.py` are the template
  - Source: tests/unit/bot/test_bot_action_listener.py (Lines 395-419) - `TestStart.test_start_delegates_to_listen_with_reconnect` reference pattern
  - Source: tests/unit/bot/test_announcement_loop.py (Lines 235-264) - `test_announcement_loop_start_retries_after_transient_error` reference pattern for exception-mid-loop-continues assertions
- **Dependencies**:
  - None (first task of the plan)

### Task 1.2: Migrate SchedulerLoop.run() to listen_with_reconnect and add per-iteration exception handling (GREEN)

Split `run()` into (a) connection-lifecycle management delegated to
`listen_with_reconnect()`, matching `BotActionListener.start()` /
`MessageRefreshListener.start()` / `SSEGameUpdateBridge.start_consuming()`,
and (b) an independent due-item loop that runs concurrently, since the
due-item loop only depends on the `_notified` `asyncio.Event` set by
`_on_notify` — it never touches the `asyncpg.Connection` object directly, so
it does not need to live inside `listen_with_reconnect`'s connection-scoped
callbacks.

Target shape (adapt naming/structure to fit; this is guidance, not a literal
diff):

```python
async def run(self) -> None:
    """Maintain the LISTEN connection and run the scheduling loop concurrently.

    Connection lifecycle (including reconnect-on-loss) is delegated to
    listen_with_reconnect; the due-item loop runs independently since it only
    depends on the `_notified` event set by `_on_notify`, not on the
    connection object itself.
    """
    async with asyncio.TaskGroup() as tg:
        tg.create_task(listen_with_reconnect(self._db_url, self.notify_channel, self._on_notify))
        tg.create_task(self._run_loop())

async def _run_loop(self) -> None:
    """Run the due-item check/process/wait cycle, surviving per-iteration errors."""
    while True:
        try:
            item = await self._get_next_due_item()
            if item is not None and self._is_due(item):
                await self._process_item(item)
                await asyncio.sleep(0)
            else:
                wait = self._time_until_due(item) or self.max_timeout
                with contextlib.suppress(asyncio.TimeoutError):
                    await asyncio.wait_for(self._notified.wait(), timeout=wait)
                self._notified.clear()
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception(
                "SchedulerLoop(%s): error in loop iteration, retrying", self.notify_channel
            )
```

`asyncio.TaskGroup` (stdlib, Python 3.11+; this project requires `>=3.13` per
`pyproject.toml`) is preferred over `asyncio.gather` here because it
cancels sibling tasks automatically if one raises, giving cleaner shutdown
semantics for two coroutines that are each meant to run forever. If
`asyncio.gather` is used instead to match the project's existing convention
(`services/bot/bot.py:665`, `services/api/routes/games.py:577,584`), note
that `gather` does **not** auto-cancel siblings on a non-cancellation
exception — acceptable here only because both coroutines already catch and
log everything except `CancelledError`, so neither is expected to raise
under normal operation. Prefer `TaskGroup` unless there is a concrete reason
not to.

Remove the `xfail` markers added in Task 1.1 (do not modify the assertions).

Update the four pre-existing tests in
`tests/unit/services/bot/test_scheduler_loop.py` that patch
`services.bot.scheduler_loop.asyncpg.connect` directly and assert on
`mock_conn.add_listener` — these test the raw-connection implementation
detail being replaced, so per the phase-isolation "ordering rule for code
removal" they must be updated in this same task, not deferred:

- `test_run_skips_process_item_when_not_due` (currently lines 131-159)
- `test_run_calls_process_item_when_due` (currently lines 162-190)
- `test_run_handles_no_items` (currently lines 193-218)
- `test_run_clears_notified_after_waking` (currently lines 250-280)

For each, replace the `patch("services.bot.scheduler_loop.asyncpg.connect",
...)` context manager with `patch("services.bot.scheduler_loop.
listen_with_reconnect", new=AsyncMock(side_effect=lambda *a, **k:
asyncio.Event().wait()))` (a permanently-pending awaitable, standing in for
a real listener that runs until cancelled) so `run()`'s `TaskGroup`/`gather`
still has a live "connection" branch while the due-item loop
(`_run_loop`/inlined body) is exercised exactly as before. Leave every other
part of each test (the due-item mocking, the `task.cancel()` /
`CancelledError` teardown, the assertions) unchanged — only the patched
target and its return value change. `test_on_notify_sets_notified_event`
(lines 221-226) and `test_get_next_due_item_queries_database` (lines
229-247) do not touch `asyncpg.connect` and need no changes.

Run `uv run pytest tests/unit/services/bot/test_scheduler_loop.py -v` and
confirm all tests pass (the two from Task 1.1 now green, no longer xfail;
all four rewritten tests green; all untouched tests still green).

- **Files**:
  - services/bot/scheduler_loop.py - split `run()` into connection delegation + independent `_run_loop()` with per-iteration try/except
  - tests/unit/services/bot/test_scheduler_loop.py - remove xfail markers from the two Task 1.1 tests; rewrite the four `asyncpg.connect`-patching tests to patch `listen_with_reconnect` instead
- **Success**:
  - `services/bot/scheduler_loop.py` no longer imports/calls `asyncpg.connect` or `add_listener` directly; it imports `listen_with_reconnect` from `shared.pg_listen`
  - `uv run pytest tests/unit/services/bot/test_scheduler_loop.py -v` — all tests pass, 0 xfail, 0 failures
  - `uv run mypy shared/ services/` passes with no new errors attributable to this file
- **Research References**:
  - .copilot-tracking/research/20260715-02-background-task-silent-failure-audit-research.md (Lines 159-167) - Recommended Approach for finding #1
  - .copilot-tracking/research/20260715-02-background-task-silent-failure-audit-research.md (Lines 169-179) - Implementation Guidance: key tasks, dependencies, success criteria
  - Source: shared/pg_listen.py (Lines 36-96) - `listen_with_reconnect()` signature and behavior being delegated to
  - Source: services/bot/bot_action_listener.py (Lines 106-118) - reference delegation pattern (`start()` body)
- **Dependencies**:
  - Task 1.1 completion (tests must exist and show `xfailed` first)

### Task 1.3: Refactor and add SchedulerLoop edge-case coverage

With the migration green, add coverage the RED-phase tests did not need to
prove the bug, following `.github/instructions/unit-tests.instructions.md`
(no coverage theater — each new test must have a falsifiable assertion):

- A test that `run()`'s `TaskGroup`/`gather` propagates `CancelledError` and
  the task can be cleanly cancelled from outside (mirrors the cancellation
  coverage already present in `tests/unit/shared/test_pg_listen.py`'s
  `TestListenWithReconnectInitialConnect.test_cancellation_closes_connection`,
  adapted to assert the `SchedulerLoop` task itself raises
  `CancelledError` on `task.cancel()`).
- A test that a second consecutive exception in `_get_next_due_item` is also
  survived (not just the first), proving the `try/except` is inside the
  `while True:`, not wrapping it once from the outside.

Run the full unit suite and mypy as the phase gate before moving to Phase 2:

- `uv run pytest tests/unit` (never `--testmon` manually per `CLAUDE.md`)
- `uv run mypy shared/ services/`

- **Files**:
  - tests/unit/services/bot/test_scheduler_loop.py - add the two edge-case tests described above
- **Success**:
  - New edge-case tests pass with real assertions (not `assert True`)
  - `uv run pytest tests/unit` passes in full
  - `uv run mypy shared/ services/` passes with no new errors
- **Research References**:
  - .copilot-tracking/research/20260715-02-background-task-silent-failure-audit-research.md (Lines 179) - Success Criteria: self-heal from both dropped-connection and unhandled-exception without process restart
- **Dependencies**:
  - Task 1.2 completion

## Phase 2: AnnouncementLoop reconnect migration

### Task 2.1: Write failing regression test for AnnouncementLoop delegation (RED)

`AnnouncementLoop.start()` already wraps its per-iteration body in
`try/except Exception: logger.exception(...)` — that part is correct and
must not change. The bug is entirely in connection handling: a raw
`asyncpg.connect()` with no reconnect-on-termination (silently degrades to
polling at `MAX_TIMEOUT` = 3600s forever), and an outer
`try/except Exception: logger.exception("AnnouncementLoop failed: could not
establish database connection")` around the initial connect that swallows a
startup failure permanently (`start()` just returns). This is a bug fix — no
stub, `xfail(strict=True)` per the same TDD workflow as Phase 1.

Add one new test to `tests/unit/bot/test_announcement_loop.py`:

- `test_start_delegates_to_listen_with_reconnect` — patches
  `services.bot.announcement_loop.listen_with_reconnect` with an `AsyncMock`,
  runs `start()` as a background task, and asserts it was awaited with
  `(loop._db_url, "game_announcement_changed", loop._on_notify)` — model
  directly on `tests/unit/bot/test_bot_action_listener.py`'s
  `TestStart.test_start_delegates_to_listen_with_reconnect`. Cancel and await
  the task the same way `test_announcement_loop_start_closes_connection_on_cancel`
  already does.

Mark it `@pytest.mark.xfail(strict=True, reason="Bug: AnnouncementLoop.start()
opens a raw asyncpg connection with no reconnect-on-loss and swallows initial
connect failures — same root cause as 5f051fb3")`. Run `uv run pytest
tests/unit/bot/test_announcement_loop.py -v` and confirm it shows `xfailed`.

- **Files**:
  - tests/unit/bot/test_announcement_loop.py - add the new xfail test described above
- **Success**:
  - New test exists with a real assertion on the delegation call arguments
  - `uv run pytest tests/unit/bot/test_announcement_loop.py -v` shows the new test as `xfailed`, all pre-existing tests still pass
- **Research References**:
  - .copilot-tracking/research/20260715-02-background-task-silent-failure-audit-research.md (Lines 20-21) - AnnouncementLoop finding (no reconnect, swallowed startup failure, no retry)
  - .copilot-tracking/research/20260715-02-background-task-silent-failure-audit-research.md (Lines 83) - Findings Inventory #2 severity/detail
  - Source: tests/unit/bot/test_bot_action_listener.py (Lines 395-419) - `TestStart` reference pattern
- **Dependencies**:
  - Phase 1 completion

### Task 2.2: Migrate AnnouncementLoop.start() to listen_with_reconnect, keep loop body unchanged (GREEN)

Split `start()` the same way as `SchedulerLoop.run()` in Task 1.2: connection
lifecycle delegated to `listen_with_reconnect()`, the existing `while True:`
loop body (with its already-correct per-iteration `try/except`) runs
independently and concurrently, since it only depends on `self._wake_event`,
not the connection object.

Target shape (adapt naming to fit; keep the existing loop body's logic and
log messages byte-for-byte — only the surrounding scaffolding changes):

```python
async def start(self) -> None:
    """Maintain the LISTEN connection and run the announcement loop concurrently."""
    async with asyncio.TaskGroup() as tg:
        tg.create_task(
            listen_with_reconnect(self._db_url, "game_announcement_changed", self._on_notify)
        )
        tg.create_task(self._run_loop())

async def _run_loop(self) -> None:
    """Poll for and post due announcements, surviving per-iteration errors."""
    while True:
        try:
            await self._process_due()
            next_due = await self._next_due_time()
            if next_due is not None:
                wait = max(
                    0.0,
                    (next_due - datetime.datetime.now(datetime.UTC).replace(tzinfo=None)).total_seconds(),
                )
            else:
                wait = float(self.MAX_TIMEOUT)
            wait = min(wait, float(self.MAX_TIMEOUT))
            logger.debug("AnnouncementLoop sleeping %.1fs (next_due=%s)", wait, next_due)
            self._wake_event.clear()
            with contextlib.suppress(TimeoutError):
                await asyncio.wait_for(self._wake_event.wait(), timeout=wait)
            logger.debug(
                "AnnouncementLoop woke up (reason=%s)",
                "notify" if self._wake_event.is_set() else "timeout",
            )
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("AnnouncementLoop: error in loop iteration, retrying")
```

This removes both the raw `asyncpg.connect()` call and the outer
`try/except Exception: logger.exception("AnnouncementLoop failed: could not
establish database connection")` — `listen_with_reconnect` already retries
the initial connect indefinitely (see
`tests/unit/shared/test_pg_listen.py::TestListenWithReconnectOnConnectError`),
closing that gap for free, as the research's Recommended Approach states.
Also remove the now-dead `conn: asyncpg.Connection | None = None` /
`finally: if conn is not None: await conn.close()` scaffolding — connection
close-on-teardown is `listen_with_reconnect`'s responsibility now (already
tested in `test_pg_listen.py`).

Remove the `xfail` marker added in Task 2.1.

Update the three pre-existing tests in `tests/unit/bot/test_announcement_loop.py`
that patch `services.bot.announcement_loop.asyncpg.connect` directly:

- `test_announcement_loop_start_closes_connection_on_cancel` (currently lines 168-193)
- `test_announcement_loop_start_logs_sleep_and_wake` (currently lines 196-232)
- `test_announcement_loop_start_retries_after_transient_error` (currently lines 235-264)

`test_announcement_loop_start_closes_connection_on_cancel` specifically
asserts `mock_conn.close.assert_awaited_once()` — that assertion no longer
applies to `AnnouncementLoop` directly (connection-close-on-cancel is now
`listen_with_reconnect`'s tested responsibility). Rewrite it to assert what
`start()` itself is responsible for: that cancelling the task raises
`CancelledError` and the `_run_loop` task is not left dangling (e.g. assert
`task.cancelled()` is not needed since gather/TaskGroup re-raises; assert the
patched `_process_due` was awaited before cancellation, proving the loop
actually started). For the other two, replace
`patch("services.bot.announcement_loop.asyncpg.connect", ...)` with
`patch("services.bot.announcement_loop.listen_with_reconnect",
new=AsyncMock(side_effect=lambda *a, **k: asyncio.Event().wait()))` (same
permanently-pending stand-in used in Task 1.2) so the per-iteration body
assertions (`process_calls == 2`, the sleep/wake logging) still exercise
`_run_loop` exactly as before.

Run `uv run pytest tests/unit/bot/test_announcement_loop.py -v` and confirm
all tests pass (the Task 2.1 test now green; the three rewritten tests
green; `_process_due`/`_announce`/`_on_notify`/`_next_due_time` tests, which
never touched `asyncpg.connect`, unchanged and still green).

- **Files**:
  - services/bot/announcement_loop.py - split `start()` into connection delegation + independent `_run_loop()`; remove raw `asyncpg.connect()`/outer swallow-and-return try/except
  - tests/unit/bot/test_announcement_loop.py - remove xfail marker from the Task 2.1 test; rewrite the three `asyncpg.connect`-patching tests
- **Success**:
  - `services/bot/announcement_loop.py` no longer imports/calls `asyncpg.connect` directly in `start()`; imports `listen_with_reconnect` from `shared.pg_listen`
  - The outer "AnnouncementLoop failed: could not establish database connection" swallow-and-return branch no longer exists
  - `uv run pytest tests/unit/bot/test_announcement_loop.py -v` — all tests pass, 0 xfail, 0 failures
  - `uv run mypy shared/ services/` passes with no new errors attributable to this file
- **Research References**:
  - .copilot-tracking/research/20260715-02-background-task-silent-failure-audit-research.md (Lines 164) - Recommended Approach for finding #2 (keep per-iteration try/except unchanged)
  - .copilot-tracking/research/20260715-02-background-task-silent-failure-audit-research.md (Lines 156) - Technical Requirement: must not change the one-shot `hasattr` guard behavior for listeners that never return — `bot.py` is not touched by this phase
  - Source: shared/pg_listen.py (Lines 36-96) - `listen_with_reconnect()` retries initial connect indefinitely
- **Dependencies**:
  - Task 2.1 completion

### Task 2.3: Refactor and add AnnouncementLoop edge-case coverage

Add coverage beyond what the RED-phase test needed:

- A test verifying `MAX_TIMEOUT` (3600s) is still used as the sleep ceiling
  when no game is due and the LISTEN connection is otherwise healthy (extend
  or add alongside `test_announcement_loop_start_logs_sleep_and_wake`),
  confirming `docs/developer/architecture.md`'s documented polling-ceiling
  behavior is preserved as a fallback, not broken by the refactor.
- A test that `start()` does not return/swallow on a second consecutive
  connect-level disruption — i.e. that the loop body keeps running across
  what would previously have been a fatal outer-catch event now that the
  outer catch is gone.

Run the full unit suite and mypy as the phase gate before moving to Phase 3:

- `uv run pytest tests/unit`
- `uv run mypy shared/ services/`

- **Files**:
  - tests/unit/bot/test_announcement_loop.py - add the edge-case tests described above
- **Success**:
  - New edge-case tests pass with real assertions
  - `uv run pytest tests/unit` passes in full
  - `uv run mypy shared/ services/` passes with no new errors
- **Research References**:
  - .copilot-tracking/research/20260715-02-background-task-silent-failure-audit-research.md (Lines 153) - Technical Requirement: preserve documented 900s/3600s polling ceilings as fallback, not the only recovery path
- **Dependencies**:
  - Task 2.2 completion

## Phase 3: _channel_worker per-iteration exception handling

### Task 3.1: Write failing regression test for _channel_worker resilience (RED)

`_channel_worker()`'s `while True:` body (dequeue → rate-limit claim →
edit-with-backoff → delete/commit) has no exception handling; only the
`finally` cleans up `_channel_workers`. A transient DB error during dequeue
or delete currently kills the task outright, self-healing only on the next
`on_ready`/`on_resumed` Gateway event. This is a bug fix — no stub,
`xfail(strict=True)`.

Add one new test to `tests/unit/services/bot/events/test_handlers_channel_worker.py`
(the active, non-stale test module for this method — confirmed via `git log`
that `test_channel_worker.py` in the same directory is an older/parallel
file; only `test_handlers_channel_worker.py`'s `TestChannelWorker` class,
which uses the shared `event_handlers` fixture from this directory's
`conftest.py`, needs the new/updated tests below):

- `test_continues_after_transient_exception_in_loop_body` — patches
  `_fetch_next_queued_game` with `side_effect=[game_id_1, RuntimeError("transient
DB error"), game_id_2, None]` (or equivalent bounded sequence — the
  exception must NOT be the sole/repeating side effect, or a correct
  catch-and-continue implementation would loop forever against a mock that
  always raises), patches `get_redis_client`/`_edit_with_backoff` as the
  existing tests in this file do, and asserts: (a) `_channel_worker` does
  **not** raise, (b) `_fetch_next_queued_game` was awaited 4 times (proving
  the loop survived the exception and continued to `game_id_2` and then the
  terminating `None`), and (c) `chan1` was removed from
  `event_handlers._channel_workers` afterward (the `finally` still runs).

Mark it `@pytest.mark.xfail(strict=True, reason="Bug: _channel_worker has no
exception handling around the loop body — a transient error kills the
worker task, same root cause as 5f051fb3")`. Run `uv run pytest
tests/unit/services/bot/events/test_handlers_channel_worker.py -v` and
confirm it shows `xfailed`.

- **Files**:
  - tests/unit/services/bot/events/test_handlers_channel_worker.py - add the new xfail test described above
- **Success**:
  - New test exists with real assertions (not-raises + call-count + cleanup, not just "ran without asserting")
  - `uv run pytest tests/unit/services/bot/events/test_handlers_channel_worker.py -v` shows the new test as `xfailed`, all pre-existing tests still pass
- **Research References**:
  - .copilot-tracking/research/20260715-02-background-task-silent-failure-audit-research.md (Lines 25-28) - `_channel_worker` finding: no try/except, self-heals only on next Gateway event
  - .copilot-tracking/research/20260715-02-background-task-silent-failure-audit-research.md (Lines 85) - Findings Inventory #4
  - Source: services/bot/events/handlers.py (Lines 1482-1512) - `_edit_with_backoff`'s existing broad-catch pattern, the project's own established pattern for this exact class of loop
- **Dependencies**:
  - Phase 2 completion

### Task 3.2: Wrap _channel_worker loop body in try/except, update the exception-propagation test (GREEN)

Wrap the loop body in a `try/except Exception: logger.exception(...);
continue`, without disturbing the existing `finally` cleanup of
`_channel_workers`, matching `_edit_with_backoff`'s established pattern one
level deeper in the same call stack:

```python
async def _channel_worker(self, discord_channel_id: str) -> None:
    attempt_counts: dict[str, int] = {}
    try:
        while True:
            try:
                game_id = await self._fetch_next_queued_game(discord_channel_id)
                if game_id is None:
                    break

                redis = await get_redis_client()
                wait_ms = await redis.claim_channel_rate_limit_slot(discord_channel_id)
                t_cut = await self._edit_with_backoff(discord_channel_id, game_id, wait_ms)
                if t_cut is None:
                    attempt_counts[game_id] = attempt_counts.get(game_id, 0) + 1
                    if attempt_counts[game_id] < _MAX_EDIT_ATTEMPTS:
                        continue
                    logger.error(
                        "Dropping game %s from refresh queue after %d failed attempts",
                        game_id,
                        _MAX_EDIT_ATTEMPTS,
                    )
                    t_cut = datetime.now(tz=UTC)

                attempt_counts.pop(game_id, None)
                async with get_db_session() as db:
                    await db.execute(
                        delete(MessageRefreshQueue).where(
                            MessageRefreshQueue.channel_id == discord_channel_id,
                            MessageRefreshQueue.game_id == game_id,
                            MessageRefreshQueue.enqueued_at <= t_cut,
                        )
                    )
                    await db.commit()
            except Exception:
                logger.exception(
                    "Unexpected error in channel worker loop body for channel %s, retrying",
                    discord_channel_id,
                )
                continue
    finally:
        self._channel_workers.pop(discord_channel_id, None)
```

`break`/`continue` used for normal control flow inside the loop are
unaffected by the added `except Exception:` — only actual exceptions are
caught there.

Remove the `xfail` marker added in Task 3.1.

Update the pre-existing `test_removes_channel_from_workers_on_exception`
test (currently `tests/unit/services/bot/events/test_handlers_channel_worker.py`
lines 143-156), which currently asserts the opposite of the fixed behavior —
`with pytest.raises(RuntimeError): await event_handlers._channel_worker("chan1")`
against a `_fetch_next_queued_game` mock whose `side_effect` is a bare
`RuntimeError(...)` (raises on every call). Per the phase-isolation
"ordering rule," this caller/test must be updated in this same task, not a
later one — left as-is it would encode now-incorrect behavior and, worse, a
bare-exception `side_effect` combined with a correct `continue`-based fix
would make this specific test hang the suite (the mock never returns `None`
to break the loop). Rewrite it to:

```python
@pytest.mark.asyncio
async def test_removes_channel_from_workers_on_exception(self, event_handlers) -> None:
    """_channel_workers entry is cleaned up even after the worker retries past an exception."""
    event_handlers._channel_workers["chan1"] = MagicMock()

    with patch.object(
        event_handlers,
        "_fetch_next_queued_game",
        new=AsyncMock(side_effect=[RuntimeError("boom"), None]),
    ):
        await event_handlers._channel_worker("chan1")  # no longer raises

    assert "chan1" not in event_handlers._channel_workers
```

Run `uv run pytest tests/unit/services/bot/events/test_handlers_channel_worker.py -v`
and confirm all tests pass (Task 3.1 test now green; the rewritten
`test_removes_channel_from_workers_on_exception` green; the four other
pre-existing tests in this file, which never depended on exception
propagation, unchanged and still green).

- **Files**:
  - services/bot/events/handlers.py - wrap `_channel_worker`'s loop body (lines 1421-1449 currently) in `try/except Exception: logger.exception(...); continue`
  - tests/unit/services/bot/events/test_handlers_channel_worker.py - remove xfail marker from the Task 3.1 test; rewrite `test_removes_channel_from_workers_on_exception`
- **Success**:
  - `_channel_worker`'s loop body no longer lets an exception from `_fetch_next_queued_game`, `get_redis_client`, `claim_channel_rate_limit_slot`, or the delete/commit propagate out of the method
  - The `finally: self._channel_workers.pop(discord_channel_id, None)` cleanup is unchanged and still fires on every exit path
  - `uv run pytest tests/unit/services/bot/events/test_handlers_channel_worker.py -v` — all tests pass, 0 xfail, 0 failures
  - `uv run mypy shared/ services/` passes with no new errors attributable to this file
- **Research References**:
  - .copilot-tracking/research/20260715-02-background-task-silent-failure-audit-research.md (Lines 165) - Recommended Approach for finding #4 (exact wrapping guidance, do not disturb `finally`)
  - .copilot-tracking/research/20260715-02-background-task-silent-failure-audit-research.md (Lines 175) - Implementation Guidance key task for `_channel_worker`
  - Source: services/bot/events/handlers.py (Lines 1408-1451) - current unguarded implementation being wrapped
- **Dependencies**:
  - Task 3.1 completion

### Task 3.3: Refactor, add edge-case coverage, and run full-suite/integration verification

Add coverage beyond what the RED-phase test needed:

- A test that an exception during the `redis.claim_channel_rate_limit_slot`
  call (not just `_fetch_next_queued_game`) is also caught and the loop
  continues, since the wrapping `try/except` covers the whole body, not just
  the fetch step.
- A test that `attempt_counts` does not leak/grow unbounded across a caught
  exception followed by a successful edit for the same `game_id` (the
  `attempt_counts.pop(game_id, None)` on the success path still runs after a
  prior caught exception for a different game).

This is the last phase touching production code in this plan. Before
considering the overall task complete, run the full verification suite:

- `uv run pytest tests/unit` (full suite, never `--testmon` manually per `CLAUDE.md`)
- `uv run mypy shared/ services/`
- `scripts/run-integration-tests.sh tests/integration/test_scheduler_loop.py |& tee output-integration.txt`
  per `.github/instructions/test-execution.instructions.md` (capture full
  output with `tee` before filtering; allow at least 10 minutes) — this
  integration suite runs `SchedulerLoop.run()` in-process against real
  PostgreSQL and was not modified by this plan, so it must still pass
  unchanged, proving the `listen_with_reconnect`/`TaskGroup` migration in
  Phase 1 did not break real-connection behavior
- `git diff --stat services/bot/bot.py` — confirm empty/no changes, proving
  the one-shot `hasattr` startup guard (deferred finding #3, explicitly
  out of scope) was not touched
- Confirm no `spawn_supervised()`-style helper or new cross-cutting
  `create_task` wrapper was introduced anywhere (deferred finding #5,
  explicitly out of scope)

- **Files**:
  - tests/unit/services/bot/events/test_handlers_channel_worker.py - add the two edge-case tests described above
- **Success**:
  - New edge-case tests pass with real assertions
  - `uv run pytest tests/unit` passes in full
  - `uv run mypy shared/ services/` passes with no new errors
  - `scripts/run-integration-tests.sh tests/integration/test_scheduler_loop.py` passes
  - `services/bot/bot.py` has zero diff from this plan's work
  - No new supervisor/restart-policy or task-death-observability helper exists in the diff
- **Research References**:
  - .copilot-tracking/research/20260715-02-background-task-silent-failure-audit-research.md (Lines 179) - overall Success Criteria: all three components self-heal from dropped connection and unhandled exception; new unit tests cover both failure modes; documented latency/polling behavior preserved; no changes to #3/#5-scoped code
  - .copilot-tracking/research/20260715-02-background-task-silent-failure-audit-research.md (Lines 157) - explicit out-of-scope statement for findings #3 and #5
- **Dependencies**:
  - Task 3.2 completion

## Dependencies

- `shared/pg_listen.py`'s `listen_with_reconnect()` (already implemented, unchanged by this plan)
- `tests/unit/shared/test_pg_listen.py` and `tests/unit/bot/test_bot_action_listener.py` as the established reconnect-behavior test templates
- Python 3.13 stdlib `asyncio.TaskGroup` (or `asyncio.gather`, matching existing project convention) for running connection-lifecycle and loop-body coroutines concurrently
- `uv run pytest tests/unit` (never `pytest --testmon` manually — see `CLAUDE.md`'s testmon warning)
- `uv run mypy shared/ services/`
- `scripts/run-integration-tests.sh` for `tests/integration/test_scheduler_loop.py` (unmodified by this plan; must still pass)

## Success Criteria

- `SchedulerLoop.run()`, `AnnouncementLoop.start()`, and
  `EventHandlers._channel_worker()` each survive (a) a dropped/terminated
  LISTEN connection (for the two listeners) and (b) an unhandled exception
  during a single loop iteration, without requiring a bot process restart
- New unit tests cover both failure modes for each of the three components,
  written test-first per the TDD-for-bug-fixes workflow (xfail → fix →
  xfail removed)
- All pre-existing tests that depended on the old raw-`asyncpg.connect()`
  implementation detail or on exceptions propagating out of `_channel_worker`
  are updated in the same phase as the corresponding production change, not
  left broken or deferred
- `docs/developer/architecture.md`'s documented sub-10-second NOTIFY latency
  and 900s/3600s polling ceilings remain accurate as fallback behavior, not
  the only recovery path
- `services/bot/bot.py`'s one-shot `hasattr` startup guards and the deferred
  findings #3 (generalized supervisor/restart-policy) and #5
  (`spawn_supervised()`-style observability helper) are untouched
- `uv run pytest tests/unit`, `uv run mypy shared/ services/`, and
  `scripts/run-integration-tests.sh tests/integration/test_scheduler_loop.py`
  all pass at the end of Phase 3
