<!-- markdownlint-disable-file -->

# Task Details: Game Image Upload Feature

## Research Reference

**Source Research**: #file:../research/20251218-game-image-attachments-research.md

## Phase 1: Database Schema Migration

### Task 1.1: Create Alembic migration for image storage columns

Create a new Alembic migration to add four columns to the game_sessions table for storing image binary data and MIME types.

- **Files**:
  - alembic/versions/0XX_add_game_image_storage.py - New migration file
- **Success**:
  - Migration adds thumbnail_data (LargeBinary), thumbnail_mime_type (String), image_data (LargeBinary), image_mime_type (String) columns
  - Migration is reversible with downgrade function
  - All columns are nullable
- **Research References**:
  - #file:../research/20251218-game-image-attachments-research.md (Lines 98-131) - Database storage pattern with BYTEA fields
  - #file:../research/20251218-game-image-attachments-research.md (Lines 149-180) - Migration implementation example
- **Dependencies**:
  - PostgreSQL database running
  - Alembic configuration present

### Task 1.2: Update GameSession model with image fields

Add four new mapped columns to the GameSession model using SQLAlchemy's LargeBinary type for binary data storage.

- **Files**:
  - shared/models/game.py - Update GameSession class
- **Success**:
  - Four new optional fields added: thumbnail_data, thumbnail_mime_type, image_data, image_mime_type
  - Uses Mapped[bytes | None] for binary fields
  - Uses Mapped[str | None] for MIME type fields (max length 50)
- **Research References**:
  - #file:../research/20251218-game-image-attachments-research.md (Lines 105-113) - Field specifications for model
  - #file:../research/20251218-game-image-attachments-research.md (Lines 182-197) - Model update example
- **Dependencies**:
  - Task 1.1 migration must be applied first

## Phase 2: API File Upload Endpoints

### Task 2.1: Update create_game endpoint for multipart/form-data

Convert the POST /games endpoint from accepting JSON to accepting multipart/form-data with both text fields and file uploads.

- **Files**:
  - services/api/routes/games.py - Update create_game function
- **Success**:
  - Function accepts Form() parameters for all text fields
  - Function accepts File() parameters for thumbnail and image uploads
  - File uploads are validated before storage
  - Binary data and MIME types stored in database
  - Endpoint works with both files present, one file, or no files
- **Research References**:
  - #file:../research/20251218-game-image-attachments-research.md (Lines 199-267) - API file upload implementation
  - #file:../research/20251218-game-image-attachments-research.md (Lines 36-41) - FastAPI UploadFile documentation
- **Dependencies**:
  - Task 1.2 model updates must be complete
  - FastAPI and UploadFile imports

### Task 2.2: Update update_game endpoint for file uploads

Convert the PATCH /games/{game_id} endpoint to accept multipart/form-data for updating game fields and replacing/removing images.

- **Files**:
  - services/api/routes/games.py - Update update_game function
- **Success**:
  - Function accepts Form() parameters for text fields
  - Function accepts File() parameters for new images
  - Function accepts boolean flags for remove_thumbnail and remove_image
  - Handles three scenarios: upload new, remove existing, keep existing
  - Only updates fields that are provided
- **Research References**:
  - #file:../research/20251218-game-image-attachments-research.md (Lines 269-305) - PATCH endpoint implementation
- **Dependencies**:
  - Task 2.1 create endpoint must be complete
  - Task 2.3 validation helper must exist

### Task 2.3: Add file validation helper function

Create a reusable async function to validate uploaded image files for type and size constraints.

- **Files**:
  - services/api/routes/games.py - Add \_validate_image_upload function
- **Success**:
  - Function checks MIME type against allowed list (PNG, JPEG, GIF, WebP)
  - Function checks file size is under 5MB limit
  - Raises HTTPException with 400 status and descriptive message on validation failure
  - Resets file pointer to beginning after size check
- **Research References**:
  - #file:../research/20251218-game-image-attachments-research.md (Lines 133-147) - Validation requirements and limits
  - #file:../research/20251218-game-image-attachments-research.md (Lines 235-256) - Validation function implementation
- **Dependencies**:
  - FastAPI HTTPException import

## Phase 3: Image Serving Endpoints

### Task 3.1: Add GET /games/{game_id}/thumbnail endpoint

Create a new endpoint to serve the thumbnail image binary data with appropriate Content-Type headers.

- **Files**:
  - services/api/routes/games.py - Add get_game_thumbnail function
- **Success**:
  - Returns 404 if game not found
  - Returns 404 if game exists but has no thumbnail
  - Returns Response with binary content and correct MIME type
  - Sets Cache-Control header to public, max-age=3600
  - No authentication required (public endpoint for Discord)
- **Research References**:
  - #file:../research/20251218-game-image-attachments-research.md (Lines 163-184) - Image serving strategy and URL generation
  - #file:../research/20251218-game-image-attachments-research.md (Lines 307-330) - Thumbnail endpoint implementation
- **Dependencies**:
  - Task 1.2 model with image fields must exist
  - FastAPI Response import

### Task 3.2: Add GET /games/{game_id}/image endpoint

Create a new endpoint to serve the banner image binary data with appropriate Content-Type headers.

- **Files**:
  - services/api/routes/games.py - Add get_game_image function
- **Success**:
  - Returns 404 if game not found
  - Returns 404 if game exists but has no banner image
  - Returns Response with binary content and correct MIME type
  - Sets Cache-Control header to public, max-age=3600
  - No authentication required (public endpoint for Discord)
- **Research References**:
  - #file:../research/20251218-game-image-attachments-research.md (Lines 163-184) - Image serving strategy
  - #file:../research/20251218-game-image-attachments-research.md (Lines 332-357) - Image endpoint implementation
- **Dependencies**:
  - Task 3.1 thumbnail endpoint as template

## Phase 4: Frontend File Upload UI

### Task 4.1: Update TypeScript interfaces for images

Modify the game announcement formatter to generate image URLs and pass them to the embed creation function.

- **Files**:
  - services/bot/formatters/game_message.py - Update format_game_announcement and create_game_embed
- **Success**:
  - format_game_announcement accepts has_thumbnail and has_image boolean parameters
  - Generates full URLs using API_BASE_URL environment variable
  - Passes thumbnail_url and image_url to create_game_embed
  - create_game_embed calls embed.set_thumbnail() when URL provided
  - create_game_embed calls embed.set_image() when URL provided
  - URLs use format: {API_BASE_URL}/api/v1/games/{game_id}/thumbnail
- **Research References**:
  - #file:../research/20251218-game-image-attachments-research.md (Lines 359-407) - Bot formatter implementation
  - #file:../research/20251218-game-image-attachments-research.md (Lines 28-34) - Discord embed API methods
- **Dependencies**:
  - Task 3.1 and 3.2 image serving endpoints must exist
  - API_BASE_URL environment variable configured

### Task 4.2: Update bot event handlers to pass image flags

Modify bot event handlers that call the game formatter to check for image data and pass boolean flags.

- **Files**:
  - services/bot/events/handlers.py - Update \_handle_game_updated and related functions
- **Success**:
  - Handlers check game.thumbnail_data is not None
  - Handlers check game.image_data is not None
  - Pass has_thumbnail and has_image flags to format_game_announcement
  - All game announcement calls updated (create, update, reminder)
- **Research References**:
  - #file:../research/20251218-game-image-attachments-research.md (Lines 409-426) - Event handler updates
- **Dependencies**:
  - Task 4.1 formatter updates must be complete

## Phase 5: Frontend File Upload UI

### Task 5.1: Update TypeScript interfaces for images

Add image-related fields to GameSession and GameFormData interfaces.

- **Files**:
  - frontend/src/types/index.ts - Update GameSession interface
  - frontend/src/components/GameForm.tsx - Update GameFormData interface
- **Success**:
  - GameSession includes has_thumbnail and has_image boolean flags
  - GameFormData includes thumbnailFile and imageFile (File | null)
  - GameFormData includes removeThumbnail and removeImage boolean flags
  - Types allow for optional images
- **Research References**:
  - #file:../research/20251218-game-image-attachments-research.md (Lines 428-443) - TypeScript interface updates
- **Dependencies**:
  - None (pure frontend changes)

### Task 4.2: Add file input components to GameForm

Add Material-UI Button-based file input components with validation for thumbnail and banner images.

- **Files**:
  - frontend/src/components/GameForm.tsx - Add file input UI and handlers
- **Success**:
  - Two file input sections: Thumbnail and Banner
  - Each uses Button with hidden file input and label wrapper
  - Accept attribute limits to image/png,image/jpeg,image/gif,image/webp
  - Client-side validation checks file size (<5MB) and type
  - Shows selected filename after choosing file
  - Shows remove button when editing game with existing image
  - Validation shows user-friendly alert messages
- **Research References**:
  - #file:../research/20251218-game-image-attachments-research.md (Lines 186-213) - File input user experience
  - #file:../research/20251218-game-image-attachments-research.md (Lines 445-523) - File input implementation with validation
- **Dependencies**:
  - Task 4.1 TypeScript interfaces must be updated
  - Material-UI Button component

### Task 4.3: Update form submission to use FormData

Convert form submission from JSON to multipart/form-data using the FormData API.

- **Files**:
  - frontend/src/pages/CreateGame.tsx - Update handleSubmit
  - frontend/src/pages/EditGame.tsx - Update handleSubmit
- **Success**:
  - Create new FormData() instance
  - Append all text fields using .append()
  - Append file uploads when present
  - Append remove flags when true (for PATCH)
  - Don't set Content-Type header (browser sets with boundary)
  - Keep Authorization header for authentication
  - PATCH only appends changed fields
- **Research References**:
  - #file:../research/20251218-game-image-attachments-research.md (Lines 525-582) - Form submission implementation for POST
  - #file:../research/20251218-game-image-attachments-research.md (Lines 584-622) - Form submission implementation for PATCH
- **Dependencies**:
  - Task 4.2 file input components must capture files
  - Task 2.1 and 2.2 API endpoints must accept FormData

## Phase 5: Frontend Image Display

### Task 5.1: Add image display to GameDetails page

Display thumbnail and banner images on the game details page when they exist.

- **Files**:
  - frontend/src/pages/GameDetails.tsx - Add image display section
- **Success**:
  - Check game.has_thumbnail and game.has_image flags
  - Display section only if at least one image exists
  - Thumbnail shown at 200x200px max with border
  - Banner shown at full width with auto height
  - Images use src pointing to API endpoints: /api/v1/games/{id}/thumbnail or /image
  - Images have appropriate alt text
  - Styled with Material-UI Box component
- **Research References**:
  - #file:../research/20251218-game-image-attachments-research.md (Lines 624-664) - Image display implementation
- **Dependencies**:
  - Task 3.1 and 3.2 image serving endpoints must work
  - Task 7.2 GameResponse must include has_thumbnail/has_image flags

## Phase 6: Discord Bot Integration

### Task 6.1: Update game message formatter to accept image flags

Modify the game announcement formatter to generate image URLs and pass them to the embed creation function.

- **Files**:
  - services/bot/formatters/game_message.py - Update format_game_announcement and create_game_embed
- **Success**:
  - format_game_announcement accepts has_thumbnail and has_image boolean parameters
  - Generates full URLs using API_BASE_URL environment variable
  - Passes thumbnail_url and image_url to create_game_embed
  - create_game_embed calls embed.set_thumbnail() when URL provided
  - create_game_embed calls embed.set_image() when URL provided
  - URLs use format: {API_BASE_URL}/api/v1/games/{game_id}/thumbnail
- **Research References**:
  - #file:../research/20251218-game-image-attachments-research.md (Lines 359-407) - Bot formatter implementation
  - #file:../research/20251218-game-image-attachments-research.md (Lines 28-34) - Discord embed API methods
- **Dependencies**:
  - Task 3.1 and 3.2 image serving endpoints must exist
  - API_BASE_URL environment variable configured

### Task 6.2: Update bot event handlers to pass image flags

Modify bot event handlers that call the game formatter to check for image data and pass boolean flags.

- **Files**:
  - services/bot/events/handlers.py - Update \_handle_game_updated and related functions
- **Success**:
  - Handlers check game.thumbnail_data is not None
  - Handlers check game.image_data is not None
  - Pass has_thumbnail and has_image flags to format_game_announcement
  - All game announcement calls updated (create, update, reminder)
- **Research References**:
  - #file:../research/20251218-game-image-attachments-research.md (Lines 409-426) - Event handler updates
- **Dependencies**:
  - Task 6.1 formatter updates must be complete

## Phase 7: Environment and Schema Updates

### Task 7.1: Add API_BASE_URL environment variable

Add API_BASE_URL configuration to all environment files for bot to generate image URLs.

- **Files**:
  - env/env.dev - Add API_BASE_URL=http://api:8000
  - env/env.int - Add API_BASE_URL=http://api:8000
  - env/env.e2e - Add API_BASE_URL=http://api:8000
  - env/env.prod - Add API_BASE_URL (set to production API URL)
  - env/env.staging - Add API_BASE_URL (set to staging API URL)
- **Success**:
  - Variable is accessible to bot service
  - Bot can construct full image URLs
  - URLs work from Discord (external access)
- **Research References**:
  - #file:../research/20251218-game-image-attachments-research.md (Lines 666-673) - Environment configuration
- **Dependencies**:
  - None (configuration only)

### Task 7.2: Update GameResponse schema with image flags

Add has_thumbnail and has_image boolean fields to GameResponse schema for API consumers.

- **Files**:
  - shared/schemas/game.py - Update GameResponse class
- **Success**:
  - has_thumbnail field defaults to False
  - has_image field defaults to False
  - from_orm method checks if thumbnail_data is not None
  - from_orm method checks if image_data is not None
  - API responses include these flags for frontend consumption
- **Research References**:
  - #file:../research/20251218-game-image-attachments-research.md (Lines 675-690) - Schema response updates
- **Dependencies**:
  - Task 1.2 model must have image data fields

## Phase 8: Testing

### Task 8.1: Add unit tests for model and validation

Create unit tests for model storage, file validation, and image serving endpoints.

- **Files**:
  - tests/shared/models/test_game.py - Add image storage tests
  - tests/services/api/routes/test_games.py - Add validation and serving tests
  - tests/services/bot/formatters/test_game_message.py - Add embed image tests
- **Success**:
  - Test game model with images stores data correctly
  - Test game model without images has null values
  - Test upload with valid file type succeeds
  - Test upload with invalid file type returns 400 error
  - Test upload with file >5MB returns 400 error
  - Test GET thumbnail returns correct data and content-type
  - Test GET thumbnail for game without image returns 404
  - Test embed formatter includes image URLs when flags are true
  - Test embed formatter excludes image URLs when flags are false
- **Research References**:
  - #file:../research/20251218-game-image-attachments-research.md (Lines 694-793) - Unit test examples
- **Dependencies**:
  - All implementation phases must be complete

### Task 8.2: Add integration tests for upload flow

Create integration tests that verify the complete upload, storage, and retrieval workflow.

- **Files**:
  - tests/integration/test_game_images.py - New integration test file
- **Success**:
  - Test creates game with thumbnail and banner via POST
  - Test retrieves thumbnail via GET and verifies binary content matches
  - Test retrieves banner via GET and verifies binary content matches
  - Test updates game to replace images
  - Test updates game to remove images
  - Tests use realistic fake image data (PNG/JPEG bytes)
- **Research References**:
  - #file:../research/20251218-game-image-attachments-research.md (Lines 795-829) - Integration test example
- **Dependencies**:
  - Task 8.1 unit tests should be passing
  - Database test fixtures must support image fields

## Dependencies

- PostgreSQL with BYTEA support
- FastAPI UploadFile and File
- Discord.py with Embed support
- SQLAlchemy LargeBinary column type
- Material-UI Button component

## Success Criteria

- All 8 phases completed and checked off
- Database migration applied successfully
- API endpoints accept and validate file uploads
- Images served with correct MIME types and cache headers
- Discord embeds display images when uploaded
- Frontend forms support full file lifecycle (upload, replace, remove)
- Frontend displays images on detail page
- All unit tests pass
- All integration tests pass
- Manual testing verifies end-to-end functionality
