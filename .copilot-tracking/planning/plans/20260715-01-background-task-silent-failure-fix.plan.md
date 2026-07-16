---
applyTo: '.copilot-tracking/changes/20260715-01-background-task-silent-failure-fix-changes.md'
---

<!-- markdownlint-disable-file -->

# Task Checklist: Background-Task Silent-Failure Fix

## Overview

Migrate `SchedulerLoop` and `AnnouncementLoop` to the already-proven `listen_with_reconnect()` helper and add per-iteration exception handling to `SchedulerLoop` and `_channel_worker`, closing the two remaining "transient error → permanent silent stop until process restart" gaps that share the exact root cause fixed in `5f051fb3`, plus the analogous unguarded-loop gap in `_channel_worker`.

## Objectives

- `SchedulerLoop.run()` (all 3 instances via `services/bot/bot.py`) reconnects automatically on a dropped/terminated LISTEN connection and survives an unhandled exception during any single due-item iteration
- `AnnouncementLoop.start()` reconnects automatically on a dropped/terminated LISTEN connection, and no longer permanently swallows an initial-connect failure with no retry
- `EventHandlers._channel_worker()` survives an unhandled exception during any single loop iteration without dying, while preserving its existing `finally`-based `_channel_workers` cleanup
- Every new/changed behavior is covered by unit tests written test-first (RED → GREEN → REFACTOR), and every pre-existing test that encoded the old, now-incorrect behavior is updated in the same phase as the production change it tests
- No changes to the deferred findings: the one-shot `hasattr` startup guard in `services/bot/bot.py` (finding #3), or a cross-cutting task-death observability helper (finding #5)

## Research Summary

### Project Files

- `shared/pg_listen.py` - `listen_with_reconnect()`, the already-shipped fix (`5f051fb3`) being extended to two more components
- `services/bot/scheduler_loop.py` - `SchedulerLoop.run()`, finding #1 (High severity), not migrated, zero exception handling
- `services/bot/announcement_loop.py` - `AnnouncementLoop.start()`, finding #2 (High severity), not migrated, per-iteration body already correct
- `services/bot/events/handlers.py` - `EventHandlers._channel_worker()` (lines 1408-1451), finding #4 (Medium severity), no exception handling around the loop body
- `services/bot/bot_action_listener.py` - reference implementation of the delegation pattern (`start()` → `listen_with_reconnect`)
- `tests/unit/shared/test_pg_listen.py` - reconnect-behavior test template (added in `5f051fb3`)
- `tests/unit/bot/test_bot_action_listener.py` - `TestStart` delegation-test template
- `tests/unit/services/bot/test_scheduler_loop.py`, `tests/unit/bot/test_announcement_loop.py`, `tests/unit/services/bot/events/test_handlers_channel_worker.py` - existing unit test modules to extend and partially rewrite
- `tests/integration/test_scheduler_loop.py` - existing integration test to run (not modify) as a final gate

### External References

- .copilot-tracking/research/20260715-02-background-task-silent-failure-audit-research.md - full audit: findings inventory, recommended approach, implementation guidance, technical requirements

### Standards References

- .github/instructions/test-driven-development.instructions.md - "TDD for Bug Fixes" workflow (no stub, xfail-then-fix) governs all three phases below
- .github/instructions/unit-tests.instructions.md - falsifiable-assertion requirements for every new/rewritten test
- .github/instructions/python.instructions.md - Python style/typing conventions for the production code changes
- .github/instructions/test-execution.instructions.md - rules for invoking `scripts/run-integration-tests.sh` (tee output, minimum timeout)

## Implementation Checklist

### [x] Phase 1: SchedulerLoop reconnect + per-iteration exception handling

- [x] Task 1.1: Write failing regression tests for SchedulerLoop resilience (RED)
  - Details: .copilot-tracking/planning/details/20260715-01-background-task-silent-failure-fix-details.md (Lines 11-66)

- [x] Task 1.2: Migrate SchedulerLoop.run() to listen_with_reconnect and add per-iteration exception handling (GREEN)
  - Details: .copilot-tracking/planning/details/20260715-01-background-task-silent-failure-fix-details.md (Lines 67-172)

- [x] Task 1.3: Refactor and add SchedulerLoop edge-case coverage
  - Details: .copilot-tracking/planning/details/20260715-01-background-task-silent-failure-fix-details.md (Lines 173-204)

### [x] Phase 2: AnnouncementLoop reconnect migration

- [x] Task 2.1: Write failing regression test for AnnouncementLoop delegation (RED)
  - Details: .copilot-tracking/planning/details/20260715-01-background-task-silent-failure-fix-details.md (Lines 207-246)

- [x] Task 2.2: Migrate AnnouncementLoop.start() to listen_with_reconnect, keep loop body unchanged (GREEN)
  - Details: .copilot-tracking/planning/details/20260715-01-background-task-silent-failure-fix-details.md (Lines 247-350)

- [x] Task 2.3: Refactor and add AnnouncementLoop edge-case coverage
  - Details: .copilot-tracking/planning/details/20260715-01-background-task-silent-failure-fix-details.md (Lines 351-380)

### [ ] Phase 3: _channel_worker per-iteration exception handling

- [ ] Task 3.1: Write failing regression test for _channel_worker resilience (RED)
  - Details: .copilot-tracking/planning/details/20260715-01-background-task-silent-failure-fix-details.md (Lines 383-428)

- [ ] Task 3.2: Wrap _channel_worker loop body in try/except, update the exception-propagation test (GREEN)
  - Details: .copilot-tracking/planning/details/20260715-01-background-task-silent-failure-fix-details.md (Lines 429-534)

- [ ] Task 3.3: Refactor, add edge-case coverage, and run full-suite/integration verification
  - Details: .copilot-tracking/planning/details/20260715-01-background-task-silent-failure-fix-details.md (Lines 535-581)

## Dependencies

- `shared/pg_listen.py`'s `listen_with_reconnect()` (already implemented; unchanged by this plan)
- Python 3.13 stdlib `asyncio.TaskGroup` (or `asyncio.gather`, matching the project's existing convention) for running connection-lifecycle and loop-body coroutines concurrently
- `uv run pytest tests/unit` (never `pytest --testmon` manually per `CLAUDE.md`)
- `uv run mypy shared/ services/`
- `scripts/run-integration-tests.sh` for `tests/integration/test_scheduler_loop.py`

## Success Criteria

- `SchedulerLoop.run()`, `AnnouncementLoop.start()`, and `EventHandlers._channel_worker()` each self-heal from a dropped/terminated LISTEN connection (the two listeners) and from an unhandled exception during a single loop iteration (all three), without requiring a process restart
- All new behavior was proven with a failing (`xfail`) regression test before being implemented, per the TDD-for-bug-fixes workflow
- Every pre-existing test that depended on the old raw-connection implementation detail, or on an exception propagating out of `_channel_worker`, was updated in the same phase as the corresponding production change
- `docs/developer/architecture.md`'s documented sub-10-second NOTIFY latency and 900s/3600s polling ceilings remain accurate as fallback behavior only
- `services/bot/bot.py` and any cross-cutting task-spawn helper are untouched (deferred findings #3 and #5 remain out of scope)
- `uv run pytest tests/unit`, `uv run mypy shared/ services/`, and `scripts/run-integration-tests.sh tests/integration/test_scheduler_loop.py` all pass after Phase 3
