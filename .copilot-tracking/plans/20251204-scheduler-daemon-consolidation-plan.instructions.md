---
applyTo: '.copilot-tracking/changes/20251204-scheduler-daemon-consolidation-changes.md'
---
<!-- markdownlint-disable-file -->
# Task Checklist: Scheduler Daemon Consolidation and Bot Status Updates

## Overview

Consolidate duplicate daemon implementations into a single generic scheduler, move status update logic to bot event handlers, and fix integration test failures.

## Objectives

- Eliminate 95% code duplication between notification and status transition daemons
- Move game status update logic from daemon to bot for consistency
- Fix integration test failures caused by incorrect constructor parameters
- Enable Discord message updates when game status transitions occur
- Reduce total scheduler daemon code from 494 lines to ~150 lines

## Research Summary

### Project Files
- services/scheduler/notification_daemon.py - 252 lines with PostgreSQL LISTEN/NOTIFY pattern
- services/scheduler/status_transition_daemon.py - 242 lines with identical algorithm structure
- services/bot/events/handlers.py - Bot event handling framework, missing status transition handler
- services/api/services/games.py - API publishes GAME_UPDATED events after modifications
- tests/integration/test_status_transitions.py - Integration tests failing due to constructor mismatch

### External References
- #file:../research/20251204-scheduler-daemon-consolidation-bot-status-updates-research.md - Complete analysis of daemon duplication, architectural patterns, and bot handling benefits

### Standards References
- #file:../../.github/instructions/python.instructions.md - Python coding conventions
- #file:../../.github/instructions/coding-best-practices.instructions.md - DRY principle, modularity, correctness

## Implementation Checklist

### [x] Phase 1: Create Generic Scheduler Daemon

- [x] Task 1.1: Create generic scheduler daemon base class
  - Details: .copilot-tracking/details/20251204-scheduler-daemon-consolidation-details.md (Lines 13-47)

- [x] Task 1.2: Implement generic query functions
  - Details: .copilot-tracking/details/20251204-scheduler-daemon-consolidation-details.md (Lines 49-78)

- [x] Task 1.3: Implement event builder pattern
  - Details: .copilot-tracking/details/20251204-scheduler-daemon-consolidation-details.md (Lines 80-107)

### [x] Phase 2: Add Status Transition Event Support

- [x] Task 2.1: Add GAME_STATUS_TRANSITION_DUE event type and schema
  - Details: .copilot-tracking/details/20251204-scheduler-daemon-consolidation-details.md (Lines 109-133)

- [x] Task 2.2: Implement bot handler for status transitions
  - Details: .copilot-tracking/details/20251204-scheduler-daemon-consolidation-details.md (Lines 135-167)

- [x] Task 2.3: Register status transition handler in bot
  - Details: .copilot-tracking/details/20251204-scheduler-daemon-consolidation-details.md (Lines 169-185)

### [x] Phase 3: Create Daemon Wrappers and Update Docker

- [x] Task 3.1: Create notification daemon wrapper
  - Details: .copilot-tracking/details/20251204-scheduler-daemon-consolidation-details.md (Lines 187-215)

- [x] Task 3.2: Create status transition daemon wrapper
  - Details: .copilot-tracking/details/20251204-scheduler-daemon-consolidation-details.md (Lines 217-245)

- [x] Task 3.3: Update Docker configurations
  - Details: .copilot-tracking/details/20251204-scheduler-daemon-consolidation-details.md (Lines 247-269)

### [ ] Phase 4: Update Integration Tests

- [ ] Task 4.1: Fix status transition daemon test constructor calls
  - Details: .copilot-tracking/details/20251204-scheduler-daemon-consolidation-details.md (Lines 271-297)

- [ ] Task 4.2: Add generic scheduler daemon tests
  - Details: .copilot-tracking/details/20251204-scheduler-daemon-consolidation-details.md (Lines 299-328)

- [ ] Task 4.3: Add bot handler tests for status transitions
  - Details: .copilot-tracking/details/20251204-scheduler-daemon-consolidation-details.md (Lines 330-360)

### [ ] Phase 5: Clean Up Old Implementations

- [ ] Task 5.1: Remove old daemon implementations
  - Details: .copilot-tracking/details/20251204-scheduler-daemon-consolidation-details.md (Lines 362-383)

- [ ] Task 5.2: Verify all tests pass
  - Details: .copilot-tracking/details/20251204-scheduler-daemon-consolidation-details.md (Lines 385-404)

## Dependencies

- PostgreSQL LISTEN/NOTIFY infrastructure (already exists)
- RabbitMQ event bus (already exists)
- Bot event handler framework (already exists)
- Schedule tables and triggers (already exist)
- Python 3.11+
- SQLAlchemy ORM
- Pika (RabbitMQ client)

## Success Criteria

- All integration tests pass without constructor errors
- Discord messages update when game status transitions from SCHEDULED to IN_PROGRESS
- Single unified generic scheduler daemon (~150 lines total)
- Bot handles all game state changes through consistent event pattern
- No code duplication between notification and status transition schedulers
- Test coverage maintained or improved for all scheduler functionality
