<!-- markdownlint-disable-file -->

# Release Changes: Complete Celery Elimination and Notification System Consolidation

**Related Plan**: 20251203-celery-elimination-notification-consolidation-plan.instructions.md
**Implementation Date**: 2025-12-03

## Summary

Eliminated Celery completely from the codebase by migrating game status transitions to database-backed scheduling using a separate game_status_schedule table and dedicated status_transition_daemon.

## Changes

### Added

- alembic/versions/020_add_game_status_schedule.py - Database migration creating game_status_schedule table with PostgreSQL LISTEN/NOTIFY trigger for status transition scheduling
- shared/models/game_status_schedule.py - SQLAlchemy model for game_status_schedule table (100% test coverage)
- services/scheduler/status_transition_daemon.py - Event-driven daemon for processing game status transitions using PostgreSQL LISTEN/NOTIFY pattern
- services/scheduler/status_schedule_queries.py - Database query functions for retrieving and updating game status schedule records (100% test coverage)
- tests/shared/models/test_game_status_schedule.py - Unit tests for GameStatusSchedule model (7 tests)
- tests/services/scheduler/test_status_schedule_queries.py - Unit tests for status schedule query functions (8 tests)

### Modified

- shared/models/__init__.py - Added GameStatusSchedule model import and export
- shared/messaging/events.py - Added GameStartedEvent model for game.started event publishing
- shared/messaging/__init__.py - Added GameStartedEvent export
- services/api/services/games.py - Integrated game_status_schedule with game creation, updates, and cancellation (Task 3.1, 3.2, 3.3)

### Removed

