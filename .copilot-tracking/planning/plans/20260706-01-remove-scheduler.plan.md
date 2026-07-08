---
applyTo: '.copilot-tracking/changes/20260706-01-remove-scheduler-changes.md'
---

<!-- markdownlint-disable-file -->

# Task Checklist: Remove Scheduler Service

## Overview

Replace the standalone scheduler container with `SchedulerLoop` asyncio tasks running inside the bot service, then delete the scheduler service entirely.

## Objectives

- Eliminate the `scheduler` container and `docker/scheduler.Dockerfile`
- Implement `SchedulerLoop` (async asyncpg-based replacement for `SchedulerDaemon`) in `services/bot/`
- Move `event_builders.py` and `participant_action_event_builder.py` to `shared/services/` before the scheduler directory is deleted
- Remove `scheduler` from all compose files (`compose.yaml`, `compose.int.yaml`, `compose.e2e.yaml`, `compose.prod.yaml`, `compose.staging.yaml`)
- Preserve crash safety by keeping `bot_action_queue` as the intermediary (Option B)
- Do NOT remove `psycopg2-binary` from `pyproject.toml` (used by `services/init/`)

## Research Summary

### Project Files

- `services/scheduler/event_builders.py` — notification and status-transition event builders; move to `shared/services/`
- `services/scheduler/participant_action_event_builder.py` — participant-drop event builder; move to `shared/services/`
- `services/scheduler/scheduler_daemon_wrapper.py` — entry point starting three `SchedulerDaemon` threads; deleted in Phase 5
- `services/scheduler/generic_scheduler_daemon.py` — sync psycopg2 daemon; replaced by async `SchedulerLoop`
- `services/scheduler/postgres_listener.py` — `PostgresNotificationListener`; used by integration tests; moved to test utility
- `services/bot/bot.py` — `on_ready` wires `BotActionListener`, `MessageRefreshListener`, `AnnouncementLoop` as asyncio tasks; `SchedulerLoop` tasks added here in Phase 4
- `tests/unit/services/scheduler/` — 7 unit test files; all deleted in Phase 5
- `tests/integration/test_notification_daemon.py`, `test_status_transitions.py`, `test_participant_action_daemon.py`, `test_clone_confirmation_notification.py` — test scheduler container behavior; deleted in Phase 5 (covered by `test_scheduler_loop.py` unit tests and existing e2e)
- `tests/integration/test_message_refresh_queue.py` — uses `PostgresNotificationListener`; import updated to `tests.shared.sync_pg_listener`
- `compose.int.yaml` — `system-ready` depends on `scheduler`; updated in Phase 5

### External References

- #file:../research/20260706-01-remove-scheduler-research.md — full research findings

## Implementation Checklist

### [x] Phase 1: Move event builders to shared/

- [x] Task 1.1: Create `shared/services/event_builders.py`
  - Details: .copilot-tracking/planning/details/20260706-01-remove-scheduler-details.md (Lines 17-46)

- [x] Task 1.2: Create `shared/services/participant_action_event_builder.py`
  - Details: .copilot-tracking/planning/details/20260706-01-remove-scheduler-details.md (Lines 47-64)

- [x] Task 1.3: Update `scheduler_daemon_wrapper.py` and unit tests; delete originals
  - Details: .copilot-tracking/planning/details/20260706-01-remove-scheduler-details.md (Lines 65-89)

### [x] Phase 2: RED — SchedulerLoop stub + xfail unit tests

- [x] Task 2.1: Create `services/bot/scheduler_loop.py` stub
  - Details: .copilot-tracking/planning/details/20260706-01-remove-scheduler-details.md (Lines 93-116)

- [x] Task 2.2: Create `tests/unit/services/bot/test_scheduler_loop.py` with xfail tests
  - Details: .copilot-tracking/planning/details/20260706-01-remove-scheduler-details.md (Lines 117-167)

### [x] Phase 3: GREEN — Implement SchedulerLoop

- [x] Task 3.1: Implement `SchedulerLoop` and lift xfail markers
  - Details: .copilot-tracking/planning/details/20260706-01-remove-scheduler-details.md (Lines 170-199)

- [x] Task 3.2: Create `tests/integration/test_scheduler_loop.py`
  - Details: .copilot-tracking/planning/details/20260706-01-remove-scheduler-details.md (Lines 200-234)

### [x] Phase 4: Wire SchedulerLoop into bot.py

- [x] Task 4.1: Import and start three `SchedulerLoop` tasks in `bot.py` `on_ready`
  - Details: .copilot-tracking/planning/details/20260706-01-remove-scheduler-details.md (Lines 237-297)

- [x] Task 4.2: Add unit tests for SchedulerLoop wiring in `test_bot.py`
  - Details: .copilot-tracking/planning/details/20260706-01-remove-scheduler-details.md (Lines 298-314)

### [x] Phase 5: Delete scheduler service

- [x] Task 5.1: Move `PostgresNotificationListener` to `tests/shared/sync_pg_listener.py`
  - Details: .copilot-tracking/planning/details/20260706-01-remove-scheduler-details.md (Lines 317-340)

- [x] Task 5.2: Delete scheduler unit tests and integration tests that test the scheduler container
  - Details: .copilot-tracking/planning/details/20260706-01-remove-scheduler-details.md (Lines 341-371)

- [x] Task 5.3: Delete `services/scheduler/` directory
  - Details: .copilot-tracking/planning/details/20260706-01-remove-scheduler-details.md (Lines 372-388)

- [x] Task 5.4: Remove `scheduler` from all compose files and delete `scheduler.Dockerfile`
  - Details: .copilot-tracking/planning/details/20260706-01-remove-scheduler-details.md (Lines 389-434)

## Dependencies

- asyncpg (already used by bot)
- sqlalchemy async session (already used by bot)
- `shared.models.NotificationSchedule`, `GameStatusSchedule`, `ParticipantActionSchedule` (already in shared.models)
- RabbitMQ removal complete (confirmed in research — no prerequisite work)

## Success Criteria

- `services/scheduler/` directory does not exist
- `docker/scheduler.Dockerfile` does not exist
- `scheduler` service absent from all compose files
- `uv run pytest tests/unit` passes
- `uv run mypy shared/ services/` passes
- `tests/integration/test_scheduler_loop.py` passes for all three schedule paths (notification, status transition, participant action)
- Integration tests pass (scheduler-specific container tests deleted; message_refresh_queue test updated)
- E2E tests pass (SchedulerLoop in bot handles notification DMs, status transitions, participant drops)
