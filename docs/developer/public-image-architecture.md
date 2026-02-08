# Public Image Architecture

## Overview

Game images (thumbnails and banners) are served through a secure public endpoint that follows the principle of least privilege. Images are stored in a separate table without Row-Level Security (RLS), enabling public access without requiring BYPASSRLS credentials.

## Architecture

### Database Schema

**game_images Table (No RLS)**

- `id` - UUID primary key
- `content_hash` - SHA256 hash for deduplication
- `image_data` - Binary image data
- `mime_type` - Image MIME type
- `reference_count` - Reference counting for automatic cleanup
- `created_at` - Timestamp
- `updated_at` - Timestamp

**game_sessions Table Updates**

- Removed: `thumbnail_data`, `thumbnail_mime_type`, `image_data`, `image_mime_type`
- Added: `thumbnail_id` (FK to game_images), `banner_image_id` (FK to game_images)

### Security Model

**Principle of Least Privilege:**

- Public endpoint uses regular database credentials (no BYPASSRLS)
- Can only access `game_images` table (no RLS policies)
- Cannot access game metadata (titles, descriptions, Discord IDs, participants)
- Programming errors cannot expose sensitive data across guild boundaries

**Comparison to Previous Architecture:**

- Old: Images in `game_sessions` table with RLS enabled
- Old: Required BYPASSRLS credentials for public access
- Old: One error could expose all game data across all guilds
- New: Images isolated in separate table without RLS
- New: Public endpoint limited to binary image data only

## Image Deduplication

### Content Hashing

Images are deduplicated using SHA256 content hashing:

```python
content_hash = hashlib.sha256(image_data).hexdigest()
```

When the same image is uploaded to multiple games:

1. Hash is computed and checked against existing images
2. If hash exists, reference count is incremented
3. If hash is new, image is stored with reference_count=1
4. All games referencing the same image share the same row

### Reference Counting

Reference counting ensures automatic cleanup:

- Each game referencing an image increments the count
- When a game is deleted or image is replaced, count is decremented
- When count reaches zero, the image is automatically deleted
- No orphaned images accumulate in the database

## API Endpoints

### Public Image Endpoint

**GET /api/v1/public/images/{image_id}**
**HEAD /api/v1/public/images/{image_id}**

Serves images without authentication. Available for Discord embeds and public access.

**Response Headers:**

- `Content-Type`: Image MIME type (e.g., `image/png`)
- `Cache-Control`: `public, max-age=3600` (1 hour browser caching)
- `Access-Control-Allow-Origin`: `*` (allows Discord embeds)

**Rate Limiting:**

- 60 requests/minute per IP (1/sec average, allows bursts)
- 100 requests/5 minutes per IP (prevents sustained abuse)

**Status Codes:**

- `200 OK` - Image found and served
- `404 Not Found` - Image does not exist
- `429 Too Many Requests` - Rate limit exceeded

### Authenticated Endpoints (Deprecated - Removed)

The following endpoints were removed in favor of the public endpoint:

- ~~GET /api/v1/games/{game_id}/thumbnail~~ - Use public endpoint instead
- ~~GET /api/v1/games/{game_id}/image~~ - Use public endpoint instead

## Usage

### From Frontend

```typescript
// Display thumbnail
<img
  src={`/api/v1/public/images/${game.thumbnail_id}`}
  alt="Game thumbnail"
/>

// Display banner
<img
  src={`/api/v1/public/images/${game.banner_image_id}`}
  alt="Game banner"
/>
```

### From Discord Bot

```python
# Generate public URL for Discord embed
thumbnail_url = f"{config.backend_url}/api/v1/public/images/{game.thumbnail_id}"
banner_url = f"{config.backend_url}/api/v1/public/images/{game.banner_image_id}"

# Use in embed
embed.set_thumbnail(url=thumbnail_url)
embed.set_image(url=banner_url)
```

## Implementation Details

### Image Storage Service

Located in `shared/services/image_storage.py`:

**store_image(db, image_data, mime_type) -> str**

- Computes SHA256 hash of image data
- Checks for existing image with same hash
- If found, increments reference_count and returns existing ID
- If new, creates image with reference_count=1
- Returns image ID

**release_image(db, image_id) -> None**

- Decrements reference_count for the image
- If count reaches zero, deletes the image
- No-op if image_id is None or image not found

### Game Service Integration

**create_game():**

- Calls `store_image()` for uploaded thumbnails/banners
- Stores returned image IDs in game session

**update_game():**

- Calls `release_image()` for old images being replaced
- Calls `store_image()` for new images
- Updates game session with new image IDs

**delete_game():**

- Calls `release_image()` for thumbnail and banner
- Deletes game session (FK constraints set to ON DELETE SET NULL)

## Migration Notes

**Schema Migration:** alembic/versions/dc81dd7fe299*migrate_images_to_separate_table_with*\*.py

**Data Migration:** Not performed - images must be re-uploaded

- No production deployment existed at time of migration
- Development/staging data is recreatable
- Existing images were dropped during schema migration

**Rollback:** Downgrade migration recreates old columns (empty)

## Testing

### Integration Tests

**Image Storage Tests** (`tests/integration/shared/services/test_image_storage.py`):

- Store new images
- Deduplicate identical images
- Increment/decrement reference counts
- Delete images when count reaches zero
- Handle concurrent operations safely

**Game Service Integration** (`tests/integration/services/api/services/test_game_image_integration.py`):

- Create games with images
- Update images (release old, store new)
- Delete games (release image references)
- Share images across multiple games
- Verify cleanup when all references removed

### Test Coverage

Total integration tests: 15

- Core storage operations: 6 tests
- Game lifecycle integration: 6 tests
- Edge cases and concurrency: 3 tests

## Dependencies

**New Dependency:** None (uses standard library hashlib for SHA256)

**Database:** PostgreSQL with `gen_random_uuid()` support

## Performance Considerations

**Storage Efficiency:**

- Identical images stored once regardless of number of games
- Typical savings: 50-80% for shared images (default templates, etc.)

**Query Performance:**

- Direct ID lookup for public endpoint (no joins)
- Content hash index for deduplication lookups
- Reference counting prevents table bloat

**Rate Limiting:**

- Prevents abuse of public endpoint
- Allows legitimate Discord embed refreshes
- Per-IP isolation prevents single abuser affecting others

## Future Enhancements

**Potential Improvements:**

- CDN integration for reduced backend load
- Image optimization/resizing at upload time
- Additional MIME types (AVIF, WebP2)
- Lazy image deletion (periodic cleanup job instead of immediate)
- Image usage analytics

## References

- [Transaction Management](transaction-management.md) - Service layer patterns
- [Database Schema](database.md) - Full schema documentation
- Research: `.copilot-tracking/research/20260207-02-public-image-endpoints-research.md`
- Implementation Plan: `.copilot-tracking/plans/20260207-02-public-image-endpoints-plan.instructions.md`
