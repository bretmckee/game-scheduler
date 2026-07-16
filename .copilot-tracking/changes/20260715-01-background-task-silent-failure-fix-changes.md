# Changes: Background-Task Silent-Failure Fix

## Summary

Migrate `SchedulerLoop` and `AnnouncementLoop` to `listen_with_reconnect()` and
add per-iteration exception handling to `SchedulerLoop` and `_channel_worker`,
closing the remaining "transient error → permanent silent stop" gaps sharing
the root cause fixed in `5f051fb3`.

## Added

## Modified

- `services/bot/scheduler_loop.py` — `SchedulerLoop.run()` split into
  connection lifecycle (delegated to `listen_with_reconnect`) and an
  independent `_run_loop()` due-item cycle with per-iteration
  try/except, run concurrently via `asyncio.TaskGroup`.
- `tests/unit/services/bot/test_scheduler_loop.py` — removed the two
  `xfail` markers from Task 1.1; rewrote the four tests that patched
  `asyncpg.connect` directly to instead patch `listen_with_reconnect`.
- `tests/unit/bot/test_bot_ready.py` — `_make_bot()` now pre-sets
  `_scheduler_loops_started = True` (see Task 1.2 note below).

## Added (edge-case coverage)

- `tests/unit/services/bot/test_scheduler_loop.py` —
  `test_run_propagates_cancellation` and
  `test_run_survives_two_consecutive_exceptions_in_iteration` (Task 1.3).

## Phase 1 Progress

### Task 1.1: RED — SchedulerLoop resilience regression tests

- `tests/unit/services/bot/test_scheduler_loop.py` — added
  `test_run_delegates_to_listen_with_reconnect` and
  `test_run_body_continues_after_exception_in_iteration`, both marked
  `xfail(strict=True)`; confirmed both show as `xfailed` and all 10
  pre-existing tests in the file still pass.

### Task 1.2: GREEN — SchedulerLoop migrated to listen_with_reconnect

- `services/bot/scheduler_loop.py` — `run()` now runs
  `listen_with_reconnect(...)` and a new `_run_loop()` concurrently
  under `asyncio.TaskGroup`; `_run_loop()` wraps each due-item
  check/process/wait cycle in try/except, logging and continuing on
  any non-`CancelledError` exception. No longer imports/calls
  `asyncpg.connect` or `add_listener` directly.
- `tests/unit/services/bot/test_scheduler_loop.py` — removed both
  `xfail` markers (now green); rewrote
  `test_run_skips_process_item_when_not_due`,
  `test_run_calls_process_item_when_due`, `test_run_handles_no_items`,
  and `test_run_clears_notified_after_waking` to patch
  `listen_with_reconnect` (via a `_blocks_forever` async helper)
  instead of `asyncpg.connect`. Fixed a bug in the plan's suggested RED
  snippet: `AsyncMock(side_effect=lambda *a, **k: asyncio.Event().wait())`
  never actually awaits — `AsyncMock` only awaits a `side_effect` when
  it is itself a coroutine function, so a plain lambda returning an
  unawaited coroutine object gets flagged by pytest. Replaced with an
  `async def _blocks_forever(...)` helper used in all 5 places the
  pattern appears.
- `uv run pytest tests/unit/services/bot/test_scheduler_loop.py -v` —
  12 passed, 0 xfail. `uv run mypy shared/ services/` — clean.
- **Full-suite regression found and fixed** (not pre-existing —
  confirmed by running `tests/unit` on unmodified `develop`, which
  passes cleanly, both before and after this task's changes were
  stashed out): `services/bot/bot.py`'s `on_ready()` spawns 3 real
  `SchedulerLoop.run()` background tasks per call, guarded only by a
  `hasattr(self, "_scheduler_loops_started")` flag. Every test in
  `tests/unit/bot/test_bot_ready.py` calls `on_ready()` via a
  `_make_bot()` helper that pre-sets the equivalent flags for the
  other two background listeners (`_refresh_listener_started`,
  `_announcement_loop_started`) but never set
  `_scheduler_loops_started` — so every on_ready test spawned 3 real
  scheduler tasks against a `MagicMock` `database_url`. Previously
  `run()` called `asyncpg.connect()` directly, which raised immediately
  on the bogus DSN, so the leaked tasks died fast and were harmless.
  After migrating to `listen_with_reconnect()` (which is deliberately
  resilient and retries forever), those same leaked tasks never die —
  they outlive the test's event loop and get garbage-collected during
  unrelated later tests, producing `Task was destroyed but it is
pending!` errors and intermittent failures in unrelated tests
  (`test_bot_ready.py`, `test_bot_reconnect_repopulation.py`,
  `test_sweep_orphaned_embeds.py`) depending on GC timing. Fixed by
  adding `instance._scheduler_loops_started = True` to `_make_bot()`
  in `tests/unit/bot/test_bot_ready.py`, matching the existing pattern
  for the other two listeners. `services/bot/bot.py` itself was not
  modified (deferred finding #3's `hasattr` guard remains out of
  scope). Verified stable across 5 consecutive full-suite runs with
  default random test ordering after the fix (2371 passed each time,
  0 failed); `BotActionListener` still leaks similarly-shaped tasks on
  unmodified `develop` under the same fixture pattern (pre-existing,
  already shipped in `5f051fb3`, out of scope for this plan) but this
  did not surface as a failure in 5 repeated runs.
- `uv run pytest tests/unit -q` — 2371 passed. `uv run mypy shared/
services/` — clean.

### Task 1.3: Refactor and add SchedulerLoop edge-case coverage

- `tests/unit/services/bot/test_scheduler_loop.py` — added
  `test_run_propagates_cancellation` (asserts `task.cancel()` raises
  `CancelledError` out of `run()`'s `TaskGroup` and `task.cancelled()`
  is `True`) and `test_run_survives_two_consecutive_exceptions_in_iteration`
  (two consecutive `RuntimeError`s from `_get_next_due_item`, asserts
  `_get_next_due_item` was awaited a 3rd time and `logger.exception`
  was called at least twice — proves the try/except sits inside
  `while True:`, not wrapping the loop once from outside). No
  production code changes needed; existing implementation already
  satisfied both.
- `uv run pytest tests/unit/services/bot/test_scheduler_loop.py -v` —
  14 passed, 0 xfail, 0 failures.
- Pre-commit's `ruff` lint (`TC002`) flagged the now-type-annotation-only
  `import asyncpg` at module level; moved it into the `TYPE_CHECKING`
  block (the file already has `from __future__ import annotations`,
  so the deferred-evaluation annotation is unaffected).
- Pre-commit's `check-test-assertions` hook flagged `mock_logger` (named
  via `as mock_logger:`) in `test_run_survives_two_consecutive_exceptions_in_iteration`
  for having no `assert_*` call; added `mock_logger.exception.assert_called()`
  alongside the existing `call_count >= 2` check.
- Phase gate: `uv run pytest tests/unit -q` — 2373 passed (3
  consecutive runs, default random order). `uv run mypy shared/
services/` — clean.

## Phase 1: Complete

All three tasks done; phase gate green. Stopping for review per the
implementation prompt's default cadence before starting Phase 2
(AnnouncementLoop reconnect migration).
