<!-- markdownlint-disable-file -->

# Task Details: Scheduler Daemon Consolidation

## Research Reference

**Source Research**: #file:../research/20260305-01-scheduler-daemon-consolidation-research.md

---

## Phase 1: Update `SchedulerDaemon` with `service_name`

### Task 1.1: Add `service_name` stub to `SchedulerDaemon.__init__`

Add `service_name: str` as a required parameter to `SchedulerDaemon.__init__` and store it as `self._service_name`. Do not yet use it in log messages or OTel spans — this is the Red stub step.

- **Files**:
  - `services/scheduler/generic_scheduler_daemon.py` — add `service_name: str` parameter and `self._service_name = service_name`
- **Success**:
  - `SchedulerDaemon(service_name="test", ...)` no longer raises `TypeError`
  - `instance._service_name == "test"` holds
- **Research References**:
  - #file:../research/20260305-01-scheduler-daemon-consolidation-research.md (Lines 18-25) — `SchedulerDaemon.__init__` current parameter list
- **Dependencies**:
  - None

### Task 1.2: Write xfail tests for `service_name` behaviour (RED)

Write tests with **real assertions** (log prefix contains service name, OTel span attribute `scheduler.service_name` is set) marked `@pytest.mark.xfail(strict=True, reason="not yet implemented")`. Do **not** assert on `NotImplementedError`; assert on the actual target behaviour.

- **Files**:
  - `tests/unit/services/scheduler/test_generic_scheduler_daemon.py` — new test cases for `service_name` in logs and OTel
- **Success**:
  - Tests run and are reported as XFAIL (expected failures)
- **Research References**:
  - #file:../research/20260305-01-scheduler-daemon-consolidation-research.md (Lines 67-78) — `service_name` requirements for log prefix and span attributes
- **Dependencies**:
  - Task 1.1 complete

### Task 1.3: Implement `service_name` in log messages and OTel spans (GREEN)

Use `self._service_name` in logger prefix strings (e.g. `f"[{self._service_name}]"`) and add `scheduler.service_name` to OTel span attributes. Remove the `xfail` markers from Task 1.2 tests without modifying their assertions.

- **Files**:
  - `services/scheduler/generic_scheduler_daemon.py` — update log calls and span attribute assignments
  - `tests/unit/services/scheduler/test_generic_scheduler_daemon.py` — remove `@pytest.mark.xfail` markers only
- **Success**:
  - All previously-xfail tests now pass
  - Existing tests still pass
- **Research References**:
  - #file:../research/20260305-01-scheduler-daemon-consolidation-research.md (Lines 67-78) — service_name usage details
- **Dependencies**:
  - Task 1.2 complete

### Task 1.4: Update existing callers of `SchedulerDaemon` to pass `service_name`

All three existing wrapper files and any test fixtures that construct `SchedulerDaemon` directly must pass `service_name`. This keeps the codebase coherent before the wrappers are deleted in Phase 5.

- **Files**:
  - `services/scheduler/notification_daemon_wrapper.py` — add `service_name="notification"`
  - `services/scheduler/status_transition_daemon_wrapper.py` — add `service_name="status-transition"`
  - `services/scheduler/participant_action_daemon_wrapper.py` — add `service_name="participant-action"`
  - `tests/unit/services/test_participant_action_daemon_wrapper.py` — update fixture construction if needed
  - `tests/services/scheduler/test_generic_scheduler_daemon.py` — update any direct constructions
- **Success**:
  - `pytest tests/` passes with no `TypeError` about missing `service_name`
- **Research References**:
  - #file:../research/20260305-01-scheduler-daemon-consolidation-research.md (Lines 18-25) — wrapper file descriptions
- **Dependencies**:
  - Task 1.1 complete

---

## Phase 2: Create Unified `scheduler_daemon_wrapper.py`

### Task 2.1: Create stub `scheduler_daemon_wrapper.py`

Create `services/scheduler/scheduler_daemon_wrapper.py` with a `main()` function that raises `NotImplementedError`. This is the TDD stub.

- **Files**:
  - `services/scheduler/scheduler_daemon_wrapper.py` — new file with stub `main()`
- **Success**:
  - File importable; `main()` raises `NotImplementedError`
- **Research References**:
  - #file:../research/20260305-01-scheduler-daemon-consolidation-research.md (Lines 82-120) — full sketch of `main()` implementation
- **Dependencies**:
  - Phase 1 complete

### Task 2.2: Write xfail tests for the unified wrapper (RED)

Write tests asserting the wrapper starts three threads and responds to a shutdown signal, marked `@pytest.mark.xfail(strict=True, reason="not yet implemented")`.

- **Files**:
  - `tests/unit/services/scheduler/test_scheduler_daemon_wrapper.py` — new test file
- **Success**:
  - Tests run and are reported as XFAIL
- **Research References**:
  - #file:../research/20260305-01-scheduler-daemon-consolidation-research.md (Lines 82-120) — thread lifecycle and signal handling sketch
- **Dependencies**:
  - Task 2.1 complete

### Task 2.3: Implement `scheduler_daemon_wrapper.main()` (GREEN)

Implement the full thread lifecycle: instantiate three `SchedulerDaemon` objects, start each in a `threading.Thread(daemon=True)`, register SIGTERM/SIGINT on the main thread via a `nonlocal shutdown_requested` flag, join all threads, then call `flush_telemetry()`. Remove `xfail` markers; do not modify test assertions.

- **Files**:
  - `services/scheduler/scheduler_daemon_wrapper.py` — full implementation replacing stub
  - `tests/unit/services/scheduler/test_scheduler_daemon_wrapper.py` — remove `@pytest.mark.xfail` markers only
- **Success**:
  - All previously-xfail unit tests now pass
  - `daemon_runner.run_daemon()` is NOT imported or called from this file
- **Research References**:
  - #file:../research/20260305-01-scheduler-daemon-consolidation-research.md (Lines 82-120) — complete code sketch
  - #file:../research/20260305-01-scheduler-daemon-consolidation-research.md (Lines 122-155) — compose configuration example
- **Dependencies**:
  - Task 2.2 complete; Phase 1 complete

### Task 2.4: Refactor and add edge-case tests

Add tests for: thread crash isolation (one daemon thread dying does not kill others), graceful shutdown within timeout, `LOG_LEVEL` env var defaulting. Keep all tests green.

- **Files**:
  - `tests/unit/services/scheduler/test_scheduler_daemon_wrapper.py` — additional test cases
- **Success**:
  - Full test suite passes; coverage for new wrapper is adequate
- **Research References**:
  - #file:../research/20260305-01-scheduler-daemon-consolidation-research.md (Lines 55-65) — thread crash recovery discussion
- **Dependencies**:
  - Task 2.3 complete

---

## Phase 3: Create `docker/scheduler.Dockerfile`

### Task 3.1: Create unified `docker/scheduler.Dockerfile`

Create a single multi-stage Dockerfile that consolidates the file-copy steps from all three existing daemon Dockerfiles. The `CMD` should invoke `scheduler_daemon_wrapper` (the new unified entry point).

- **Files**:
  - `docker/scheduler.Dockerfile` — new file
- **Success**:
  - `docker build -f docker/scheduler.Dockerfile .` completes without error
  - The three old Dockerfiles (`notification-daemon.Dockerfile`, `status-transition-daemon.Dockerfile`, `participant-action-daemon.Dockerfile`) are NOT yet deleted (done in Phase 5)
- **Research References**:
  - #file:../research/20260305-01-scheduler-daemon-consolidation-research.md (Lines 28-34) — existing Dockerfile descriptions
- **Dependencies**:
  - Phase 2 complete

---

## Phase 4: Update Compose Files

### Task 4.1: Update `compose.yaml`

Replace the three daemon service definitions (`notification-daemon`, `status-transition-daemon`, `participant-action-daemon`) with a single `scheduler` service using the new Dockerfile and `SCHEDULER_LOG_LEVEL` env var.

- **Files**:
  - `compose.yaml` — replace three service blocks with one `scheduler` block (see research lines 122-155 for template)
- **Success**:
  - `docker compose config` validates without error
  - `scheduler` service present; old three service names absent
- **Research References**:
  - #file:../research/20260305-01-scheduler-daemon-consolidation-research.md (Lines 122-155) — example compose service definition
  - #file:../research/20260305-01-scheduler-daemon-consolidation-research.md (Lines 36-42) — current compose service descriptions
- **Dependencies**:
  - Task 3.1 complete

### Task 4.2: Update all compose override files

Update `compose.prod.yaml`, `compose.int.yaml`, `compose.e2e.yaml`, `compose.staging.yaml`, and `compose.override.yaml` to replace per-daemon stubs with a single `scheduler` stub. The `compose.staging.yaml` gap (missing `participant-action-daemon`) is resolved automatically.

- **Files**:
  - `compose.prod.yaml`
  - `compose.int.yaml`
  - `compose.e2e.yaml`
  - `compose.staging.yaml`
  - `compose.override.yaml`
- **Success**:
  - `docker compose -f compose.yaml -f compose.<env>.yaml config` validates for all envs
  - Old daemon service names absent in all files
- **Research References**:
  - #file:../research/20260305-01-scheduler-daemon-consolidation-research.md (Lines 43-45) — compose override file descriptions
- **Dependencies**:
  - Task 4.1 complete

---

## Phase 5: Delete Old Files

### Task 5.1: Delete old wrapper files, their tests, and old Dockerfiles

Remove the three individual wrapper Python files, their unit test files, and their three Dockerfiles in one atomic step. The test files must be deleted in the same commit as the wrapper files they test — leaving test files behind would cause import errors that break the pre-commit test run.

- **Files to delete**:
  - `services/scheduler/notification_daemon_wrapper.py`
  - `services/scheduler/status_transition_daemon_wrapper.py`
  - `services/scheduler/participant_action_daemon_wrapper.py`
  - `tests/unit/services/test_participant_action_daemon_wrapper.py` (and any analogous tests for the other two wrappers)
  - `docker/notification-daemon.Dockerfile`
  - `docker/status-transition-daemon.Dockerfile`
  - `docker/participant-action-daemon.Dockerfile`
- **Success**:
  - `pytest tests/` passes with no import errors referencing deleted modules
  - No remaining import of old wrapper modules in production code
  - Integration tests still pass (they test scheduling behaviour, not container structure)
- **Research References**:
  - #file:../research/20260305-01-scheduler-daemon-consolidation-research.md (Lines 9-17) — old wrapper file descriptions
  - #file:../research/20260305-01-scheduler-daemon-consolidation-research.md (Lines 48-56) — test file inventory
- **Dependencies**:
  - Phase 4 complete

---

## Phase 6: Update Documentation

### Task 6.1: Update documentation and env var references

Scan documentation and config templates for old service names (`notification-daemon`, `status-transition-daemon`, `participant-action-daemon`) and old env vars (`NOTIFICATION_DAEMON_LOG_LEVEL`, etc.). Update or remove them.

- **Files**:
  - `docs/` — search and update any service name references
  - `config/` and `config.template/` — replace old env vars with `SCHEDULER_LOG_LEVEL`
- **Success**:
  - `grep -r "notification-daemon\|status-transition-daemon\|participant-action-daemon" docs/ config/` returns no matches
  - `grep -r "NOTIFICATION_DAEMON_LOG_LEVEL\|STATUS_TRANSITION_DAEMON_LOG_LEVEL\|PARTICIPANT_ACTION_DAEMON_LOG_LEVEL" .` returns no matches
- **Research References**:
  - #file:../research/20260305-01-scheduler-daemon-consolidation-research.md (Lines 159-170) — env var replacement details
- **Dependencies**:
  - Phase 5 complete

---

## Dependencies

- Python `threading` (stdlib — no new packages)
- `pytest` with `xfail` marker support (already in project)
- Docker CLI available for build validation

## Success Criteria

- All three scheduling behaviours pass integration tests against a single `scheduler` container
- Old service names (`notification-daemon`, `status-transition-daemon`, `participant-action-daemon`) absent from all compose files and Dockerfiles
- `docker compose up` starts one `scheduler` container, not three
- Full test suite passes with no regressions
