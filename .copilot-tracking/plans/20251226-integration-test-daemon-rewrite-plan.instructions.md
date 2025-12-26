---
applyTo: '.copilot-tracking/changes/20251226-integration-test-daemon-rewrite-changes.md'
---

<!-- markdownlint-disable-file -->

# Task Checklist: Integration Test Daemon Pattern Rewrite

## Overview

Rewrite test_notification_daemon.py and test_status_transitions.py to test running daemon services instead of creating conflicting SchedulerDaemon instances.

## Objectives

- Eliminate all SchedulerDaemon instantiation in integration tests (7 occurrences total)
- Align notification and status transition tests with retry daemon test pattern
- Ensure tests validate running daemon services from compose.int.yaml
- Utilize PostgreSQL LISTEN/NOTIFY event-driven wake mechanism correctly

## Research Summary

### Project Files

- tests/integration/test_retry_daemon.py - Reference implementation showing correct pattern for testing running daemon services
- tests/integration/test_notification_daemon.py - Currently creates own daemon instances (4 occurrences), needs rewrite
- tests/integration/test_status_transitions.py - Currently creates own daemon instances (3 occurrences), needs rewrite
- conftest.py - May need rabbitmq_channel fixture addition

### External References

- #file:../research/20251226-integration-test-daemon-rewrite-research.md - Comprehensive analysis of current test patterns and required changes

### Standards References

- #file:../../.github/instructions/python.instructions.md - Python coding conventions
- #file:../../.github/instructions/self-explanatory-code-commenting.instructions.md - Commenting guidelines
- #file:../../.github/instructions/integration-tests.instructions.md - Integration test standards

## Implementation Checklist

### [ ] Phase 1: Infrastructure Setup

- [ ] Task 1.1: Add rabbitmq_channel fixture if missing
  - Details: .copilot-tracking/details/20251226-integration-test-daemon-rewrite-details.md (Lines 13-29)

- [ ] Task 1.2: Add RabbitMQ helper functions
  - Details: .copilot-tracking/details/20251226-integration-test-daemon-rewrite-details.md (Lines 31-54)

### [ ] Phase 2: Rewrite Notification Daemon Tests

- [ ] Task 2.1: Rewrite test_daemon_processes_due_notification
  - Details: .copilot-tracking/details/20251226-integration-test-daemon-rewrite-details.md (Lines 56-87)

- [ ] Task 2.2: Rewrite test_daemon_waits_for_future_notification
  - Details: .copilot-tracking/details/20251226-integration-test-daemon-rewrite-details.md (Lines 89-118)

- [ ] Task 2.3: Rewrite test_daemon_marks_notification_as_processed
  - Details: .copilot-tracking/details/20251226-integration-test-daemon-rewrite-details.md (Lines 120-147)

- [ ] Task 2.4: Rewrite test_daemon_publishes_correct_event_type
  - Details: .copilot-tracking/details/20251226-integration-test-daemon-rewrite-details.md (Lines 149-176)

### [ ] Phase 3: Rewrite Status Transition Tests

- [ ] Task 3.1: Rewrite test_status_transition_daemon_processes_due_transition
  - Details: .copilot-tracking/details/20251226-integration-test-daemon-rewrite-details.md (Lines 178-209)

- [ ] Task 3.2: Rewrite test_status_transition_daemon_waits_for_future
  - Details: .copilot-tracking/details/20251226-integration-test-daemon-rewrite-details.md (Lines 211-238)

- [ ] Task 3.3: Rewrite test_status_transition_daemon_handles_cancellation
  - Details: .copilot-tracking/details/20251226-integration-test-daemon-rewrite-details.md (Lines 240-267)

### [ ] Phase 4: Validation and Cleanup

- [ ] Task 4.1: Verify all tests pass with running daemons
  - Details: .copilot-tracking/details/20251226-integration-test-daemon-rewrite-details.md (Lines 269-283)

- [ ] Task 4.2: Remove unused imports and code
  - Details: .copilot-tracking/details/20251226-integration-test-daemon-rewrite-details.md (Lines 285-298)

## Dependencies

- compose.int.yaml with notification-daemon and status-transition-daemon services running
- PostgreSQL with LISTEN/NOTIFY triggers configured
- RabbitMQ infrastructure with bot_events queue

## Success Criteria

- No SchedulerDaemon instances created in test files (0 occurrences of "SchedulerDaemon(")
- All integration tests pass without creating daemon instances
- Tests use event-driven wait pattern (2s sleep for NOTIFY) not polling pattern
- No threading or listener instantiation in test code
- Tests validate running daemon services from compose.int.yaml
