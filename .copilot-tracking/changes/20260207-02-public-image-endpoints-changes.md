<!-- markdownlint-disable-file -->

# Release Changes: Secure Public Image Architecture with Deduplication

**Related Plan**: 20260207-02-public-image-endpoints-plan.instructions.md
**Implementation Date**: 2026-02-08

## Summary

Migration from RLS-protected game_sessions table to separate game_images table for secure public image serving with hash-based deduplication and reference counting.

**Phase 1 Status**: COMPLETE - Image storage service with 9 passing integration tests (6 core + 3 edge cases)

## Changes

### Added

- alembic/versions/dc81dd7fe299*migrate_images_to_separate_table_with*\*.py - Alembic migration creating game_images table with deduplication (Lines 1-100, Phase 0)
- shared/models/game_image.py - GameImage model with content_hash, reference_count, timestamps using utc_now (Lines 1-62, Phase 0)
- shared/services/image_storage.py - Image storage service with SHA256 deduplication and reference counting (Lines 1-110, Phase 1)
- shared/services/**init**.py - Export store_image and release_image functions (Lines 1-27, Phase 1)
- tests/integration/shared/**init**.py - Package marker for shared integration tests (Lines 1-22, Phase 1)
- tests/integration/shared/services/**init**.py - Package marker for service integration tests (Lines 1-22, Phase 1)
- tests/integration/shared/services/test_image_storage.py - Integration tests with hermetic isolation (Lines 1-176, Phase 1)

### Modified

- shared/models/**init**.py - Exported GameImage model (Phase 0)
- shared/models/game.py - Replaced embedded image columns with FK relationships to game_images table (Phase 0)

### Removed
