<!-- markdownlint-disable-file -->

# Release Changes: Complete Celery Elimination and Notification System Consolidation

**Related Plan**: 20251203-celery-elimination-notification-consolidation-plan.instructions.md
**Implementation Date**: 2025-12-03

## Summary

Eliminated Celery completely from the codebase by migrating game status transitions to database-backed scheduling using a separate game_status_schedule table and dedicated status_transition_daemon.

## Changes

### Added

- alembic/versions/020_add_game_status_schedule.py - Database migration creating game_status_schedule table with PostgreSQL LISTEN/NOTIFY trigger for status transition scheduling
- shared/models/game_status_schedule.py - SQLAlchemy model for game_status_schedule table

### Modified

- shared/models/__init__.py - Added GameStatusSchedule model import and export

### Removed

