<!-- markdownlint-disable-file -->
# Task Research Notes: Game Image Upload Feature

## Research Executed

### File Analysis

- `services/bot/formatters/game_message.py` (Lines 60-160)
  - `create_game_embed()` creates Discord embeds for game announcements
  - Currently no image support (no `set_image()` or `set_thumbnail()` calls)
  - Returns `discord.Embed` object with fields for game details

- `shared/schemas/game.py` (Lines 70-161)
  - `GameCreateRequest` and `GameUpdateRequest` define API schemas
  - `GameResponse` defines response format with all game fields
  - Currently no image fields present

- `shared/models/game.py` (Lines 47-105)
  - `GameSession` model with SQLAlchemy mappings
  - No image storage fields in current schema

- `frontend/src/components/GameForm.tsx` (Lines 72-105)
  - `GameFormData` interface defines form structure
  - Contains: title, description, signupInstructions, scheduledAt, where, etc.
  - No image upload fields currently present

- `services/api/routes/games.py`
  - Uses Pydantic schemas for request validation
  - Currently handles JSON payloads only
  - Will need multipart/form-data support for file uploads

### Code Search Results

- Discord embed searches
  - 20+ matches for `discord.Embed` across bot formatters and tests
  - No existing uses of `set_thumbnail()` or `set_image()` methods
  - All embeds are text-only currently

- FastAPI file upload patterns
  - No existing file upload endpoints in codebase
  - Will be first use of `File()` and `UploadFile` from FastAPI

### External Research

- #fetch:"https://discordpy.readthedocs.io/en/stable/api.html#discord.Embed"
  - **Thumbnail**: `embed.set_thumbnail(url)` - displays small image in upper right
  - **Image**: `embed.set_image(url)` - displays large image at bottom
  - **URL Requirements**: Must be HTTP(S) protocol only
  - Discord validates and proxies external URLs through their CDN

- #fetch:"https://fastapi.tiangolo.com/tutorial/request-files/"
  - FastAPI supports `UploadFile` for file uploads
  - Uses multipart/form-data encoding
  - Can mix files with JSON data in same request
  - `UploadFile` provides async read methods

## Key Discoveries

### Database Storage Pattern

**Binary Storage in PostgreSQL**:
- Store images as BYTEA (binary data) directly in database
- No external file storage needed
- Simple backup/restore (part of database)
- No volume mounts or CDN required

**Field Specifications**:
```python
# shared/models/game.py additions
thumbnail_data: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
thumbnail_mime_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
image_data: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
image_mime_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
```

**Why MIME Type**:
- Need to serve images with correct Content-Type header
- Allows validation of uploaded file types
- Discord needs proper MIME types for image display

### File Size and Type Validation

**Validation Requirements**:
- Max file size: 5MB per image (reasonable for game banners)
- Allowed MIME types: `image/png`, `image/jpeg`, `image/gif`, `image/webp`
- Validate on upload before storing in database
- Basic MIME type check (from file upload metadata)

**Why These Limits**:
- 5MB allows high-quality images without excessive database bloat
- Standard image formats supported by Discord
- No need for virus scanning (accepting from authenticated users only)

### Image Serving Strategy

**New API Endpoints**:
```python
GET /api/v1/games/{game_id}/thumbnail
GET /api/v1/games/{game_id}/image
```

**Response Characteristics**:
- Return binary data with appropriate Content-Type header
- 404 if game exists but no image uploaded
- Public access (no auth required) since Discord bot needs to fetch
- Cache headers for browser/Discord caching

**URL Generation**:
- Bot generates full URL: `https://{API_HOST}/api/v1/games/{game_id}/thumbnail`
- Passes URL to `embed.set_thumbnail()`
- Discord fetches and caches the image

### Frontend File Upload

**Input Type**:
- File input component (not text field)
- Accept attribute: `image/png,image/jpeg,image/gif,image/webp`
- Optional fields (both thumbnail and banner)
- Client-side file size check before upload

**Form Submission**:
- Use `multipart/form-data` instead of JSON
- FormData API in JavaScript
- Mix file uploads with other game fields
- Handle file removal (set to null)

**User Experience**:
- Simple file picker (no drag-and-drop required)
- No preview needed (user uploading their own image)
- Error messages for invalid file type or size

## Implementation Guidance

### Phase 1: Database Schema Migration

**Add Image Storage Columns**:
```python
# alembic/versions/0XX_add_game_image_storage.py
"""Add image storage for thumbnails and banners."""

def upgrade() -> None:
    op.add_column(
        'game_sessions',
        sa.Column('thumbnail_data', sa.LargeBinary(), nullable=True)
    )
    op.add_column(
        'game_sessions',
        sa.Column('thumbnail_mime_type', sa.String(length=50), nullable=True)
    )
    op.add_column(
        'game_sessions',
        sa.Column('image_data', sa.LargeBinary(), nullable=True)
    )
    op.add_column(
        'game_sessions',
        sa.Column('image_mime_type', sa.String(length=50), nullable=True)
    )

def downgrade() -> None:
    op.drop_column('game_sessions', 'image_mime_type')
    op.drop_column('game_sessions', 'image_data')
    op.drop_column('game_sessions', 'thumbnail_mime_type')
    op.drop_column('game_sessions', 'thumbnail_data')
```

**Update Model**:
```python
# shared/models/game.py
from sqlalchemy import LargeBinary, String

class GameSession(Base):
    # ... existing fields ...
    thumbnail_data: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    thumbnail_mime_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    image_data: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    image_mime_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
```

### Phase 2: API File Upload Endpoint

**Update Request Handling**:
```python
# services/api/routes/games.py
from fastapi import File, UploadFile, Form
from typing import Annotated

@router.post("/games")
async def create_game(
    # Regular fields as Form parameters
    title: Annotated[str, Form()],
    description: Annotated[str, Form()],
    scheduled_at: Annotated[str, Form()],
    guild_id: Annotated[str, Form()],
    channel_id: Annotated[str, Form()],
    max_players: Annotated[int, Form()],
    # Optional fields
    where: Annotated[str | None, Form()] = None,
    signup_instructions: Annotated[str | None, Form()] = None,
    expected_duration_minutes: Annotated[int | None, Form()] = None,
    reminder_minutes: Annotated[int | None, Form()] = None,
    notify_role_ids: Annotated[str | None, Form()] = None,  # JSON string
    # File uploads
    thumbnail: Annotated[UploadFile | None, File()] = None,
    image: Annotated[UploadFile | None, File()] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> GameResponse:
    # Validate thumbnail
    thumbnail_data = None
    thumbnail_mime = None
    if thumbnail:
        await _validate_image_upload(thumbnail, "thumbnail")
        thumbnail_data = await thumbnail.read()
        thumbnail_mime = thumbnail.content_type

    # Validate image
    image_data = None
    image_mime = None
    if image:
        await _validate_image_upload(image, "image")
        image_data = await image.read()
        image_mime = image.content_type

    # Create game with image data
    game = await game_service.create_game(
        db=db,
        # ... other fields ...
        thumbnail_data=thumbnail_data,
        thumbnail_mime_type=thumbnail_mime,
        image_data=image_data,
        image_mime_type=image_mime,
    )
    return GameResponse.model_validate(game)

async def _validate_image_upload(file: UploadFile, field_name: str) -> None:
    """Validate uploaded image file."""
    # Check MIME type
    allowed_types = {"image/png", "image/jpeg", "image/gif", "image/webp"}
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"{field_name} must be PNG, JPEG, GIF, or WebP"
        )

    # Check file size
    file.file.seek(0, 2)  # Seek to end
    size = file.file.tell()
    file.file.seek(0)  # Reset to beginning

    max_size = 5 * 1024 * 1024  # 5MB
    if size > max_size:
        raise HTTPException(
            status_code=400,
            detail=f"{field_name} must be less than 5MB"
        )
```

**Update PATCH Endpoint**:
```python
@router.patch("/games/{game_id}")
async def update_game(
    game_id: str,
    # Form fields for text data
    title: Annotated[str | None, Form()] = None,
    description: Annotated[str | None, Form()] = None,
    # ... other fields ...
    # File uploads
    thumbnail: Annotated[UploadFile | None, File()] = None,
    image: Annotated[UploadFile | None, File()] = None,
    # Special flags for deletion
    remove_thumbnail: Annotated[bool, Form()] = False,
    remove_image: Annotated[bool, Form()] = False,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> GameResponse:
    # Handle file uploads and deletions
    thumbnail_data = None
    thumbnail_mime = None
    if remove_thumbnail:
        thumbnail_data = None
        thumbnail_mime = None
    elif thumbnail:
        await _validate_image_upload(thumbnail, "thumbnail")
        thumbnail_data = await thumbnail.read()
        thumbnail_mime = thumbnail.content_type

    # Similar for image...
    # Update game with new data
```

### Phase 3: Image Serving Endpoints

**Add Image Retrieval Routes**:
```python
# services/api/routes/games.py
from fastapi.responses import Response

@router.get("/games/{game_id}/thumbnail")
async def get_game_thumbnail(
    game_id: str,
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Serve game thumbnail image."""
    game = await game_service.get_game_by_id(db, game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    if not game.thumbnail_data:
        raise HTTPException(status_code=404, detail="No thumbnail for this game")

    return Response(
        content=game.thumbnail_data,
        media_type=game.thumbnail_mime_type or "image/png",
        headers={
            "Cache-Control": "public, max-age=3600",  # Cache for 1 hour
        }
    )

@router.get("/games/{game_id}/image")
async def get_game_image(
    game_id: str,
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Serve game banner image."""
    game = await game_service.get_game_by_id(db, game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    if not game.image_data:
        raise HTTPException(status_code=404, detail="No banner image for this game")

    return Response(
        content=game.image_data,
        media_type=game.image_mime_type or "image/png",
        headers={
            "Cache-Control": "public, max-age=3600",
        }
    )
```

### Phase 4: Discord Bot Integration

**Update Bot Formatter**:
```python
# services/bot/formatters/game_message.py
import os

def format_game_announcement(
    game_id: str,
    game_title: str,
    # ... existing parameters ...
    has_thumbnail: bool = False,
    has_image: bool = False,
) -> tuple[str | None, discord.Embed, GameView]:
    # Generate image URLs if images exist
    api_base_url = os.getenv("API_BASE_URL", "http://api:8000")

    thumbnail_url = None
    if has_thumbnail:
        thumbnail_url = f"{api_base_url}/api/v1/games/{game_id}/thumbnail"

    image_url = None
    if has_image:
        image_url = f"{api_base_url}/api/v1/games/{game_id}/image"

    embed = GameMessageFormatter.create_game_embed(
        game_title=game_title,
        # ... existing parameters ...
        thumbnail_url=thumbnail_url,
        image_url=image_url,
    )
    # ... rest of function ...

@staticmethod
def create_game_embed(
    game_title: str,
    description: str,
    # ... existing parameters ...
    thumbnail_url: str | None = None,
    image_url: str | None = None,
) -> discord.Embed:
    # ... existing embed creation code ...

    # Set thumbnail (upper right)
    if thumbnail_url:
        embed.set_thumbnail(url=thumbnail_url)

    # Set image (bottom of embed)
    if image_url:
        embed.set_image(url=image_url)

    return embed
```

**Update Bot Event Handler**:
```python
# services/bot/events/handlers.py
async def _handle_game_updated(event: GameEvent) -> None:
    # ... fetch game data ...

    content, embed, view = format_game_announcement(
        game_id=str(game.id),
        # ... existing parameters ...
        has_thumbnail=game.thumbnail_data is not None,
        has_image=game.image_data is not None,
    )
    # ... update Discord message ...
```

### Phase 5: Frontend File Input

**Update TypeScript Interfaces**:
```typescript
// frontend/src/types/index.ts
export interface GameSession {
  // ... existing fields ...
  has_thumbnail: boolean;  // Indicator that thumbnail exists
  has_image: boolean;      // Indicator that banner exists
}

// frontend/src/components/GameForm.tsx
export interface GameFormData {
  // ... existing fields ...
  thumbnailFile: File | null;
  imageFile: File | null;
  removeThumbnail: boolean;
  removeImage: boolean;
}
```

**Update Form Component**:
```tsx
// frontend/src/components/GameForm.tsx
import { Button } from '@mui/material';

const [formData, setFormData] = useState<GameFormData>({
  // ... existing fields ...
  thumbnailFile: null,
  imageFile: null,
  removeThumbnail: false,
  removeImage: false,
});

const handleThumbnailChange = (event: React.ChangeEvent<HTMLInputElement>) => {
  const file = event.target.files?.[0] || null;

  // Validate file size
  if (file && file.size > 5 * 1024 * 1024) {
    alert('Thumbnail must be less than 5MB');
    return;
  }

  // Validate file type
  if (file && !['image/png', 'image/jpeg', 'image/gif', 'image/webp'].includes(file.type)) {
    alert('Thumbnail must be PNG, JPEG, GIF, or WebP');
    return;
  }

  setFormData(prev => ({
    ...prev,
    thumbnailFile: file,
    removeThumbnail: false,
  }));
};

const handleImageChange = (event: React.ChangeEvent<HTMLInputElement>) => {
  const file = event.target.files?.[0] || null;

  if (file && file.size > 5 * 1024 * 1024) {
    alert('Banner image must be less than 5MB');
    return;
  }

  if (file && !['image/png', 'image/jpeg', 'image/gif', 'image/webp'].includes(file.type)) {
    alert('Banner must be PNG, JPEG, GIF, or WebP');
    return;
  }

  setFormData(prev => ({
    ...prev,
    imageFile: file,
    removeImage: false,
  }));
};

// In form render:
<Box sx={{ mt: 2 }}>
  <Typography variant="subtitle2" gutterBottom>
    Thumbnail Image (optional)
  </Typography>
  <Button
    variant="outlined"
    component="label"
    disabled={loading}
  >
    Choose Thumbnail
    <input
      type="file"
      hidden
      accept="image/png,image/jpeg,image/gif,image/webp"
      onChange={handleThumbnailChange}
    />
  </Button>
  {formData.thumbnailFile && (
    <Typography variant="body2" sx={{ ml: 2, display: 'inline' }}>
      {formData.thumbnailFile.name}
    </Typography>
  )}
  {initialData?.has_thumbnail && !formData.thumbnailFile && (
    <Button
      size="small"
      color="error"
      onClick={() => setFormData(prev => ({ ...prev, removeThumbnail: true }))}
      disabled={loading}
    >
      Remove Thumbnail
    </Button>
  )}
</Box>

<Box sx={{ mt: 2 }}>
  <Typography variant="subtitle2" gutterBottom>
    Banner Image (optional)
  </Typography>
  <Button
    variant="outlined"
    component="label"
    disabled={loading}
  >
    Choose Banner
    <input
      type="file"
      hidden
      accept="image/png,image/jpeg,image/gif,image/webp"
      onChange={handleImageChange}
    />
  </Button>
  {formData.imageFile && (
    <Typography variant="body2" sx={{ ml: 2, display: 'inline' }}>
      {formData.imageFile.name}
    </Typography>
  )}
  {initialData?.has_image && !formData.imageFile && (
    <Button
      size="small"
      color="error"
      onClick={() => setFormData(prev => ({ ...prev, removeImage: true }))}
      disabled={loading}
    >
      Remove Banner
    </Button>
  )}
</Box>
```

**Update Form Submission**:
```tsx
// frontend/src/pages/CreateGame.tsx
const handleSubmit = async (formData: GameFormData) => {
  const payload = new FormData();

  // Add text fields
  payload.append('title', formData.title);
  payload.append('description', formData.description);
  payload.append('scheduled_at', formData.scheduledAt);
  payload.append('guild_id', selectedGuild);
  payload.append('channel_id', formData.channelId);
  payload.append('max_players', formData.maxPlayers.toString());

  if (formData.where) payload.append('where', formData.where);
  if (formData.signupInstructions) payload.append('signup_instructions', formData.signupInstructions);
  // ... other optional fields ...

  // Add file uploads
  if (formData.thumbnailFile) {
    payload.append('thumbnail', formData.thumbnailFile);
  }
  if (formData.imageFile) {
    payload.append('image', formData.imageFile);
  }

  // Send multipart request
  const response = await fetch('/api/v1/games', {
    method: 'POST',
    body: payload,
    // Note: Don't set Content-Type header - browser sets it with boundary
    headers: {
      'Authorization': `Bearer ${token}`,
    },
  });

  // ... handle response ...
};
```

**Update PATCH Request**:
```tsx
// frontend/src/pages/EditGame.tsx
const handleSubmit = async (formData: GameFormData) => {
  const payload = new FormData();

  // Add only changed fields
  if (formData.title !== initialData.title) {
    payload.append('title', formData.title);
  }
  // ... other fields ...

  // File uploads
  if (formData.thumbnailFile) {
    payload.append('thumbnail', formData.thumbnailFile);
  }
  if (formData.removeThumbnail) {
    payload.append('remove_thumbnail', 'true');
  }

  if (formData.imageFile) {
    payload.append('image', formData.imageFile);
  }
  if (formData.removeImage) {
    payload.append('remove_image', 'true');
  }

  const response = await fetch(`/api/v1/games/${gameId}`, {
    method: 'PATCH',
    body: payload,
    headers: {
      'Authorization': `Bearer ${token}`,
    },
  });

  // ... handle response ...
};
```

### Phase 6: Frontend Image Display

**Update GameDetails Page**:
```tsx
// frontend/src/pages/GameDetails.tsx
{(game.has_thumbnail || game.has_image) && (
  <Box sx={{ mb: 3 }}>
    {game.has_thumbnail && (
      <Box sx={{ mb: 2 }}>
        <Typography variant="h6" gutterBottom>
          Thumbnail
        </Typography>
        <Box
          component="img"
          src={`/api/v1/games/${game.id}/thumbnail`}
          alt="Game thumbnail"
          sx={{
            maxWidth: '200px',
            maxHeight: '200px',
            border: '1px solid',
            borderColor: 'divider',
            borderRadius: 1,
          }}
        />
      </Box>
    )}
    {game.has_image && (
      <Box>
        <Typography variant="h6" gutterBottom>
          Banner
        </Typography>
        <Box
          component="img"
          src={`/api/v1/games/${game.id}/image`}
          alt="Game banner"
          sx={{
            maxWidth: '100%',
            height: 'auto',
            border: '1px solid',
            borderColor: 'divider',
            borderRadius: 1,
          }}
        />
      </Box>
    )}
  </Box>
)}
```

### Phase 7: Environment Configuration

**Add API Base URL Configuration**:
```bash
# env/env.dev, env/env.prod, etc.
API_BASE_URL=http://api:8000  # For bot to generate image URLs
```

**Update API Response Schema**:
```python
# shared/schemas/game.py
class GameResponse(BaseModel):
    # ... existing fields ...
    has_thumbnail: bool = False
    has_image: bool = False

    @classmethod
    def from_orm(cls, game: GameSession) -> "GameResponse":
        data = {
            # ... existing fields ...
            "has_thumbnail": game.thumbnail_data is not None,
            "has_image": game.image_data is not None,
        }
        return cls(**data)
```

## Testing Considerations

### Unit Tests

**Model Tests**:
```python
# tests/shared/models/test_game.py
def test_game_with_images():
    game = GameSession(
        # ... required fields ...
        thumbnail_data=b"fake_png_data",
        thumbnail_mime_type="image/png",
        image_data=b"fake_jpg_data",
        image_mime_type="image/jpeg",
    )
    assert game.thumbnail_data is not None
    assert game.thumbnail_mime_type == "image/png"

def test_game_without_images():
    game = GameSession(
        # ... required fields ...
        thumbnail_data=None,
        thumbnail_mime_type=None,
        image_data=None,
        image_mime_type=None,
    )
    assert game.thumbnail_data is None
```

**Validation Tests**:
```python
# tests/services/api/routes/test_games.py
async def test_upload_valid_thumbnail():
    # Create fake image file
    file_content = b"fake PNG data"
    files = {
        "thumbnail": ("test.png", file_content, "image/png")
    }
    data = {"title": "Test Game", ...}

    response = await client.post("/api/v1/games", data=data, files=files)
    assert response.status_code == 200

async def test_upload_invalid_file_type():
    files = {
        "thumbnail": ("test.txt", b"not an image", "text/plain")
    }
    data = {"title": "Test Game", ...}

    response = await client.post("/api/v1/games", data=data, files=files)
    assert response.status_code == 400
    assert "PNG, JPEG, GIF, or WebP" in response.json()["detail"]

async def test_upload_file_too_large():
    large_file = b"x" * (6 * 1024 * 1024)  # 6MB
    files = {
        "thumbnail": ("big.png", large_file, "image/png")
    }

    response = await client.post("/api/v1/games", data=data, files=files)
    assert response.status_code == 400
    assert "5MB" in response.json()["detail"]
```

**Image Serving Tests**:
```python
# tests/services/api/routes/test_games.py
async def test_get_thumbnail():
    # Create game with thumbnail
    game = await create_test_game(
        thumbnail_data=b"fake_png",
        thumbnail_mime_type="image/png"
    )

    response = await client.get(f"/api/v1/games/{game.id}/thumbnail")
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    assert response.content == b"fake_png"

async def test_get_thumbnail_not_found():
    game = await create_test_game()  # No thumbnail

    response = await client.get(f"/api/v1/games/{game.id}/thumbnail")
    assert response.status_code == 404
```

**Discord Formatter Tests**:
```python
# tests/services/bot/formatters/test_game_message.py
def test_embed_with_images():
    content, embed, view = format_game_announcement(
        game_id="123",
        # ... other params ...
        has_thumbnail=True,
        has_image=True,
    )

    assert embed.thumbnail.url == "http://api:8000/api/v1/games/123/thumbnail"
    assert embed.image.url == "http://api:8000/api/v1/games/123/image"

def test_embed_without_images():
    content, embed, view = format_game_announcement(
        game_id="123",
        # ... other params ...
        has_thumbnail=False,
        has_image=False,
    )

    assert embed.thumbnail.url is None
    assert embed.image.url is None
```

### Integration Tests

**Full Upload Flow**:
```python
# tests/integration/test_game_images.py
async def test_create_game_with_images(authenticated_client):
    # Upload game with images
    files = {
        "thumbnail": ("thumb.png", fake_png_bytes, "image/png"),
        "image": ("banner.jpg", fake_jpg_bytes, "image/jpeg"),
    }
    data = {
        "title": "Test Game",
        # ... other required fields ...
    }

    response = await authenticated_client.post("/api/v1/games", data=data, files=files)
    assert response.status_code == 200

    game_id = response.json()["id"]

    # Verify thumbnail can be retrieved
    thumb_response = await authenticated_client.get(f"/api/v1/games/{game_id}/thumbnail")
    assert thumb_response.status_code == 200
    assert thumb_response.content == fake_png_bytes

    # Verify banner can be retrieved
    image_response = await authenticated_client.get(f"/api/v1/games/{game_id}/image")
    assert image_response.status_code == 200
    assert image_response.content == fake_jpg_bytes
```

### Manual Testing

**Upload Testing**:
- Upload game with thumbnail only → thumbnail displays in Discord
- Upload game with banner only → banner displays in Discord
- Upload game with both → both display correctly
- Upload invalid file type → error message shown
- Upload file > 5MB → error message shown

**Update Testing**:
- Update game, add thumbnail → thumbnail appears
- Update game, replace existing thumbnail → new thumbnail displays
- Update game, remove thumbnail → thumbnail removed from Discord
- Update game, keep existing images → images unchanged

**Edge Cases**:
- Upload game, then immediately fetch thumbnail → data returned correctly
- Create multiple games with same image → each stored separately
- Delete game → images deleted with game (cascade)
- Discord fetch fails → Discord shows broken image (graceful)

## Success Criteria

- [x] Database stores image binary data in BYTEA columns
- [x] API accepts multipart/form-data with file uploads
- [x] API validates file type (PNG/JPEG/GIF/WebP) and size (<5MB)
- [x] API serves images via GET endpoints with correct MIME types
- [x] Discord bot generates image URLs and passes to embeds
- [x] Discord embeds display thumbnail in upper right when uploaded
- [x] Discord embeds display banner at bottom when uploaded
- [x] Frontend forms have file input components
- [x] Frontend can upload, replace, and remove images
- [x] Frontend displays images on game detail page
- [x] Both images are optional (can be null)
- [x] Tests verify file validation and storage

## Dependencies

- PostgreSQL database with BYTEA support (already present)
- FastAPI `UploadFile` and `File` (already available)
- Discord.py library with Embed support (already present)
- SQLAlchemy LargeBinary column type (already present)
- Material-UI Button component (already present)

## Database Size Considerations

**Storage Impact**:
- Average thumbnail: ~100KB
- Average banner: ~500KB
- Total per game: ~600KB if both images uploaded
- 1000 games: ~600MB
- Acceptable for PostgreSQL BYTEA storage

**Optimization Options** (Future):
- Add database column for image size in bytes
- Monitor total storage via database metrics
- Implement cleanup for old/canceled games
- Consider compression if storage becomes issue

## Future Enhancements (Not in Scope)

- **Image Resizing**: Automatically resize large images to reduce storage
- **Client-Side Preview**: Show image preview before upload
- **Image Compression**: Compress images server-side before storage
- **CDN Migration**: Move to CDN if traffic/storage grows
- **Drag and Drop**: Add drag-and-drop file upload UI
- **Multiple Images**: Support gallery of multiple images per game
- **Image Editing**: Crop/rotate tools in browser before upload
