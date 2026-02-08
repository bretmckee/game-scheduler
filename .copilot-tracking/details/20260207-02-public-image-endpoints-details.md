<!-- markdownlint-disable-file -->

# Task Details: Secure Public Image Architecture with Deduplication

## Research Reference

**Source Research**: #file:../research/20260207-02-public-image-endpoints-research.md

## Phase 0: Database Migration and Models

### Task 0.1: Create Alembic migration for schema changes

Create schema-only migration that drops existing image columns from game_sessions and creates new game_images table with deduplication support.

- **Files**:
  - alembic/versions/YYYYMMDDHHMMSS_migrate_images_to_separate_table.py - New migration file
- **Success**:
  - Migration drops 4 columns from game_sessions (thumbnail_data, thumbnail_mime_type, image_data, image_mime_type)
  - Creates game_images table with content_hash, reference_count columns
  - Adds thumbnail_id and banner_image_id FK columns to game_sessions
  - Creates index on content_hash for O(1) deduplication lookups
  - Migration upgrades and downgrades cleanly
- **Research References**:
  - #file:../research/20260207-02-public-image-endpoints-research.md (Lines 199-274) - Complete migration SQL
- **Dependencies**:
  - Alembic migration framework
  - PostgreSQL UUID and gen_random_uuid() support

### Task 0.2: Create GameImage SQLAlchemy model

Create new model for game_images table with deduplication and reference counting support.

- **Files**:
  - shared/models/game_image.py - New model file
  - shared/models/**init**.py - Export GameImage
- **Success**:
  - Model includes: id (UUID), content_hash (unique), image_data, mime_type, reference_count (default 0)
  - Timestamps: created_at, updated_at with server defaults
  - Proper type hints with Mapped[] annotations
  - **repr** method for debugging
- **Research References**:
  - #file:../research/20260207-02-public-image-endpoints-research.md (Lines 67-97) - Schema definition
- **Dependencies**:
  - SQLAlchemy 2.x with Mapped annotations
  - PostgreSQL UUID type

### Task 0.3: Update GameSession model to use FK relationships

Remove old image columns from GameSession model and add FK relationships to GameImage.

- **Files**:
  - shared/models/game.py - Modify GameSession model
- **Success**:
  - Removed: thumbnail_data, thumbnail_mime_type, image_data, image_mime_type columns
  - Added: thumbnail_id and banner_image_id FK columns (nullable, ondelete='SET NULL')
  - Relationship declarations to GameImage model
  - No breaking changes to existing queries (yet)
- **Research References**:
  - #file:../research/20260207-02-public-image-endpoints-research.md (Lines 88-97) - FK column definitions
- **Dependencies**:
  - Task 0.2 completion (GameImage model exists)

## Phase 1: Image Storage Service with Deduplication (TDD)

### Task 1.1: Create failing integration tests for image storage

Write comprehensive integration tests for image storage with deduplication before implementing the service.

- **Files**:
  - tests/integration/shared/services/test_image_storage.py - New test file
  - tests/integration/conftest.py - Add image data fixtures
- **Success**:
  - Test: store_image creates new image with reference_count=1
  - Test: storing duplicate increments count, returns same ID
  - Test: release_image decrements count
  - Test: release_image deletes when count reaches zero
  - Test: concurrent operations safe (SELECT FOR UPDATE)
  - Tests use valid PNG/JPEG binary data fixtures
- **Research References**:
  - #file:../research/20260207-02-public-image-endpoints-research.md (Lines 304-383) - Complete test examples
- **Dependencies**:
  - Phase 0 complete (models and migration)
  - pytest with asyncio support

### Task 1.2: Run tests to verify RED phase (tests fail)

Execute tests to confirm they fail correctly before implementation exists.

- **Files**:
  - N/A (test execution)
- **Success**:
  - Tests fail with ImportError or NotImplementedError
  - Failure messages are clear and expected
  - No false positives (tests actually running)
- **Research References**:
  - #file:../../.github/instructions/test-driven-development.instructions.md - RED phase requirements
- **Dependencies**:
  - Task 1.1 complete

### Task 1.3: Implement store_image() and release_image() functions

Create image storage service with hash-based deduplication and reference counting.

- **Files**:
  - shared/services/image_storage.py - New service file
  - shared/services/**init**.py - Export functions
- **Success**:
  - store_image() computes SHA256 hash of image data
  - Uses SELECT FOR UPDATE to prevent race conditions
  - Increments reference_count for duplicates
  - Creates new image with reference_count=1 for unique data
  - release_image() decrements count, deletes if zero
  - Proper error handling for None/missing IDs
- **Research References**:
  - #file:../research/20260207-02-public-image-endpoints-research.md (Lines 99-175) - Complete implementation examples
- **Dependencies**:
  - hashlib for SHA256
  - SQLAlchemy async session
  - Task 0.2 complete (GameImage model)

### Task 1.4: Run tests to verify GREEN phase (tests pass)

Execute tests to confirm implementation makes all tests pass.

- **Files**:
  - N/A (test execution)
- **Success**:
  - All tests from Task 1.1 pass
  - No test failures or errors
  - Coverage includes all code paths
- **Research References**:
  - #file:../../.github/instructions/test-driven-development.instructions.md - GREEN phase requirements
- **Dependencies**:
  - Task 1.3 complete

### Task 1.5: Refactor and add edge case tests

Add comprehensive edge case tests and refactor for production quality.

- **Files**:
  - tests/integration/shared/services/test_image_storage.py - Add edge case tests
  - shared/services/image_storage.py - Refactor if needed
- **Success**:
  - Test: release_image with None ID (no-op)
  - Test: release_image with missing ID (no error)
  - Test: different MIME types with same data (separate entries)
  - Test: transaction rollback scenarios
  - All tests pass after refactoring
- **Research References**:
  - #file:../research/20260207-02-public-image-endpoints-research.md (Lines 540-552) - Edge case examples
- **Dependencies**:
  - Task 1.4 complete

## Phase 2: Game Service Integration (TDD)

### Task 2.1: Create failing tests for game-image lifecycle integration

Write integration tests for game creation, update, and deletion with image handling.

- **Files**:
  - tests/integration/services/api/services/test_game_image_integration.py - New test file
- **Success**:
  - Test: create game with images stores and links them
  - Test: update game images releases old, stores new
  - Test: delete game releases image references
  - Test: shared image not deleted until all refs gone
  - Test: reference counting across multiple games
- **Research References**:
  - #file:../research/20260207-02-public-image-endpoints-research.md (Lines 421-518) - Complete test examples
- **Dependencies**:
  - Phase 1 complete (image storage service working)

### Task 2.2: Update game service methods to use image storage

Integrate image storage service into game service lifecycle methods.

- **Files**:
  - services/api/services/game_service.py - Update create_game, update_game, delete_game
- **Success**:
  - create_game calls store_image for uploaded images
  - update_game releases old images before storing new ones
  - delete_game calls release_image for both thumbnail and banner
  - Proper transaction handling (flush, not commit)
  - Image IDs stored in game.thumbnail_id and game.banner_image_id
- **Research References**:
  - #file:../research/20260207-02-public-image-endpoints-research.md (Lines 177-197) - Integration pattern examples
  - #file:../../.github/instructions/fastapi-transaction-patterns.instructions.md - Transaction management
- **Dependencies**:
  - Phase 1 complete
  - Understanding of service layer transaction patterns

### Task 2.3: Run tests to verify integration works correctly

Execute integration tests to confirm game-image lifecycle works end-to-end.

- **Files**:
  - N/A (test execution)
- **Success**:
  - All tests from Task 2.1 pass
  - No orphaned images created
  - Reference counting accurate across operations
  - Shared images properly handled
- **Research References**:
  - #file:../../.github/instructions/test-driven-development.instructions.md - Integration testing
- **Dependencies**:
  - Task 2.2 complete

## Phase 3: Public Image Endpoint (TDD)

### Task 3.1: Create endpoint stub returning NotImplementedError

Create public router with stub endpoint for RED phase.

- **Files**:
  - services/api/routes/public.py - New router file
- **Success**:
  - Router prefix: /api/v1/public/images
  - GET /{image_id} and HEAD /{image_id} endpoints
  - Both raise NotImplementedError with clear message
  - Proper docstrings explaining public access
- **Research References**:
  - #file:../research/20260207-02-public-image-endpoints-research.md (Lines 276-295) - Stub example
- **Dependencies**:
  - FastAPI router knowledge

### Task 3.2: Write failing integration tests for public endpoint

Write comprehensive tests for public image endpoint before implementation.

- **Files**:
  - tests/integration/services/api/routes/test_public_images.py - New test file
- **Success**:
  - Test: GET image returns data without authentication
  - Test: response includes cache-control headers
  - Test: response includes CORS headers
  - Test: missing image returns 404
  - Test: HEAD request returns headers only
  - All tests fail with 501 NotImplementedError
- **Research References**:
  - #file:../research/20260207-02-public-image-endpoints-research.md (Lines 554-619) - Complete test examples
- **Dependencies**:
  - Phase 2 complete (images stored with games)
  - httpx AsyncClient for testing

### Task 3.3: Run tests to verify RED phase

Execute tests to confirm they fail correctly before endpoint implementation.

- **Files**:
  - N/A (test execution)
- **Success**:
  - All tests fail with 501 NotImplementedError
  - Failure messages clear and expected
- **Research References**:
  - #file:../../.github/instructions/test-driven-development.instructions.md - RED phase
- **Dependencies**:
  - Task 3.2 complete

### Task 3.4: Implement public endpoint with proper headers

Replace NotImplementedError with working implementation that queries game_images table.

- **Files**:
  - services/api/routes/public.py - Implement endpoints
- **Success**:
  - Query game_images by ID (no JOIN needed)
  - Return image data with proper MIME type
  - Headers: Cache-Control: public, max-age=3600
  - Headers: Access-Control-Allow-Origin: \*
  - 404 for missing images with descriptive message
  - HEAD request returns headers only
  - Uses regular database credentials (no BYPASSRLS)
- **Research References**:
  - #file:../research/20260207-02-public-image-endpoints-research.md (Lines 118-176) - Complete implementation
- **Dependencies**:
  - Task 3.1 complete (stub exists)
  - database.get_db dependency (regular credentials)

### Task 3.5: Register router in main.py

Add public router to FastAPI application.

- **Files**:
  - services/api/main.py - Import and include router
- **Success**:
  - Import: from services.api.routes import public
  - Include: app.include_router(public.router)
  - Router appears in OpenAPI docs under "public" tag
- **Research References**:
  - Existing router patterns in main.py
- **Dependencies**:
  - Task 3.4 complete

### Task 3.6: Run tests to verify GREEN phase

Execute tests to confirm implementation makes all tests pass.

- **Files**:
  - N/A (test execution)
- **Success**:
  - All tests from Task 3.2 pass
  - Images served correctly
  - Headers present as expected
  - 404 handling works
- **Research References**:
  - #file:../../.github/instructions/test-driven-development.instructions.md - GREEN phase
- **Dependencies**:
  - Task 3.5 complete

### Task 3.7: Add rate limiting tests

Add tests for rate limiting before implementing the feature.

- **Files**:
  - tests/integration/services/api/routes/test_public_images.py - Add rate limit tests
- **Success**:
  - Test: 61st request in 1 minute returns 429
  - Test: 101st request in 5 minutes returns 429
  - Test: rate limit headers present in response
- **Research References**:
  - #file:../research/20260207-02-public-image-endpoints-research.md (Lines 621-640) - Rate limit test examples
- **Dependencies**:
  - Task 3.6 complete

### Task 3.8: Implement rate limiting with slowapi

Add slowapi rate limiting to public endpoint.

- **Files**:
  - services/api/main.py - Configure Limiter
  - services/api/routes/public.py - Apply rate limits
  - pyproject.toml - Add slowapi dependency
- **Success**:
  - Dependency: slowapi = "^0.1.9" added
  - Limiter configured with get_remote_address
  - Endpoint decorated with @limiter.limit("60/minute")
  - Endpoint decorated with @limiter.limit("100/5minutes")
  - Request parameter added for limiter access
  - 429 responses include rate limit headers
- **Research References**:
  - #file:../research/20260207-02-public-image-endpoints-research.md (Lines 177-197) - Rate limiting configuration
- **Dependencies**:
  - Task 3.7 complete (tests exist)
  - slowapi library

### Task 3.9: Run full test suite to verify REFACTOR phase

Execute complete test suite to ensure all functionality works together.

- **Files**:
  - N/A (test execution)
- **Success**:
  - All public endpoint tests pass
  - Rate limiting tests pass
  - No regressions in other tests
  - Coverage meets requirements
- **Research References**:
  - #file:../../.github/instructions/test-driven-development.instructions.md - REFACTOR phase
- **Dependencies**:
  - Task 3.8 complete

## Phase 4: Consumer Updates

### Task 4.1: Update bot message formatter URLs and tests

Update bot to use new public image endpoint URLs.

- **Files**:
  - services/bot/formatters/game_message.py - Update URL generation (lines 404, 407)
  - tests/services/bot/formatters/test_game_message.py - Update/add tests
- **Success**:
  - Thumbnail URL: f"{config.backend_url}/api/v1/public/images/{game.thumbnail_id}"
  - Banner URL: f"{config.backend_url}/api/v1/public/images/{game.banner_image_id}"
  - Handle None image IDs gracefully (no URL if no image)
  - Tests verify URL format correct
- **Research References**:
  - #file:../research/20260207-02-public-image-endpoints-research.md (Lines 15-17) - Current bot URLs
- **Dependencies**:
  - Phase 3 complete (public endpoint working)

### Task 4.2: Update frontend image display URLs and tests

Update frontend to use new public image endpoint URLs.

- **Files**:
  - frontend/src/pages/GameDetails.tsx - Update image sources (lines 361, 380)
  - frontend/src/components/**tests**/GameDetails.test.tsx - Update/add tests
- **Success**:
  - Thumbnail: src={`/api/v1/public/images/${game.thumbnail_id}`}
  - Banner: src={`/api/v1/public/images/${game.banner_image_id}`}
  - Handle undefined image IDs (no img tag if no ID)
  - Tests verify images load correctly
- **Research References**:
  - #file:../research/20260207-02-public-image-endpoints-research.md (Lines 18-20) - Current frontend URLs
- **Dependencies**:
  - Phase 3 complete
  - Frontend testing knowledge

### Task 4.3: Update E2E tests for new image URLs

Update E2E tests that reference image URLs.

- **Files**:
  - tests/e2e/test_game_creation_flow.py - Update image URL expectations
  - tests/e2e/test_discord_embeds.py - Update embed image checks
- **Success**:
  - Tests expect new URL format
  - Tests verify images accessible publicly
  - All E2E tests pass
- **Research References**:
  - Existing E2E test patterns
- **Dependencies**:
  - Phase 3 complete
  - Tasks 4.1 and 4.2 complete

## Phase 5: Cleanup and Documentation

### Task 5.1: Remove deprecated image endpoints from games.py

Remove old authenticated image endpoints that are no longer needed.

- **Files**:
  - services/api/routes/games.py - Remove get_game_thumbnail, get_game_image endpoints (lines 845-893)
- **Success**:
  - Both endpoint functions removed
  - No references to old endpoints in codebase
  - Full test suite passes (confirms no dependencies)
  - OpenAPI docs no longer show old endpoints
- **Research References**:
  - #file:../research/20260207-02-public-image-endpoints-research.md (Lines 10-13) - Current endpoints to remove
- **Dependencies**:
  - Phase 4 complete (all consumers updated)

### Task 5.2: Update API documentation and CHANGELOG

Document the new architecture and migration in project documentation.

- **Files**:
  - docs/developer/database.md - Add game_images table to ERD
  - docs/developer/api-reference.md - Document public image endpoint
  - CHANGELOG.md - Add migration notes
  - README.md - Update if needed
- **Success**:
  - ERD includes game_images table with relationships
  - Public endpoint documented with security notes
  - CHANGELOG explains breaking change (migration drops data)
  - Migration warning visible to users
- **Research References**:
  - #file:../research/20260207-02-public-image-endpoints-research.md - Complete architecture documentation
- **Dependencies**:
  - All phases complete

## Dependencies

- PostgreSQL with gen_random_uuid() and BYPASSRLS concepts understood
- Alembic for schema migrations
- SQLAlchemy 2.x with async support
- FastAPI router and dependency injection
- slowapi for rate limiting
- pytest with async and fixtures
- httpx for HTTP testing
- Understanding of TDD Red-Green-Refactor cycle
- Understanding of reference counting patterns
- Understanding of SELECT FOR UPDATE for transaction safety

## Success Criteria

- Migration executes cleanly (upgrade and downgrade)
- GameImage model properly structured
- Image storage service passes all tests (deduplication, reference counting)
- Game service integration tests pass (create, update, delete with images)
- Public endpoint tests pass (30+ tests total)
- Rate limiting enforced correctly
- Bot and frontend updated successfully
- E2E tests pass with new architecture
- Old endpoints removed without regressions
- Documentation complete and accurate
- Zero BYPASSRLS credentials used for public endpoint
- Principle of least privilege maintained throughout
