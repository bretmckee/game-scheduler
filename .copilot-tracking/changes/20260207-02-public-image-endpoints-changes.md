<!-- markdownlint-disable-file -->

# Release Changes: Secure Public Image Architecture with Deduplication

**Related Plan**: 20260207-02-public-image-endpoints-plan.instructions.md
**Implementation Date**: 2026-02-08

## Summary

Migration from RLS-protected game_sessions table to separate game_images table for secure public image serving with hash-based deduplication and reference counting.

## Changes

### Added

- alembic/versions/dc81dd7fe299*migrate_images_to_separate_table_with*.py - Alembic migration creating game_images table with deduplication
- shared/models/game_image.py - GameImage model with content_hash and reference_count for deduplication

### Modified

- shared/models/**init**.py - Exported GameImage model
- shared/models/game.py - Replaced embedded image columns with FK relationships to game_images table

### Removed
