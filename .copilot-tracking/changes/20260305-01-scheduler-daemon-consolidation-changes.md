<!-- markdownlint-disable-file -->

# Release Changes: Scheduler Daemon Consolidation

**Related Plan**: .copilot-tracking/plans/20260305-01-scheduler-daemon-consolidation.plan.md
**Implementation Date**: 2026-03-05

## Summary

Consolidate three separate scheduler daemon containers (`notification-daemon`, `status-transition-daemon`, `participant-action-daemon`) into a single `scheduler` container running all three `SchedulerDaemon` instances as threads. Reduces operational surface from 3 containers to 1 without changing scheduling behaviour.

## Changes

### Added

- `services/scheduler/scheduler_daemon_wrapper.py` — new unified entry point; starts all three `SchedulerDaemon` instances as daemon threads with a shared shutdown flag, SIGTERM/SIGINT handling, per-thread exception isolation, and telemetry flush (Phase 2)
- `tests/unit/services/scheduler/test_scheduler_daemon_wrapper.py` — 10 unit tests covering thread startup, signal handling, crash isolation, and `LOG_LEVEL` defaults (Phase 2)
- `docker/scheduler.Dockerfile` — new multi-stage Dockerfile consolidating file copies for all scheduler modules with `CMD` pointing to `scheduler_daemon_wrapper` (Phase 3)

### Modified

- `services/scheduler/generic_scheduler_daemon.py` — Added required `service_name: str` parameter to `SchedulerDaemon.__init__`; stored as `self._service_name` (Task 1.1 stub; not yet used in log messages or OTel spans)
- `tests/services/scheduler/test_generic_scheduler_daemon.py` — Updated `daemon` fixture and `test_init_stores_all_configuration_parameters` to pass `service_name="test"` to match new required parameter
- `tests/services/scheduler/test_generic_scheduler_daemon.py` — Added `TestSchedulerDaemonServiceName` class with two `@pytest.mark.xfail(strict=True)` tests asserting `[test]` appears in run() logs and `scheduler.service_name` is set in OTel span attributes (Task 1.2 RED)
- `services/scheduler/generic_scheduler_daemon.py` — Updated `run()` startup log to include `[service_name]` prefix and added `scheduler.service_name` to `_process_item` OTel span attributes; removed xfail markers from previously-failing tests (Task 1.3 GREEN)
- `services/scheduler/notification_daemon_wrapper.py` — Added `service_name="notification"` to `SchedulerDaemon` constructor call (Task 1.4)
- `services/scheduler/status_transition_daemon_wrapper.py` — Added `service_name="status-transition"` to `SchedulerDaemon` constructor call (Task 1.4)
- `services/scheduler/participant_action_daemon_wrapper.py` — Added `service_name="participant-action"` to `SchedulerDaemon` constructor call (Task 1.4)
- `compose.yaml` — Replaced three daemon service definitions (`notification-daemon`, `status-transition-daemon`, `participant-action-daemon`) with a single `scheduler` service using `docker/scheduler.Dockerfile` and `SCHEDULER_LOG_LEVEL` env var (Task 4.1)
- `compose.prod.yaml` — Replaced two daemon service build stubs with single `scheduler` stub; updated `frontend.depends_on` to reference `scheduler` (Task 4.2)
- `compose.staging.yaml` — Replaced two daemon service stubs with single `scheduler` stub; updated `frontend.depends_on` to reference `scheduler` (Task 4.2)
- `compose.override.yaml` — Replaced two daemon dev override blocks with single `scheduler` dev override with volume mounts (Task 4.2)
- `compose.int.yaml` — Replaced three daemon service environment stubs with single `scheduler` stub; updated `system-ready.depends_on` to reference `scheduler` (Task 4.2)
- `compose.e2e.yaml` — Replaced three daemon service stubs with single `scheduler` stub; updated `system-ready.depends_on` to reference `scheduler` (Task 4.2)

### Removed
