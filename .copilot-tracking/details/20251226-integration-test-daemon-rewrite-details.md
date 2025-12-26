<!-- markdownlint-disable-file -->

# Task Details: Integration Test Daemon Pattern Rewrite

## Research Reference

**Source Research**: #file:../research/20251226-integration-test-daemon-rewrite-research.md

## Phase 1: Infrastructure Setup

### Task 1.1: Add rabbitmq_channel fixture if missing

Check if `rabbitmq_channel` fixture exists in conftest.py and add if missing. This fixture is required for RabbitMQ queue assertions.

- **Files**:
  - conftest.py - Check for rabbitmq_channel fixture existence, add if missing
- **Success**:
  - `rabbitmq_channel` fixture available in conftest.py
  - Fixture returns pika.BlockingChannel connected to RabbitMQ
- **Research References**:
  - #file:../research/20251226-integration-test-daemon-rewrite-research.md (Lines 121-135) - Retry daemon test pattern showing fixture usage
- **Dependencies**:
  - RabbitMQ running in compose.int.yaml
  - pika library installed

### Task 1.2: Add RabbitMQ helper functions

Add `get_queue_message_count()` and optionally `consume_one_message()` helper functions if not present. Copy from test_retry_daemon.py.

- **Files**:
  - tests/integration/test_notification_daemon.py - Add helpers at module level
  - tests/integration/test_status_transitions.py - Add helpers at module level
- **Success**:
  - `get_queue_message_count(channel, queue_name)` function available
  - Function returns integer count of messages in queue
  - `consume_one_message(channel, queue_name)` optional helper added
- **Research References**:
  - #file:../research/20251226-integration-test-daemon-rewrite-research.md (Lines 73-78) - Reference to helper function usage in retry daemon tests
- **Dependencies**:
  - rabbitmq_channel fixture from Task 1.1
  - pika library

## Phase 2: Rewrite Notification Daemon Tests

### Task 2.1: Rewrite test_daemon_processes_due_notification

Replace SchedulerDaemon instantiation with pattern that tests running notification-daemon service.

- **Files**:
  - tests/integration/test_notification_daemon.py - Function at line 102 creates daemon instance
- **Success**:
  - Test inserts notification_schedule record with past trigger_at
  - Test uses `time.sleep(2)` for event-driven processing wait
  - Test asserts is_processed=True in database
  - Test asserts message published to bot_events queue
  - No SchedulerDaemon instantiation
  - No threading code
- **Research References**:
  - #file:../research/20251226-integration-test-daemon-rewrite-research.md (Lines 137-190) - Target pattern showing INSERT + NOTIFY + wait + assert
  - #file:../research/20251226-integration-test-daemon-rewrite-research.md (Lines 81-85) - Environment variables showing NOTIFY mechanism (no polling interval)
- **Dependencies**:
  - Phase 1 completion (fixtures and helpers)
  - notification-daemon service running in compose.int.yaml

### Task 2.2: Rewrite test_daemon_waits_for_future_notification

Replace daemon instantiation with pattern that verifies running daemon doesn't process future notifications.

- **Files**:
  - tests/integration/test_notification_daemon.py - Function at line 187 creates daemon instance
- **Success**:
  - Test inserts notification_schedule record with future trigger_at (e.g., +10 minutes)
  - Test waits briefly (2s)
  - Test asserts is_processed=False (notification not processed yet)
  - Test asserts no message in bot_events queue
  - No SchedulerDaemon instantiation
- **Research References**:
  - #file:../research/20251226-integration-test-daemon-rewrite-research.md (Lines 81-85) - Daemon wake mechanisms showing max_timeout of 15min
  - #file:../research/20251226-integration-test-daemon-rewrite-research.md (Lines 137-190) - Testing pattern for running services
- **Dependencies**:
  - Phase 1 completion
  - Task 2.1 completion (pattern established)

### Task 2.3: Rewrite test_daemon_marks_notification_as_processed

Replace daemon instantiation with pattern that validates database state changes.

- **Files**:
  - tests/integration/test_notification_daemon.py - Function at line 333 creates daemon instance
- **Success**:
  - Test inserts notification_schedule with past trigger_at
  - Test waits 2s for processing
  - Test queries database to verify is_processed=True
  - No SchedulerDaemon instantiation
- **Research References**:
  - #file:../research/20251226-integration-test-daemon-rewrite-research.md (Lines 137-190) - Database assertion pattern
- **Dependencies**:
  - Phase 1 completion
  - Task 2.1 completion

### Task 2.4: Rewrite test_daemon_publishes_correct_event_type

Replace daemon instantiation with pattern that validates RabbitMQ message content.

- **Files**:
  - tests/integration/test_notification_daemon.py - Function at line 430 creates daemon instance
- **Success**:
  - Test inserts notification_schedule with past trigger_at
  - Test waits 2s for processing
  - Test consumes message from bot_events queue
  - Test asserts event_type matches EventType.NOTIFICATION_DUE
  - No SchedulerDaemon instantiation
- **Research References**:
  - #file:../research/20251226-integration-test-daemon-rewrite-research.md (Lines 137-190) - RabbitMQ assertion pattern
  - #file:../research/20251226-integration-test-daemon-rewrite-research.md (Lines 192-198) - Status transition daemon showing routing_key and event_type
- **Dependencies**:
  - Phase 1 completion with consume_one_message helper
  - Task 2.1 completion

## Phase 3: Rewrite Status Transition Tests

### Task 3.1: Rewrite test_status_transition_daemon_processes_due_transition

Replace SchedulerDaemon instantiation at line 268 with pattern for testing running status-transition-daemon.

- **Files**:
  - tests/integration/test_status_transitions.py - Function at line 268 creates daemon instance
- **Success**:
  - Test inserts game_status_schedule record with past trigger_at
  - Test uses `time.sleep(2)` for event-driven wait
  - Test asserts is_processed=True in game_status_schedule
  - Test asserts message published to bot_events queue
  - Test verifies event_type=EventType.GAME_STATUS_TRANSITION_DUE
  - No SchedulerDaemon instantiation
- **Research References**:
  - #file:../research/20251226-integration-test-daemon-rewrite-research.md (Lines 192-198) - Status transition daemon specifics
  - #file:../research/20251226-integration-test-daemon-rewrite-research.md (Lines 137-190) - General test pattern
- **Dependencies**:
  - Phase 1 completion
  - Phase 2 completion (pattern well established)
  - status-transition-daemon service running

### Task 3.2: Rewrite test_status_transition_daemon_waits_for_future

Replace SchedulerDaemon instantiation at line 405 with pattern that verifies future transitions not processed.

- **Files**:
  - tests/integration/test_status_transitions.py - Function at line 405 creates daemon instance
- **Success**:
  - Test inserts game_status_schedule with future trigger_at
  - Test waits 2s
  - Test asserts is_processed=False
  - Test asserts no message in bot_events queue
  - No SchedulerDaemon instantiation
- **Research References**:
  - #file:../research/20251226-integration-test-daemon-rewrite-research.md (Lines 81-85) - Wake mechanism with max_timeout
  - #file:../research/20251226-integration-test-daemon-rewrite-research.md (Lines 192-198) - Status transition specifics
- **Dependencies**:
  - Task 3.1 completion

### Task 3.3: Rewrite test_status_transition_daemon_handles_cancellation

Replace SchedulerDaemon instantiation at line 486 with pattern testing cancellation logic.

- **Files**:
  - tests/integration/test_status_transitions.py - Function at line 486 creates daemon instance
- **Success**:
  - Test inserts game_status_schedule then cancels it
  - Test waits 2s
  - Test verifies cancelled transition not processed
  - No SchedulerDaemon instantiation
- **Research References**:
  - #file:../research/20251226-integration-test-daemon-rewrite-research.md (Lines 192-198) - Status transition patterns
- **Dependencies**:
  - Task 3.1 completion

## Phase 4: Validation and Cleanup

### Task 4.1: Verify all tests pass with running daemons

Run integration tests to validate rewritten tests work correctly with running daemon services.

- **Files**:
  - tests/integration/test_notification_daemon.py - All 4 rewritten tests
  - tests/integration/test_status_transitions.py - All 3 rewritten tests
- **Success**:
  - All notification daemon tests pass
  - All status transition tests pass
  - Tests complete within reasonable time (no excessive waits)
  - No flaky behavior from race conditions
- **Research References**:
  - #file:../research/20251226-integration-test-daemon-rewrite-research.md (Lines 200-218) - Success criteria and dependencies
- **Dependencies**:
  - All previous phases complete

### Task 4.2: Remove unused imports and code

Clean up imports and remove any dead code from daemon instantiation removal.

- **Files**:
  - tests/integration/test_notification_daemon.py - Remove threading, SchedulerDaemon, PostgresNotificationListener imports
  - tests/integration/test_status_transitions.py - Remove threading, SchedulerDaemon imports
- **Success**:
  - No unused imports remain
  - No commented-out daemon instantiation code
  - Files pass linting
  - Grep search for "SchedulerDaemon(" returns 0 matches in test files
- **Research References**:
  - #file:../research/20251226-integration-test-daemon-rewrite-research.md (Lines 220-226) - Key tasks including cleanup
- **Dependencies**:
  - Task 4.1 completion (tests validated)

## Dependencies

- compose.int.yaml with notification-daemon and status-transition-daemon services configured
- PostgreSQL database with LISTEN/NOTIFY triggers on notification_schedule and game_status_schedule tables
- RabbitMQ with bot_events queue configured

## Success Criteria

- Zero occurrences of "SchedulerDaemon(" in test_notification_daemon.py and test_status_transitions.py
- All integration tests pass without creating daemon instances
- Tests use 2s wait time (event-driven) not retry daemon's polling pattern
- No threading or subprocess code in integration tests
- Tests demonstrate understanding of NOTIFY-based wake mechanism
