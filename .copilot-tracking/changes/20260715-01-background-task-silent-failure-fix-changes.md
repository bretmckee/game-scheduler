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

## Phase 2 Progress

### Task 2.1: RED — AnnouncementLoop delegation regression test

- `tests/unit/bot/test_announcement_loop.py` — added a module-level
  `_blocks_forever` async helper (same rationale as Task 1.2: a plain
  lambda side_effect returning an unawaited coroutine gets flagged by
  pytest) and `test_start_delegates_to_listen_with_reconnect`, marked
  `xfail(strict=True)`; confirmed `xfailed`, all 9 pre-existing tests
  still pass.

### Task 2.2: GREEN — AnnouncementLoop migrated to listen_with_reconnect

- `services/bot/announcement_loop.py` — `start()` now runs
  `listen_with_reconnect(...)` and a new `_run_loop()` concurrently
  under `asyncio.TaskGroup`; `_run_loop()` is the unmodified
  loop-body logic (still its own per-iteration try/except, unchanged
  log messages). Removed the raw `asyncpg.connect()` call and the
  outer `try/except Exception: logger.exception("AnnouncementLoop
failed: could not establish database connection")` — that
  swallow-and-return-forever bug is closed for free, since
  `listen_with_reconnect` retries the initial connect indefinitely.
  Also removed the now-dead `conn`/`finally: conn.close()`
  scaffolding. Added `from __future__ import annotations` (matching
  `scheduler_loop.py`'s style) so `asyncpg` could move into the
  `TYPE_CHECKING` block per ruff's `TC002`, and dropped the
  now-unnecessary quoted `"GameSchedulerBot"` forward reference
  (ruff `UP037` auto-fix).
- `tests/unit/bot/test_announcement_loop.py` — removed the `xfail`
  marker (now green); rewrote the three tests that patched
  `asyncpg.connect` directly:
  - `test_announcement_loop_start_closes_connection_on_cancel` — no
    longer asserts `mock_conn.close`, which is now
    `listen_with_reconnect`'s tested responsibility. Rewritten to
    assert what `start()` owns: cancelling the wrapping task raises
    `CancelledError`, and `_process_due` was awaited first (proving
    the loop body actually started).
  - `test_announcement_loop_start_logs_sleep_and_wake` and
    `test_announcement_loop_start_retries_after_transient_error` —
    switched from the plan's literal suggestion (mocking
    `_process_due` to raise `asyncio.CancelledError` itself to
    terminate the loop) to external `task.cancel()`, for a
    correctness reason found empirically, not just style: a child
    task inside `asyncio.TaskGroup` raising `CancelledError`
    spontaneously (not via a real `.cancel()` on that task) does
    **not** cause the group to cancel its siblings — confirmed with a
    standalone repro (`asyncio.TaskGroup` with one always-blocked
    sibling and one child that self-raises `CancelledError` hangs
    forever, it does not propagate). The old single-connection
    `start()` didn't have this problem since there was only one
    coroutine; the new two-task `TaskGroup` shape does. Real external
    cancellation (`task.cancel()` on the task wrapping `loop.start()`)
    is delivered to whatever the group is suspended on and correctly
    cascades to both children, matching the pattern already
    established for `SchedulerLoop.run()` in Task 1.2/1.3.
  - `test_announcement_loop_start_logs_sleep_and_wake` also now
    asserts the actual "sleeping"/"woke up" log calls (with real
    argument values), which the original test's docstring promised
    but its body never checked.
- `uv run pytest tests/unit/bot/test_announcement_loop.py -v` — 10
  passed, 0 xfail. Verified stable across 5 additional repeated runs.
  `uv run ruff check`/`format --check` — clean. `uv run mypy shared/
services/` — clean.

### Task 2.3: Refactor and add AnnouncementLoop edge-case coverage

- `tests/unit/bot/test_announcement_loop.py` — added
  `test_announcement_loop_start_clamps_wait_to_max_timeout` (proves
  the `min(wait, MAX_TIMEOUT)` clamp specifically, using a `next_due`
  2 hours out so the pre-clamp value would exceed 3600s) and
  `test_announcement_loop_start_survives_two_consecutive_exceptions`
  (two consecutive `RuntimeError`s from `_process_due`; asserts
  `_process_due` was awaited a 3rd time and `logger.exception` was
  called at least twice — proving the per-iteration try/except is the
  only thing between an error and a dead loop now that the outer
  swallow-and-return catch is gone, and that it survives more than
  once in a row). `uv run pytest tests/unit/bot/test_announcement_loop.py
-v` — 12 passed, 0 xfail. Verified stable across 5 additional
  repeated runs.
- Pre-commit's `check-test-assertions` hook flagged `mock_logger`
  (named via `as mock_logger:`) in
  `test_announcement_loop_start_clamps_wait_to_max_timeout` for having
  no `assert_*` call (it only filtered `call_args_list` manually);
  replaced with `mock_logger.debug.assert_any_call(...)` against the
  exact log arguments.
- **Full-suite regression found and fixed** (confirmed not
  pre-existing the same way as Phase 1's: 5 consecutive full-suite
  runs were clean with these two files' changes stashed out, then
  flaky — 4/5 failed — with them restored):
  `tests/unit/services/bot/test_bot.py::TestGameSchedulerBot::test_on_ready_event`
  constructs a real `GameSchedulerBot` and calls `on_ready()`; it
  already patches `services.bot.bot.SchedulerLoop` (with a mock whose
  `.run` is a no-op `AsyncMock`) precisely to avoid spawning a real
  background task, but had no equivalent patch for `AnnouncementLoop`.
  Before this migration `AnnouncementLoop.start()`'s raw
  `asyncpg.connect()` failed fast against the test's real (non-mock)
  `database_url` pointing nowhere reachable, so the leaked task died
  quickly and was harmless. After migrating to `listen_with_reconnect`
  (deliberately resilient, retries forever), that leaked task now
  outlives the test and gets garbage-collected during unrelated later
  tests, same failure signature as Phase 1's finding. Fixed by adding
  `patch("services.bot.bot.AnnouncementLoop", return_value=mock_al_instance)`
  (mirroring the existing `SchedulerLoop` patch) to
  `test_on_ready_event`. `services/bot/bot.py` itself was not
  modified. Verified stable across 6 consecutive full-suite runs after
  the fix (2376 passed each time, 0 failed). `MessageRefreshListener`
  and `BotActionListener` still leak similarly-shaped tasks from this
  same test (pre-existing, already shipped before this plan, out of
  scope) but did not surface as a failure in 6 repeated runs.
- Phase gate: `uv run pytest tests/unit -q` — 2376 passed (6
  consecutive runs, default random order). `uv run mypy shared/
services/` — clean.

## Phase 2: Complete

All three tasks done; phase gate green. Stopping for review per the
implementation prompt's default cadence before starting Phase 3
(_channel_worker per-iteration exception handling).

## Phase 3 Progress

### Task 3.1: RED — _channel_worker resilience regression test

- `tests/unit/services/bot/events/test_handlers_channel_worker.py` —
  added `test_continues_after_transient_exception_in_loop_body`,
  marked `xfail(strict=True)`; confirmed `xfailed`, all 5 pre-existing
  tests still pass.

### Task 3.2: GREEN — _channel_worker loop body wrapped in try/except

- `services/bot/events/handlers.py` — `_channel_worker`'s `while
True:` body now wraps the whole dequeue/rate-limit/edit/delete cycle
  in `try/except Exception: logger.exception(...); continue`, one
  level inside the existing outer `try/finally` that cleans up
  `_channel_workers`. `break`/`continue` used for normal control flow
  are unaffected — only real exceptions are caught. No changes to the
  `finally` cleanup.
- `tests/unit/services/bot/events/test_handlers_channel_worker.py` —
  removed the Task 3.1 `xfail` marker (now green); rewrote
  `test_removes_channel_from_workers_on_exception`, which previously
  asserted the now-incorrect old behavior (`pytest.raises(RuntimeError)`
  against a `_fetch_next_queued_game` mock that raised on every call —
  left as-is, a bare-exception `side_effect` combined with the new
  `continue`-based fix would hang the suite, since the mock would never
  return `None` to break the loop). Rewritten to a bounded
  `side_effect=[RuntimeError("boom"), None]` and asserts `start()`
  no longer raises while `_channel_workers` is still cleaned up.
- `uv run pytest tests/unit/services/bot/events/test_handlers_channel_worker.py
-v` — 6 passed, 0 xfail. `uv run ruff check`/`format --check` —
  clean. `uv run mypy shared/ services/` — clean.

### Task 3.3: Refactor and add _channel_worker edge-case coverage

- `tests/unit/services/bot/events/test_handlers_channel_worker.py` —
  added:
  - `test_continues_after_exception_in_rate_limit_claim` — an
    exception from `redis.claim_channel_rate_limit_slot` (not just
    `_fetch_next_queued_game`) is also caught and the worker continues
    to the next queued game.
  - `test_attempt_counts_survives_unrelated_caught_exception` — proves
    the `attempt_counts` dict (declared outside the per-iteration
    try/except so it can track retries across iterations for the same
    `game_id`) is not disturbed by an intervening caught exception for
    a _different_ game: `game_id_1` fails twice, an unrelated
    `game_id_2` hits a caught rate-limit exception in between, then
    `game_id_1` fails a third time and correctly hits the
    `_MAX_EDIT_ATTEMPTS` drop path at exactly that point (asserted via
    exact fetch/execute call counts and the specific "Dropping game…"
    log call) — if the exception path had leaked/reset the counter,
    the drop would need more attempts and these exact assertions would
    fail.
  - No production code changes needed; the Task 3.2 implementation
    already satisfied both.
- Pre-commit's `check-test-assertions` hook flagged
  `mock_logger.exception.assert_called_once()` in
  `test_attempt_counts_survives_unrelated_caught_exception` (call
  count only, no argument check); replaced with
  `assert_called_once_with(...)` against the exact log arguments.
- Pre-commit's `complexipy` hook flagged `_channel_worker` at
  cognitive complexity 16 (limit 15, Δ +4 from the added nested
  try/except). Refactored by extracting the per-iteration body into a
  new `_drain_one_queued_game(discord_channel_id, attempt_counts) ->
bool` method (`False` = queue empty, matching the old `break`;
  `True` = keep looping, matching the old bare `continue` in the
  attempt-retry path) — `_channel_worker` is now a thin
  try/except/while wrapper, mirroring the `run()`/`_run_loop()` and
  `start()`/`_run_loop()` splits from Phases 1–2. Purely structural;
  no behavior change, so no test changes were needed — all 8 tests in
  the file still pass unmodified. `complexipy` now reports no function
  over the limit.
- `uv run pytest tests/unit/services/bot/events/test_handlers_channel_worker.py
-v` — 8 passed, 0 xfail, 0 failures.
- Phase gate: `uv run pytest tests/unit -q` — 2379 passed (3
  consecutive runs, default random order — no task-leak regression
  this time, since `_channel_worker` is only spawned on-demand via
  `_spawn_channel_worker`, not unconditionally on every `on_ready()`
  call like the three background loops in Phases 1–2).
  `uv run mypy shared/ services/` — clean. `git diff --stat
services/bot/bot.py` — empty, confirming the deferred `hasattr`
  startup guard (finding #3) was not touched. No
  `spawn_supervised()`-style helper or new cross-cutting `create_task`
  wrapper introduced anywhere in the diff (finding #5 remains out of
  scope).

## Phase 3: Complete

All three tasks done; phase gate green. This is the last phase
touching production code in this plan.
