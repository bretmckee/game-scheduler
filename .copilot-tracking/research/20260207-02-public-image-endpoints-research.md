<!-- markdownlint-disable-file -->

# Task Research Notes: Secure Public Image Architecture with Deduplication

## Research Executed

### File Analysis

- services/api/routes/games.py
  - Lines 845-893: Current authenticated image endpoints (`get_game_thumbnail`, `get_game_image`)
  - Lines 63-86: `_validate_image_upload` enforces 5MB max, validates MIME types (PNG, JPEG, GIF, WebP)
  - Lines 93-110: `_get_game_service` dependency requires authentication via `get_current_user`
- services/bot/formatters/game_message.py
  - Line 404: Bot generates thumbnail URL: `f"{config.backend_url}/api/v1/games/{game_id}/thumbnail"`
  - Line 407: Bot generates image URL: `f"{config.backend_url}/api/v1/games/{game_id}/image"`
- frontend/src/pages/GameDetails.tsx
  - Line 361: Frontend displays thumbnail: `src={'/api/v1/games/${game.id}/thumbnail'}`
  - Line 380: Frontend displays image: `src={'/api/v1/games/${game.id}/image'}`
- frontend/src/constants/ui.ts
  - Line 44: Frontend enforces 5MB max file size
- shared/models/game.py
  - Lines 107-110: Images stored directly on `game_sessions` table with RLS enabled
  - `thumbnail_data: bytes`, `thumbnail_mime_type: str`
  - `image_data: bytes`, `image_mime_type: str`
- shared/database.py
  - Lines 56-69: `BOT_DATABASE_URL` with BYPASSRLS privilege
  - Lines 193-210: `get_bypass_db_session()` for system operations requiring BYPASSRLS

### Git History Analysis

- Commit `fcd3b23` (2024): Original implementation - endpoints were unauthenticated
- Commit `8cb8b9e` (2026-01-02): **Regression introduced** - authentication added to `_get_game_service`
  - Inadvertently broke Discord embeds (Discord cannot send auth cookies)

### External Research

- #fetch:https://discord.com/developers/docs/resources/channel#embed-object
  - Discord embed fields require publicly accessible URLs
  - Discord does not send authentication headers or cookies when fetching images

### Project Conventions

- Standards referenced: RESTful API design, FastAPI dependency injection, TDD methodology, principle of least privilege
- TDD instruction file: `.github/instructions/test-driven-development.instructions.md`
- Router organization: Separate routers by resource type (games, templates, auth, export, public)

## Key Discoveries

### Problem Statement

Image endpoints require authentication due to `_get_game_service` dependency, breaking Discord embeds. Images are stored in `game_sessions` table **with RLS enabled**, requiring BYPASSRLS credentials for public access.

### Security Risk: BYPASSRLS for Public Endpoints

**Critical Security Issue:**

- `game_sessions` table has RLS enabled for guild isolation
- Public endpoint must serve images across all guilds
- Would require BYPASSRLS credentials (`gamebot_bot` user)
- **Blast radius**: One programming error exposes **all game data across all guilds**
  - Game titles, descriptions, signup instructions
  - Discord IDs (guilds, channels, messages, users)
  - Participant lists and host information
  - Scheduled times and metadata

**Violation of Least Privilege:**

- Public endpoint only needs image binary data
- BYPASSRLS grants access to **entire** `game_sessions` table
- Cannot limit scope of credentials

### Secure Solution: Separate Image Table

**Architecture Decision:**

- Create `game_images` table **without RLS**
- Public endpoint uses regular credentials (no BYPASSRLS)
- Images isolated from game metadata

**Security Boundary:**

- ✅ Public endpoint can only access image binary data
- ❌ Cannot access game metadata (titles, descriptions, etc.)
- ❌ Cannot access Discord IDs
- ❌ Cannot access participant information
- ❌ Cannot cross security boundaries even with programming errors

## Recommended Approach: Secure Architecture with Deduplication

### Database Schema (Enhanced)

**New `game_images` Table (No RLS):**

```sql
CREATE TABLE game_images (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    content_hash VARCHAR(64) UNIQUE NOT NULL,  -- SHA256 for deduplication
    image_data BYTEA NOT NULL,
    mime_type VARCHAR(50) NOT NULL,
    reference_count INTEGER NOT NULL DEFAULT 0,  -- Reference counting
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_game_images_content_hash ON game_images(content_hash);

-- No RLS policies on this table
```

**Modified `game_sessions` Table:**

```sql
ALTER TABLE game_sessions
    ADD COLUMN thumbnail_id UUID REFERENCES game_images(id) ON DELETE SET NULL,
    ADD COLUMN banner_image_id UUID REFERENCES game_images(id) ON DELETE SET NULL;

ALTER TABLE game_sessions
    DROP COLUMN thumbnail_data,
    DROP COLUMN thumbnail_mime_type,
    DROP COLUMN image_data,
    DROP COLUMN image_mime_type;
```

### URL Design: `/api/v1/public/images/{image_id}`

**Endpoints:**

- `GET /api/v1/public/images/{image_id}` - Serve image by ID (thumbnail or banner)
- `HEAD /api/v1/public/images/{image_id}` - Check image existence

**Rationale:**

1. `/public/` prefix explicitly signals no authentication required
2. Direct ID lookup - no need to join with `game_sessions`
3. Simple, RESTful, and secure by design
4. Single endpoint serves both thumbnails and banners

### Image Deduplication with Content Hashing

**Hash-Based Deduplication:**

```python
import hashlib

async def store_image(
    db: AsyncSession,
    image_data: bytes,
    mime_type: str
) -> str:
    """
    Store image with automatic deduplication via SHA256 hash.

    Returns image_id (existing or newly created).
    """
    # Compute content hash
    content_hash = hashlib.sha256(image_data).hexdigest()

    # Check for existing image with SELECT FOR UPDATE (prevent race conditions)
    stmt = (
        select(GameImage)
        .where(GameImage.content_hash == content_hash)
        .with_for_update()
    )
    result = await db.execute(stmt)
    existing_image = result.scalar_one_or_none()

    if existing_image:
        # Image already exists - increment reference count
        existing_image.reference_count += 1
        await db.flush()
        return existing_image.id
    else:
        # New image - create with reference_count = 1
        new_image = GameImage(
            content_hash=content_hash,
            image_data=image_data,
            mime_type=mime_type,
            reference_count=1
        )
        db.add(new_image)
        await db.flush()
        return new_image.id
```

**Reference Counting:**

```python
async def release_image(db: AsyncSession, image_id: str | None) -> None:
    """
    Decrement reference count, delete image if count reaches zero.
    """
    if not image_id:
        return

    stmt = select(GameImage).where(GameImage.id == image_id)
    result = await db.execute(stmt)
    image = result.scalar_one_or_none()

    if not image:
        return  # Already deleted

    image.reference_count -= 1

    if image.reference_count <= 0:
        await db.delete(image)

    await db.flush()
```

**Integration with Game Lifecycle:**

```python
async def update_game_images(
    db: AsyncSession,
    game: GameSession,
    new_thumbnail_data: bytes | None,
    new_thumbnail_mime: str | None,
    new_banner_data: bytes | None,
    new_banner_mime: str | None,
) -> None:
    """Update game images with automatic deduplication and cleanup."""
    # Release old thumbnail if being replaced
    if new_thumbnail_data and game.thumbnail_id:
        await release_image(db, game.thumbnail_id)
        game.thumbnail_id = None

    # Release old banner if being replaced
    if new_banner_data and game.banner_image_id:
        await release_image(db, game.banner_image_id)
        game.banner_image_id = None

    # Store new thumbnail
    if new_thumbnail_data:
        game.thumbnail_id = await store_image(db, new_thumbnail_data, new_thumbnail_mime)

    # Store new banner
    if new_banner_data:
        game.banner_image_id = await store_image(db, new_banner_data, new_banner_mime)

    await db.flush()

async def delete_game(db: AsyncSession, game_id: str) -> None:
    """Delete game and release image references."""
    game = await get_game(db, game_id)

    # Release image references (decrement counts, delete if zero)
    await release_image(db, game.thumbnail_id)
    await release_image(db, game.banner_image_id)

    # Delete game (ON DELETE SET NULL handles FK cleanup)
    await db.delete(game)
    await db.flush()
```

**Benefits:**

- **Storage Optimization**: Same image uploaded to multiple games stored once
- **Performance**: O(1) hash lookup with index
- **Automatic Cleanup**: Images deleted when last reference removed
- **No Orphans**: Reference counting prevents dangling image data

### Rate Limiting for Public Endpoints

**Rate Limit Configuration:**

```python
# Add dependency: slowapi = "^0.1.9"

from slowapi import Limiter
from slowapi.util import get_remote_address
from fastapi import Request

# In services/api/main.py:
limiter = Limiter(key_func=get_remote_address)

# In services/api/routes/public.py:
@router.get("/{image_id}", operation_id="get_public_image")
@limiter.limit("60/minute")  # 1 req/sec average, allows bursts
@limiter.limit("100/5minutes")  # Prevent sustained abuse
async def get_image(
    image_id: str,
    request: Request,  # Required for limiter
    db: AsyncSession = Depends(database.get_db),
) -> Response:
    """Serve image by ID (public, no auth required)."""
    stmt = select(GameImage.image_data, GameImage.mime_type).where(
        GameImage.id == image_id
    )
    result = await db.execute(stmt)
    row = result.first()

    if not row or not row.image_data:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Image not found",
        )

    return Response(
        content=row.image_data,
        media_type=row.mime_type or "image/png",
        headers={
            "Cache-Control": "public, max-age=3600",
            "Access-Control-Allow-Origin": "*",  # Discord embeds
        },
    )
```

**Rate Limiting Strategy:**

- **60 requests/minute**: Matches Discord's typical embed refresh (1/sec average)
- **100 requests/5 minutes**: Prevents sustained abuse patterns
- **Per IP address**: Using `get_remote_address` for isolation
- **Allows bursts**: Short-term bursts permitted within minute limit

### Existing Protections (Confirmed)

**Image Size Limits (Already Enforced):**

- Backend validation: **5 MB max** (`services/api/routes/games.py:84`)
- Frontend validation: **5 MB max** (`frontend/src/constants/ui.ts:44`)
- Allowed MIME types: PNG, JPEG, GIF, WebP

**No Additional Limits Needed**: Existing constraints sufficient for public endpoints.

### Database Migration Strategy

**Schema-Only Migration (No Data Preservation):**

Given no production deployment and recreatable staging/dev data, migration will drop existing image columns and create new architecture without data migration.

```python
"""Migrate to separate game_images table with deduplication

Revision ID: <generated>
Revises: <previous>
Create Date: 2026-02-08

⚠️ WARNING: This migration drops existing image data.
   All images must be re-uploaded after migration.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

def upgrade() -> None:
    # Drop old image columns from game_sessions (data loss)
    op.drop_column('game_sessions', 'thumbnail_data')
    op.drop_column('game_sessions', 'thumbnail_mime_type')
    op.drop_column('game_sessions', 'image_data')
    op.drop_column('game_sessions', 'image_mime_type')

    # Create new game_images table (no RLS)
    op.create_table(
        'game_images',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text('gen_random_uuid()')),
        sa.Column('content_hash', sa.String(64), unique=True, nullable=False),
        sa.Column('image_data', sa.LargeBinary(), nullable=False),
        sa.Column('mime_type', sa.String(50), nullable=False),
        sa.Column('reference_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now()),
    )

    # Create index on content_hash for deduplication lookups
    op.create_index('idx_game_images_content_hash', 'game_images', ['content_hash'])

    # Add new FK columns to game_sessions
    op.add_column('game_sessions',
                  sa.Column('thumbnail_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('game_sessions',
                  sa.Column('banner_image_id', postgresql.UUID(as_uuid=True), nullable=True))

    # Create foreign key constraints with ON DELETE SET NULL
    op.create_foreign_key(
        'fk_game_sessions_thumbnail_id',
        'game_sessions', 'game_images',
        ['thumbnail_id'], ['id'],
        ondelete='SET NULL'
    )
    op.create_foreign_key(
        'fk_game_sessions_banner_image_id',
        'game_sessions', 'game_images',
        ['banner_image_id'], ['id'],
        ondelete='SET NULL'
    )

def downgrade() -> None:
    # Remove FK constraints
    op.drop_constraint('fk_game_sessions_banner_image_id', 'game_sessions')
    op.drop_constraint('fk_game_sessions_thumbnail_id', 'game_sessions')

    # Remove FK columns
    op.drop_column('game_sessions', 'banner_image_id')
    op.drop_column('game_sessions', 'thumbnail_id')

    # Drop game_images table
    op.drop_index('idx_game_images_content_hash')
    op.drop_table('game_images')

    # Restore old columns (empty - data not recoverable)
    op.add_column('game_sessions',
                  sa.Column('thumbnail_data', sa.LargeBinary(), nullable=True))
    op.add_column('game_sessions',
                  sa.Column('thumbnail_mime_type', sa.String(50), nullable=True))
    op.add_column('game_sessions',
                  sa.Column('image_data', sa.LargeBinary(), nullable=True))
    op.add_column('game_sessions',
                  sa.Column('image_mime_type', sa.String(50), nullable=True))
```

**Migration Considerations:**

- ✅ Simple, straightforward schema changes
- ✅ No complex data migration logic
- ✅ Fast execution
- ⚠️ Existing images lost (acceptable for non-prod)

## Implementation Guidance: TDD with Comprehensive Integration Tests

Following Red-Green-Refactor methodology from `.github/instructions/test-driven-development.instructions.md`.

### Integration Test Coverage Requirements

Integration tests can cover complete functionality since everything except Discord bot is available:

**Test Categories:**

1. **Image Storage & Deduplication**: Store images, verify hash-based dedup works
2. **Reference Counting**: Increment/decrement counts, verify cleanup
3. **Public Endpoint**: Serve images without authentication, proper headers
4. **Game Lifecycle**: Upload images with games, update images, delete games
5. **Concurrent Operations**: Race conditions in deduplication
6. **Rate Limiting**: Verify limits enforced correctly
7. **Edge Cases**: Missing images, invalid IDs, HEAD requests, CORS

## Implementation Guidance (TDD Phases)

### Phase 0: Database Migration and Models

**Tasks:**

- [ ] **Task 0.1**: Create database migration (schema-only)
  - Create Alembic migration dropping old columns, creating `game_images` table
  - Add FK columns to `game_sessions`: `thumbnail_id`, `banner_image_id`
  - Run migration: `alembic upgrade head`

- [ ] **Task 0.2**: Create `GameImage` model
  - Add `shared/models/game_image.py` with SQLAlchemy model
  - Include: `id`, `content_hash`, `image_data`, `mime_type`, `reference_count`, timestamps
  - Update `shared/models/__init__.py` to export model

- [ ] **Task 0.3**: Update `GameSession` model
  - Remove old image columns from model
  - Add FK relationships: `thumbnail_id`, `banner_image_id`
  - Update relationship declarations

### Phase 1: Image Storage Service with Deduplication (TDD)

**RED Phase - Write Failing Tests:**

- [ ] **Task 1.1**: Create test file: `tests/integration/shared/services/test_image_storage.py`

```python
import pytest
import hashlib
from sqlalchemy.ext.asyncio import AsyncSession
from shared.models.game_image import GameImage
from shared.services.image_storage import store_image, release_image

PNG_DATA = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR...'  # Valid PNG header

@pytest.mark.asyncio
async def test_store_image_creates_new_image(db_session: AsyncSession):
    """First upload creates new image with reference_count=1."""
    image_id = await store_image(db_session, PNG_DATA, "image/png")

    result = await db_session.get(GameImage, image_id)
    assert result is not None
    assert result.image_data == PNG_DATA
    assert result.mime_type == "image/png"
    assert result.reference_count == 1
    assert result.content_hash == hashlib.sha256(PNG_DATA).hexdigest()

@pytest.mark.asyncio
async def test_store_duplicate_image_increments_count(db_session: AsyncSession):
    """Uploading same image twice increments count, returns same ID."""
    image_id_1 = await store_image(db_session, PNG_DATA, "image/png")
    image_id_2 = await store_image(db_session, PNG_DATA, "image/png")

    assert image_id_1 == image_id_2  # Same image

    result = await db_session.get(GameImage, image_id_1)
    assert result.reference_count == 2

@pytest.mark.asyncio
async def test_release_image_decrements_count(db_session: AsyncSession):
    """Releasing image decrements count, keeps image if count > 0."""
    image_id = await store_image(db_session, PNG_DATA, "image/png")
    await store_image(db_session, PNG_DATA, "image/png")  # Count = 2

    await release_image(db_session, image_id)

    result = await db_session.get(GameImage, image_id)
    assert result is not None
    assert result.reference_count == 1

@pytest.mark.asyncio
async def test_release_image_deletes_when_count_zero(db_session: AsyncSession):
    """Releasing last reference deletes image."""
    image_id = await store_image(db_session, PNG_DATA, "image/png")

    await release_image(db_session, image_id)

    result = await db_session.get(GameImage, image_id)
    assert result is None  # Image deleted

@pytest.mark.asyncio
async def test_concurrent_store_operations_safe(db_session: AsyncSession):
    """Concurrent uploads of same image handled safely (SELECT FOR UPDATE)."""
    # This tests transaction safety - would need concurrent execution
    # Simplified test: verify no duplicate content_hash created
    image_id_1 = await store_image(db_session, PNG_DATA, "image/png")
    await db_session.commit()

    # New transaction
    await db_session.begin()
    image_id_2 = await store_image(db_session, PNG_DATA, "image/png")

    assert image_id_1 == image_id_2
```

- [ ] **Task 1.2**: Run tests - verify they fail (no implementation yet)

**GREEN Phase - Implement:**

- [ ] **Task 1.3**: Create `shared/services/image_storage.py`
  - Implement `store_image()` with hash-based deduplication
  - Implement `release_image()` with reference counting
  - Use `SELECT FOR UPDATE` for transaction safety

- [ ] **Task 1.4**: Run tests - verify they pass

**REFACTOR Phase:**

- [ ] **Task 1.5**: Add edge case tests
  - Test `release_image()` with None/missing ID
  - Test different MIME types with same data
  - Test transaction rollback scenarios

### Phase 2: Game Service Integration (TDD)

**RED Phase:**

- [ ] **Task 2.1**: Create test file: `tests/integration/services/api/services/test_game_image_integration.py`

```python
@pytest.mark.asyncio
async def test_create_game_with_images_stores_and_links(
    db_session: AsyncSession,
    thumbnail_data: bytes,
    banner_data: bytes,
):
    """Creating game with images stores them and links to game."""
    game_id = await create_game(
        db_session,
        title="Test Game",
        thumbnail_data=thumbnail_data,
        thumbnail_mime="image/png",
        banner_data=banner_data,
        banner_mime="image/jpeg",
    )

    game = await db_session.get(GameSession, game_id)
    assert game.thumbnail_id is not None
    assert game.banner_image_id is not None

    # Verify images exist
    thumbnail = await db_session.get(GameImage, game.thumbnail_id)
    assert thumbnail.reference_count == 1
    banner = await db_session.get(GameImage, game.banner_image_id)
    assert banner.reference_count == 1

@pytest.mark.asyncio
async def test_update_game_replaces_images_releases_old(db_session: AsyncSession):
    """Updating game images releases old images, stores new ones."""
    game_id = await create_game(db_session, thumbnail_data=OLD_PNG)
    game = await db_session.get(GameSession, game_id)
    old_thumbnail_id = game.thumbnail_id

    await update_game_images(db_session, game_id, thumbnail_data=NEW_PNG)

    game = await db_session.get(GameSession, game_id)
    assert game.thumbnail_id != old_thumbnail_id

    # Old image should be deleted (reference_count was 1)
    old_image = await db_session.get(GameImage, old_thumbnail_id)
    assert old_image is None

@pytest.mark.asyncio
async def test_delete_game_releases_images(db_session: AsyncSession):
    """Deleting game releases image references, deletes if unused."""
    game_id = await create_game(db_session, thumbnail_data=PNG_DATA)
    game = await db_session.get(GameSession, game_id)
    thumbnail_id = game.thumbnail_id

    await delete_game(db_session, game_id)

    # Game deleted
    game = await db_session.get(GameSession, game_id)
    assert game is None

    # Image deleted (no other references)
    image = await db_session.get(GameImage, thumbnail_id)
    assert image is None

@pytest.mark.asyncio
async def test_shared_image_not_deleted_until_all_refs_gone(db_session: AsyncSession):
    """Image shared by multiple games not deleted until all games deleted."""
    # Two games share same thumbnail
    game1_id = await create_game(db_session, thumbnail_data=PNG_DATA)
    game2_id = await create_game(db_session, thumbnail_data=PNG_DATA)

    game1 = await db_session.get(GameSession, game1_id)
    image_id = game1.thumbnail_id

    # Verify same image used (deduplication worked)
    game2 = await db_session.get(GameSession, game2_id)
    assert game2.thumbnail_id == image_id

    # Delete first game
    await delete_game(db_session, game1_id)

    # Image still exists (game2 references it)
    image = await db_session.get(GameImage, image_id)
    assert image is not None
    assert image.reference_count == 1

    # Delete second game
    await delete_game(db_session, game2_id)

    # Now image deleted
    image = await db_session.get(GameImage, image_id)
    assert image is None
```

**GREEN Phase:**

- [ ] **Task 2.2**: Update game service with image storage integration
  - Modify `create_game()` to call `store_image()` for uploads
  - Modify `update_game()` to release old, store new images
  - Modify `delete_game()` to call `release_image()`

- [ ] **Task 2.3**: Run tests - verify they pass

### Phase 3: Public Image Endpoint (TDD)

**RED Phase:**

- [ ] **Task 3.1**: Create router stub: `services/api/routes/public.py`

```python
from fastapi import APIRouter
router = APIRouter(prefix="/api/v1/public/images", tags=["public"])

@router.get("/{image_id}")
@router.head("/{image_id}")
async def get_image(image_id: str):
    raise NotImplementedError("Public image endpoint not implemented")
```

- [ ] **Task 3.2**: Create test file: `tests/integration/services/api/routes/test_public_images.py`

```python
@pytest.mark.asyncio
async def test_get_image_returns_data_without_auth(
    async_client: AsyncClient,
    image_id: str,
):
    """Public endpoint serves image without authentication."""
    response = await async_client.get(f"/api/v1/public/images/{image_id}")

    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    assert len(response.content) > 0

@pytest.mark.asyncio
async def test_get_image_includes_cache_headers(async_client: AsyncClient, image_id: str):
    """Response includes cache control headers."""
    response = await async_client.get(f"/api/v1/public/images/{image_id}")

    assert "public" in response.headers["cache-control"]
    assert "max-age=3600" in response.headers["cache-control"]

@pytest.mark.asyncio
async def test_get_image_includes_cors_headers(async_client: AsyncClient, image_id: str):
    """Response includes CORS headers for Discord embeds."""
    response = await async_client.get(f"/api/v1/public/images/{image_id}")

    assert response.headers["access-control-allow-origin"] == "*"

@pytest.mark.asyncio
async def test_get_image_missing_returns_404(async_client: AsyncClient):
    """Missing image returns 404."""
    response = await async_client.get("/api/v1/public/images/nonexistent-uuid")

    assert response.status_code == 404

@pytest.mark.asyncio
async def test_head_request_returns_headers_only(
    async_client: AsyncClient,
    image_id: str,
):
    """HEAD request returns headers without body."""
    response = await async_client.head(f"/api/v1/public/images/{image_id}")

    assert response.status_code == 200
    assert "content-type" in response.headers
    assert len(response.content) == 0
```

- [ ] **Task 3.3**: Run tests - verify they fail (NotImplementedError)

**GREEN Phase:**

- [ ] **Task 3.4**: Implement public endpoint
  - Query `game_images` table by ID
  - Return image data with proper headers
  - Handle 404 for missing images

- [ ] **Task 3.5**: Register router in `services/api/main.py`
- [ ] **Task 3.6**: Run tests - verify they pass

**REFACTOR Phase:**

- [ ] **Task 3.7**: Add rate limiting tests

```python
@pytest.mark.asyncio
async def test_rate_limit_enforced_60_per_minute(async_client: AsyncClient, image_id: str):
    """Rate limit prevents > 60 requests per minute."""
    # Make 61 requests rapidly
    for i in range(61):
        response = await async_client.get(f"/api/v1/public/images/{image_id}")
        if i < 60:
            assert response.status_code == 200
        else:
            assert response.status_code == 429  # Rate limited

@pytest.mark.asyncio
async def test_rate_limit_enforced_100_per_5_minutes(async_client: AsyncClient, image_id: str):
    """Rate limit prevents > 100 requests per 5 minutes."""
    # Would need time manipulation or longer test
    pass  # Implementation detail
```

- [ ] **Task 3.8**: Add rate limiting with slowapi
- [ ] **Task 3.9**: Run full test suite - verify all pass

### Phase 4: Consumer Updates

- [ ] **Task 4.1**: Update bot message formatter
  - Change URL from `/api/v1/games/{game_id}/thumbnail` to `/api/v1/public/images/{thumbnail_id}`
  - Update integration tests for bot formatter
  - Verify tests pass

- [ ] **Task 4.2**: Update frontend image display
  - Change URL from `/api/v1/games/${game.id}/thumbnail` to `/api/v1/public/images/${game.thumbnail_id}`
  - Add frontend tests for image loading
  - Verify tests pass

- [ ] **Task 4.3**: Update E2E tests
  - Update any E2E tests referencing old image URLs
  - Verify E2E tests pass

### Phase 5: Cleanup

- [ ] **Task 5.1**: Remove old endpoints
  - Remove `get_game_thumbnail` and `get_game_image` from `services/api/routes/games.py`
  - Verify no references remain
  - Run full test suite

- [ ] **Task 5.2**: Update documentation
  - Document new public endpoints in API docs
  - Add migration notes to CHANGELOG
  - Document security model (separate table, no RLS needed)

### Test Fixtures Required

**Integration Test Fixtures** (`tests/integration/conftest.py`):

```python
@pytest.fixture
def thumbnail_data() -> bytes:
    """Valid PNG thumbnail data."""
    return b'\x89PNG\r\n\x1a\n...'  # Valid PNG header + minimal data

@pytest.fixture
def banner_data() -> bytes:
    """Valid JPEG banner data."""
    return b'\xff\xd8\xff\xe0...'  # Valid JPEG header + minimal data

@pytest.fixture
async def stored_image(db_session: AsyncSession, thumbnail_data: bytes) -> str:
    """Pre-stored image for endpoint tests."""
    from shared.services.image_storage import store_image
    image_id = await store_image(db_session, thumbnail_data, "image/png")
    await db_session.commit()
    return image_id
```

### Success Criteria

- [ ] All integration tests pass (image storage, deduplication, reference counting)
- [ ] Public endpoint serves images without authentication
- [ ] Rate limiting enforced correctly
- [ ] Images deduplicated by content hash
- [ ] Reference counting prevents orphans and premature deletion
- [ ] Shared images deleted only when last reference removed
- [ ] Game deletion properly releases image references
- [ ] Discord embeds work (CORS headers present)
- [ ] Cache headers present for CDN/browser caching
- [ ] HEAD requests supported
- [ ] Bot and frontend updated with new URLs
- [ ] E2E tests updated and passing
- [ ] Old endpoints removed
- [ ] Zero untested code paths
- [ ] No security regressions (principle of least privilege maintained)

### Dependencies

- `slowapi` for rate limiting
- SQLAlchemy async for database operations
- pytest for integration testing
- httpx for HTTP client testing
- Understanding of SELECT FOR UPDATE for transaction safety
- FastAPI dependency injection patterns
- TDD methodology (Red-Green-Refactor)
