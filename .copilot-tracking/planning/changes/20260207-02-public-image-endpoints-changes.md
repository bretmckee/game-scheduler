<!-- markdownlint-disable-file -->

# Release Changes: Secure Public Image Architecture with Deduplication

**Related Plan**: 20260207-02-public-image-endpoints.plan.md
**Implementation Date**: 2026-02-08

## Summary

Migration from RLS-protected game_sessions table to separate game_images table for secure public image serving with hash-based deduplication and reference counting.

**Phase 1 Status**: COMPLETE - Image storage service with 9 passing integration tests (6 core + 3 edge cases)

**Phase 2 Status**: COMPLETE - GameService integration with 6 passing integration tests

**Phase 3 Status**: NOT STARTED (skipped per user request)

**Phase 4 Status**: COMPLETE - Bot and frontend updated to use new public image URLs

## Changes

### Added

- alembic/versions/dc81dd7fe299*migrate_images_to_separate_table_with*\*.py - Alembic migration creating game_images table with deduplication (Lines 1-100, Phase 0)
- shared/models/game_image.py - GameImage model with content_hash, reference_count, timestamps using utc_now (Lines 1-62, Phase 0)
- shared/services/image_storage.py - Image storage service with SHA256 deduplication and reference counting (Lines 1-110, Phase 1)
- shared/services/**init**.py - Export store_image and release_image functions (Lines 1-27, Phase 1)
- tests/integration/shared/**init**.py - Package marker for shared integration tests (Lines 1-22, Phase 1)
- tests/integration/shared/services/**init**.py - Package marker for service integration tests (Lines 1-22, Phase 1)
- tests/integration/shared/services/test_image_storage.py - Integration tests with hermetic isolation (Lines 1-176, Phase 1)
- tests/integration/services/api/services/test_game_image_integration.py - Integration tests for GameService image lifecycle with fixture override to disable mock (Lines 1-619, Phase 2)

### Modified

- shared/models/**init**.py - Exported GameImage model (Phase 0)
- shared/models/game.py - Replaced embedded image columns with FK relationships to game_images table (Phase 0)
- services/api/services/games.py - Integrated image storage service into create_game, update_game, delete_game (Lines 41, 448-509, 610-612, 1242-1284, 1385-1387, 1462-1464, Phase 2)
  - Added import for store_image and release_image functions
  - Modified \_build_game_session to store images via image_storage service (now async)
  - Modified create_game to await \_build_game_session
  - Modified \_update_image_fields to release old images before storing new ones (now async)
  - Modified update_game to await \_update_image_fields
  - Modified delete_game to release image references before cancelling game
- tests/conftest.py - Added reset_redis_singleton fixture to disconnect/reconnect Redis between integration tests with flushdb in teardown (Lines 282-300, Phase 2)
- shared/schemas/game.py - Added thumbnail_id and banner_image_id fields to GameResponse schema (Lines 207-208, Phase 4)
- services/bot/formatters/game_message.py - Updated format_game_announcement() to accept thumbnail_id and banner_image_id instead of has_thumbnail/has_image booleans, construct public image URLs (Lines 347-368, 389-392, 398-403, Phase 4)
- services/bot/events/handlers.py - Updated format_game_announcement() call to pass thumbnail_id and banner_image_id as strings (Lines 1211-1212, Phase 4)
- tests/services/bot/formatters/test_game_message.py - Updated tests to pass thumbnail_id and banner_image_id instead of has_thumbnail/has_image (Lines 946-978, 979-1009, Phase 4)
- frontend/src/pages/GameDetails.tsx - Updated image display to use /api/v1/public/images/{id} URLs (Lines 353-386, Phase 4)
- frontend/src/types/index.ts - Added thumbnail_id and banner_image_id fields to GameSession interface (Lines 105-106, Phase 4)

### Documentation

- docs/developer/public-image-architecture.md - Comprehensive documentation of new public image architecture including security model, deduplication, API endpoints, usage examples, testing coverage, and migration notes (Lines 1-265, Phase 5)
- docs/developer/README.md - Added reference to public image architecture documentation (Line 37, Phase 5)

### Removed

- tests/services/api/routes/test_games_image_serving.py - Deprecated tests for old authenticated image endpoints (Lines 1-171, Phase 5)
- tests/services/api/routes/conftest.py - Removed unused fixtures (sample_game_with_images, sample_game_no_images, create_mock_game_image) that were only used by deleted test file (Lines 32-82, Phase 5)
- services/api/routes/games.py - Removed deprecated get_game_thumbnail and get_game_image endpoints (Lines 845-897, Phase 5)
