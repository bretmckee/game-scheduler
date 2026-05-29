<!-- markdownlint-disable-file -->

# Task Research Notes: Web UI Game Creation Fixes

## Research Executed

### File Analysis

- `services/api/routes/public.py`
  - `GET /{image_id}` and `HEAD /{image_id}`: `image_id` typed as `UUID` via FastAPI `Path` — any URL with a `.gif` or `.jpg` suffix is rejected before the handler runs
  - Both endpoints share identical UUID-parse logic; need same change applied to both
- `services/bot/formatters/game_message.py`
  - `format_game_announcement()` builds thumbnail/banner URLs as `f"{config.backend_url}/api/v1/public/images/{thumbnail_id}"` — no extension
  - Accepts `thumbnail_id: str | None` and `banner_image_id: str | None` but not MIME types
- `services/bot/events/handlers.py`
  - `_create_game_announcement()` passes `game.thumbnail_id` and `game.banner_image_id` as strings
  - `game.thumbnail` and `game.banner_image` are `lazy="selectin"` relationships — MIME types already loaded, no extra query needed
- `shared/models/game.py`
  - `thumbnail: Mapped["GameImage | None"] = relationship("GameImage", foreign_keys=[thumbnail_id], lazy="selectin")`
  - `banner_image: Mapped["GameImage | None"] = relationship("GameImage", foreign_keys=[banner_image_id], lazy="selectin")`
  - Both relationships are eagerly loaded via `selectin` — `game.thumbnail.mime_type` available without additional DB query
- `services/api/services/channel_resolver.py`
  - `resolve_channel_mentions()` processes `#name` patterns: exact match → `<#id>`; ambiguous → error; not found → error with suggestions
  - Does NOT currently have special handling for `#<integer>` patterns
  - Called only for `resolved_fields["where"]` in `games.py`
- `services/api/services/games.py`
  - `channel_resolver.resolve_channel_mentions()` applied only to `resolved_fields["where"]` (lines ~640–657)
  - `description` and `signup_instructions` stored as-is, no resolution
- `shared/discord/client.py`
  - Has `get_guild_channels(guild_id)` — reads from Redis gateway cache; 503 on cache miss
  - Pattern for cache-only reads: `_read_cache_only(cache_key, operation)`
  - No emoji methods exist
- `shared/cache/keys.py`
  - Has `discord_guild_channels(guild_id)` cache key
  - No emoji cache key

### Code Search Results

- `thumbnail_id|banner_image_id` in `services/bot/events/handlers.py`
  - Lines 1340–1341: `thumbnail_id=str(game.thumbnail_id) if game.thumbnail_id else None` and same for `banner_image_id`
  - `game.thumbnail.mime_type` would be `game.thumbnail.mime_type if game.thumbnail else None`
- `resolve_channel_mentions` callers in `services/api/services/games.py`
  - Called only once: line ~644, for `resolved_fields["where"]`
  - `description` passed directly to `_build_game_session` without resolution (line 529)
  - `signup_instructions` from `resolved_fields` but `resolved_fields["signup_instructions"]` is set from template/input without resolution (line 530)
- `on_guild_emojis|emoji` in bot service
  - No matches — gateway emoji events not handled; no emoji cache

## Key Discoveries

### Issue 1: GIF Animation (URL File Extension)

Discord's embed renderer requires the URL to end in a recognized image extension (`.gif`, `.png`, `.jpg`, `.webp`) to decide how to render the image. Without the extension, Discord treats it as a static image even if the server sends `Content-Type: image/gif`.

**Root cause**: `public.py` declares `image_id: UUID` so FastAPI rejects `/{uuid}.gif`. `game_message.py` builds URLs without extensions.

**MIME-to-extension map**:

```python
_MIME_TO_EXT: dict[str, str] = {
    "image/gif": ".gif",
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/webp": ".webp",
}
```

### Issue 2: @mentions in description/signup_instructions

`ParticipantResolver` handles `@username` → `<@discord_id>` resolution. Currently only used for `initial_participants` list, not free-text fields. Decision: **block on invalid `@user`** (same behaviour as participant list).

### Issue 3: #channel in description/signup_instructions

`ChannelResolver.resolve_channel_mentions()` handles `#name` → `<#id>`. Currently only applied to `where` field.

**Decision for integer tokens**: `#1` could be a valid channel name (Discord allows numeric channel names). The correct behaviour is:

1. Attempt lookup for any `#<token>` pattern
2. If found → resolve normally
3. If NOT found AND `<token>` is a pure integer → pass through as plain text (don't block)
4. If NOT found AND `<token>` is NOT a pure integer → block with validation error

This requires a small addition to the `not_found` branch in `resolve_channel_mentions`: check `channel_name.isdigit()` and skip adding the error in that case.

### Issue 4: Custom Emoji Resolution

Gateway provides emoji data via `on_guild_emojis_update` event (fired when emojis are added/removed/modified) and on `on_guild_available` (initial population). Discord gateway emoji object fields:

```json
{ "id": "123456", "name": "custom_emoji", "animated": true }
```

Resolved format: `<:name:id>` for static, `<a:name:id>` for animated.

Pattern to scan for: `:word:` — but only match when the word exists in the guild emoji list. Unknown `:word:` patterns that don't match any guild emoji should be passed through as plain text (not blocked).

**Cache key pattern** (following existing convention in `keys.py`):

```python
@staticmethod
def discord_guild_emojis(guild_id: str) -> str:
    return f"discord:guild_emojis:{guild_id}"
```

**Bot gateway event** (following `on_guild_channel_create` pattern in bot):

```python
@commands.Cog.listener()
async def on_guild_emojis_update(self, guild, before, after):
    await redis.set(
        CacheKeys.discord_guild_emojis(str(guild.id)),
        json.dumps([{"id": str(e.id), "name": e.name, "animated": e.animated} for e in after]),
        ttl=CacheTTL.GUILD_EMOJIS,
    )
```

**New `DiscordAPIClient` method** (cache-only, same pattern as `get_guild_channels`):

```python
async def get_guild_emojis(self, guild_id: str) -> list[dict[str, Any]]:
    return cast(
        "list[dict[str, Any]]",
        await self._read_cache_only(
            cache_keys.CacheKeys.discord_guild_emojis(guild_id),
            CacheOperation.FETCH_GUILD_EMOJIS,
        ),
    )
```

### Issue 5: username#discriminator in Participants (No-Op)

Discord deprecated username discriminators (e.g. `User#0`, `User#1234`). Decision: **do not implement support**. Document the behaviour in user-facing docs.

## Recommended Approach

### Fix 1 — GIF extension in image URLs

**Files changed**: 3

**`services/api/routes/public.py`** — Change path parameter from `UUID` to `str` on both GET and HEAD routes, strip extension before parsing:

```python
@router.get("/{image_id_with_ext}")
async def get_image(
    request: Request,
    image_id_with_ext: Annotated[str, Path(description="UUID of the image, optionally with extension")],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
    image_id = UUID(image_id_with_ext.split(".")[0])
    ...
```

**`services/bot/formatters/game_message.py`** — Add `thumbnail_mime_type: str | None = None` and `banner_image_mime_type: str | None = None` parameters to `format_game_announcement()`. Add `_MIME_TO_EXT` map. Build URLs with extension:

```python
_MIME_TO_EXT: dict[str, str] = {
    "image/gif": ".gif",
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/webp": ".webp",
}

if thumbnail_id:
    ext = _MIME_TO_EXT.get(thumbnail_mime_type or "", "")
    thumbnail_url = f"{config.backend_url}/api/v1/public/images/{thumbnail_id}{ext}"
```

**`services/bot/events/handlers.py`** — Pass MIME types from already-loaded relationships:

```python
thumbnail_id=str(game.thumbnail_id) if game.thumbnail_id else None,
thumbnail_mime_type=game.thumbnail.mime_type if game.thumbnail else None,
banner_image_id=str(game.banner_image_id) if game.banner_image_id else None,
banner_image_mime_type=game.banner_image.mime_type if game.banner_image else None,
```

### Fix 2 — @mentions in description/signup_instructions

**Files changed**: `services/api/services/games.py`

Apply `participant_resolver` to `description` and `signup_instructions` text using a new helper similar to `resolve_initial_participants` but for inline `@` mentions within free-text — scan for `@word` tokens, resolve each, replace with `<@discord_id>` or block on failure.

The `ParticipantResolver` already contains the lookup logic. A new method `resolve_mentions_in_text(text, guild_id)` → `(resolved_text, errors)` would scan for `@word` patterns, resolve each, and return the modified text plus any errors.

Apply in `games.py` after current `where` resolution and before `_build_game_session`.

### Fix 3 — #channel in description/signup_instructions (with integer passthrough)

**Files changed**: `services/api/services/channel_resolver.py`, `services/api/services/games.py`

In `channel_resolver.py`, modify the `not_found` branch of the `hash_matches` loop:

```python
else:
    if channel_name.isdigit():
        # Pure integer — may be a raw channel ID; pass through without error
        pass
    else:
        similar_channels = [...]
        errors.append({...})
```

In `games.py`, call `channel_resolver.resolve_channel_mentions()` on `description` and `signup_instructions` in addition to `where`, accumulating errors from all three fields.

### Fix 4 — Custom Emoji Resolution

**Files changed**: 4 (new file + 3 modifications)

1. **`shared/cache/keys.py`** — Add `discord_guild_emojis(guild_id)` cache key
2. **`shared/cache/operations.py`** (or equivalent) — Add `FETCH_GUILD_EMOJIS` operation
3. **`shared/discord/client.py`** — Add `get_guild_emojis(guild_id)` using `_read_cache_only`
4. **Bot `guild_projection.py` or event cog** — Add `on_guild_emojis_update` handler to populate cache; also populate on `on_guild_available`
5. **`services/api/services/emoji_resolver.py`** (new file) — `EmojiResolver` class with `resolve_emoji_mentions(text, guild_id) → (resolved_text, errors)`:
   - Scan for `:word:` patterns
   - Look up in emoji list from cache
   - Replace with `<:name:id>` (static) or `<a:name:id>` (animated)
   - Unknown `:word:` patterns → pass through unchanged (not an error)
6. **`services/api/services/games.py`** — Add `emoji_resolver` dependency, apply to `description` and `signup_instructions`

### Fix 5 — Discriminator format (documentation only)

Update `docs/PLAYER-GUIDE.md` or equivalent to note that `username#0` / `username#1234` format is not supported because Discord deprecated discriminators. Users should use `@username` (prefix search) or `<@discord_id>` format.

## Implementation Guidance

- **Objectives**: Fix 4 UX issues in game creation; document 1 deprecated pattern
- **Key Tasks**:
  - Issue 1 (GIF): 3 files, ~30 lines — lowest risk, no new infrastructure
  - Issue 3 (#channel integer passthrough): 2 files, ~10 lines — very small, contained to `channel_resolver.py`
  - Issue 2 (@mentions in text): new method on `ParticipantResolver` + `games.py` wiring — ~60 lines
  - Issue 4 (emojis): most work — new cache key, new bot event handler, new client method, new resolver service, `games.py` wiring — ~150 lines
  - Issue 5 (docs): 1 markdown file update
- **Dependencies**:
  - Issues 2 and 3 depend on `ChannelResolver` and `ParticipantResolver` already existing
  - Issue 4 depends on bot gateway cache infrastructure already existing (channels/roles as template)
  - Issue 1 has zero dependencies on other fixes
- **TDD**: All Python changes (Issues 1–4) should follow TDD (RED → GREEN → REFACTOR)
- **Success Criteria**:
  - GIF thumbnails animate in Discord announcements
  - `@username` in description/signup_instructions resolves to Discord mention
  - `#channel-name` in description/signup_instructions resolves to Discord channel link
  - `#123` in description/signup_instructions passes through without error
  - Custom emojis via `:name:` syntax in description/signup_instructions render in Discord
  - `username#0` in participant list documented as unsupported
