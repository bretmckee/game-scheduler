<!-- markdownlint-disable-file -->

# Release Changes: Game Model Refactor (Remove min_players, Add where field)

**Related Plan**: 20251129-game-model-refactor-plan.instructions.md
**Implementation Date**: 2025-11-30

## Summary

Refactoring the game data model to remove the unused `min_players` field and add a `where` field for game location information. This change improves the user experience by simplifying participant count displays and adding location tracking capabilities.

## Changes

### Phase 1: Add where Field to Database ✓

### Added

- alembic/versions/014_add_where_field.py - Migration to add where column to game_sessions table

### Modified

- shared/models/game.py - Added where field to GameSession model as nullable Text field
  - Positioned after scheduled_at for logical grouping (when/where)
  - Implemented as `Mapped[str | None] = mapped_column(Text, nullable=True)`

### Database Changes

- game_sessions table now includes `where` column (TEXT, nullable)
- Migration 014_add_where_field executed successfully
- All existing game records preserved with NULL values for where field

### Removed

## Release Summary

_Will be completed after all phases are implemented_
