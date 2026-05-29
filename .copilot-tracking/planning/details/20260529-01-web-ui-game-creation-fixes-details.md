<!-- markdownlint-disable-file -->

# Task Details: Web UI Game Creation Fixes

## Research Reference

**Source Research**: #file:../research/20260529-01-web-ui-game-creation-fixes-research.md

---

## Phase 1: GIF Animation Fix

### Task 1.1: Change `image_id` path parameter from `UUID` to `str` in `public.py`

Both the `GET /{image_id}` and `HEAD /{image_id}` routes in `services/api/routes/public.py`
reject requests whose path contains a file extension (e.g. `/uuid.gif`) because FastAPI
validates the path segment as a `UUID` before the handler runs. Change the parameter type
to `str`, strip any trailing extension with `.split(".")[0]`, then parse the UUID explicitly.
Apply the same change to both the GET and HEAD handlers.

**TDD**: Write a regression test (`xfail`) that sends `GET /api/v1/public/images/{uuid}.gif`
and asserts a 200 response; verify it xfails; implement the fix; remove `xfail`.

- **Files**:
  - `services/api/routes/public.py` — change `image_id: UUID` to `image_id_with_ext: str`, add `UUID(image_id_with_ext.split(".")[0])` parse in both GET and HEAD handlers
  - `tests/unit/api/routes/test_public.py` (or integration equivalent) — regression tests for extension-suffixed URLs on GET and HEAD
- **Success**:
  - `GET /api/v1/public/images/{uuid}.gif` returns 200 with image content
  - `HEAD /api/v1/public/images/{uuid}.gif` returns 200
  - `GET /api/v1/public/images/{uuid}` (no extension) still returns 200
  - Invalid UUIDs (non-hex string before first `.`) still return 422/404
- **Research References**:
  - #file:../research/20260529-01-web-ui-game-creation-fixes-research.md (Lines 4-9) — route parameter analysis
  - #file:../research/20260529-01-web-ui-game-creation-fixes-research.md (Lines 109-119) — recommended code change
- **Dependencies**: None

---

### Task 1.2: Add MIME-to-extension map and update `format_game_announcement()` in `game_message.py`

`services/bot/formatters/game_message.py` builds thumbnail/banner URLs without a file
extension. Discord requires the URL to end in a recognised extension to animate GIFs.
Add a module-level `_MIME_TO_EXT` dict and two new optional parameters
(`thumbnail_mime_type: str | None`, `banner_image_mime_type: str | None`) to
`format_game_announcement()`. Append the extension to the URL when a known MIME type is
provided.

**TDD**: Write tests asserting that a `image/gif` MIME type produces a URL ending in
`.gif`; mark `xfail`; implement; remove `xfail`.

- **Files**:
  - `services/bot/formatters/game_message.py` — add `_MIME_TO_EXT`, add parameters, update URL construction
  - `tests/unit/bot/formatters/test_game_message.py` — tests for extension-suffixed URLs per MIME type and for `None` MIME type (no extension)
- **Success**:
  - URL ends in `.gif` when MIME type is `image/gif`
  - URL ends in `.png`, `.jpg`, `.webp` for corresponding MIME types
  - URL has no extension when `mime_type` is `None` or unknown
  - All existing `format_game_announcement()` callers still work (parameters are optional)
- **Research References**:
  - #file:../research/20260529-01-web-ui-game-creation-fixes-research.md (Lines 10-13) — formatter analysis
  - #file:../research/20260529-01-web-ui-game-creation-fixes-research.md (Lines 120-138) — MIME map and URL construction pattern
- **Dependencies**: None (can be done before or after Task 1.1)

---

### Task 1.3: Pass MIME types from loaded relationships in `handlers.py`

`services/bot/events/handlers.py` calls `format_game_announcement()` passing only
`thumbnail_id` and `banner_image_id`. The `game.thumbnail` and `game.banner_image`
relationships are already eagerly loaded via `selectin` — `mime_type` is available with
no extra query. Pass `thumbnail_mime_type` and `banner_image_mime_type` from those
relationships.

**TDD**: Update existing handler unit tests (or add new ones) to assert that the MIME
type arguments are forwarded correctly.

- **Files**:
  - `services/bot/events/handlers.py` — update `_create_game_announcement()` call to pass `thumbnail_mime_type` and `banner_image_mime_type`
  - `tests/unit/bot/events/test_handlers.py` — verify MIME type arguments forwarded
- **Success**:
  - Handler passes `game.thumbnail.mime_type` (or `None`) as `thumbnail_mime_type`
  - Handler passes `game.banner_image.mime_type` (or `None`) as `banner_image_mime_type`
  - Full test suite passes
- **Research References**:
  - #file:../research/20260529-01-web-ui-game-creation-fixes-research.md (Lines 14-21) — handler and relationship analysis
  - #file:../research/20260529-01-web-ui-game-creation-fixes-research.md (Lines 47-53) — code search results showing exact lines
  - #file:../research/20260529-01-web-ui-game-creation-fixes-research.md (Lines 139-149) — recommended handler change
- **Dependencies**: Task 1.2 must be complete (new parameters must exist)

---

## Phase 2: #channel Integer Passthrough Fix

### Task 2.1: Allow pure-integer tokens in `resolve_channel_mentions()`

`services/api/services/channel_resolver.py` currently blocks any `#<token>` that does not
match a guild channel name with a validation error. Discord allows numeric channel names,
but `#1` in free-text may also be a list marker with no channel intent. The agreed
behaviour: if the token is a pure integer AND no channel with that name exists, pass it
through unchanged (no error). Non-integer unknown tokens still produce an error.

Add the `channel_name.isdigit()` check in the `not_found` branch of the `hash_matches`
loop.

**TDD**: Write a test asserting that `resolve_channel_mentions("see step #1", guild_id)`
returns the text unchanged with no errors; mark `xfail`; implement; remove `xfail`.

- **Files**:
  - `services/api/services/channel_resolver.py` — add `if channel_name.isdigit(): pass` (or `continue`) in the not-found error branch
  - `tests/unit/api/services/test_channel_resolver.py` — test for integer passthrough; confirm non-integer still errors
- **Success**:
  - `#1`, `#42`, `#100` in text pass through unchanged when no channel with that name exists
  - `#unknown-channel` still produces a validation error
  - `#real-channel-name` still resolves to `<#id>`
- **Research References**:
  - #file:../research/20260529-01-web-ui-game-creation-fixes-research.md (Lines 22-27) — channel_resolver analysis
  - #file:../research/20260529-01-web-ui-game-creation-fixes-research.md (Lines 72-85) — integer passthrough decision and code change
- **Dependencies**: None

---

### Task 2.2: Apply `resolve_channel_mentions()` to `description` and `signup_instructions`

`services/api/services/games.py` currently calls `channel_resolver.resolve_channel_mentions()`
only for the `where` field. Apply it to `description` and `signup_instructions` as well,
accumulating errors from all three fields and returning a combined validation error list.

**TDD**: Write a test asserting that a `#channel-name` in the `description` field of a
game creation request is resolved to `<#id>`; mark `xfail`; implement; remove `xfail`.

- **Files**:
  - `services/api/services/games.py` — call `resolve_channel_mentions()` on `description` and `signup_instructions`, accumulate errors
  - `tests/unit/api/services/test_games.py` (or integration) — test channel resolution in description and signup_instructions
- **Success**:
  - `#channel-name` in `description` resolved to `<#channel_id>`
  - `#channel-name` in `signup_instructions` resolved to `<#channel_id>`
  - Invalid channel names in either field produce validation errors
  - `#42` in either field passes through unchanged
- **Research References**:
  - #file:../research/20260529-01-web-ui-game-creation-fixes-research.md (Lines 28-33) — games.py analysis showing where resolution is applied
  - #file:../research/20260529-01-web-ui-game-creation-fixes-research.md (Lines 86-97) — recommended games.py wiring
- **Dependencies**: Task 2.1 must be complete

---

## Phase 3: @mention Resolution in Free-Text Fields

### Task 3.1: Add `resolve_mentions_in_text()` to `ParticipantResolver`

`services/api/services/participant_resolver.py` (or equivalent) resolves `@username`
tokens to `<@discord_id>` for the `initial_participants` list. Add a new method
`resolve_mentions_in_text(text: str, guild_id: str) -> tuple[str, list[dict]]` that:

1. Scans `text` for `@word` tokens (regex `@\w+`)
2. For each token, looks up the username using existing resolver logic
3. Replaces matched tokens with `<@discord_id>` in the text
4. Returns `(resolved_text, errors)` — errors are in the same format as the participant list

Block on unresolvable `@username` (same behaviour as the participant list).

**TDD**: Write tests for match/no-match/error cases; mark `xfail`; implement; remove
`xfail`.

- **Files**:
  - `services/api/services/participant_resolver.py` — add `resolve_mentions_in_text()` method
  - `tests/unit/api/services/test_participant_resolver.py` — tests for text scanning, resolution, and error cases
- **Success**:
  - `@validuser` in text replaced with `<@discord_id>`
  - `@unknownuser` produces a validation error
  - Text with no `@` tokens returned unchanged
  - Multiple `@` tokens in one text all resolved
- **Research References**:
  - #file:../research/20260529-01-web-ui-game-creation-fixes-research.md (Lines 55-70) — @mention resolution design
- **Dependencies**: None

---

### Task 3.2: Apply `resolve_mentions_in_text()` to `description` and `signup_instructions`

Wire the new `resolve_mentions_in_text()` into `services/api/services/games.py`, applying
it to `description` and `signup_instructions` after channel resolution. Accumulate errors
alongside channel resolution errors.

**TDD**: Write a test asserting that `@username` in `description` resolves to the Discord
mention; mark `xfail`; implement; remove `xfail`.

- **Files**:
  - `services/api/services/games.py` — inject `participant_resolver`, call `resolve_mentions_in_text()` on `description` and `signup_instructions`
  - `tests/unit/api/services/test_games.py` — test @mention resolution in description and signup_instructions
- **Success**:
  - `@validuser` in `description` replaced with `<@discord_id>`
  - `@validuser` in `signup_instructions` replaced with `<@discord_id>`
  - Unknown `@username` in either field produces validation error
  - Channel and @mention errors are both reported together
- **Research References**:
  - #file:../research/20260529-01-web-ui-game-creation-fixes-research.md (Lines 55-70) — recommended games.py wiring
- **Dependencies**: Task 3.1 must be complete

---

## Phase 4: Custom Emoji Resolution

### Task 4.1: Add `discord_guild_emojis` cache key and `FETCH_GUILD_EMOJIS` operation

Add a `discord_guild_emojis(guild_id: str) -> str` static method to `CacheKeys` in
`shared/cache/keys.py`, following the same pattern as `discord_guild_channels`. Add
`FETCH_GUILD_EMOJIS` to the cache operations enum (or equivalent constant) in
`shared/cache/operations.py` (or wherever `CacheOperation` is defined).

**TDD**: Add unit tests for the new cache key returning the expected string; mark `xfail`;
implement; remove `xfail`.

- **Files**:
  - `shared/cache/keys.py` — add `discord_guild_emojis` static method
  - `shared/cache/operations.py` (or equivalent) — add `FETCH_GUILD_EMOJIS`
  - `tests/unit/shared/cache/test_keys.py` — test new cache key format
- **Success**:
  - `CacheKeys.discord_guild_emojis("123")` returns `"discord:guild_emojis:123"`
  - `FETCH_GUILD_EMOJIS` constant available in operations module
- **Research References**:
  - #file:../research/20260529-01-web-ui-game-creation-fixes-research.md (Lines 34-40) — cache key analysis
  - #file:../research/20260529-01-web-ui-game-creation-fixes-research.md (Lines 98-103) — cache key pattern
- **Dependencies**: None

---

### Task 4.2: Add `get_guild_emojis()` to `DiscordAPIClient`

Add `get_guild_emojis(self, guild_id: str) -> list[dict[str, Any]]` to
`shared/discord/client.py`, using `_read_cache_only` exactly as `get_guild_channels` does.
This is a cache-only read; it returns 503 if the cache is cold.

**TDD**: Write a unit test asserting that the method calls `_read_cache_only` with the
correct cache key; mark `xfail`; implement; remove `xfail`.

- **Files**:
  - `shared/discord/client.py` — add `get_guild_emojis()` method
  - `tests/unit/shared/discord/test_client.py` — test cache-only emoji fetch
- **Success**:
  - `get_guild_emojis()` calls `_read_cache_only` with `CacheKeys.discord_guild_emojis(guild_id)`
  - Returns `list[dict]` cast from cache
- **Research References**:
  - #file:../research/20260529-01-web-ui-game-creation-fixes-research.md (Lines 34-40) — existing `get_guild_channels` pattern
  - #file:../research/20260529-01-web-ui-game-creation-fixes-research.md (Lines 104-113) — recommended client method code
- **Dependencies**: Task 4.1 must be complete (cache key must exist)

---

### Task 4.3: Add `on_guild_emojis_update` bot event handler and populate on `on_guild_available`

In the bot's guild projection cog (following the `on_guild_channel_create` pattern in
`services/bot/guild_projection.py` or equivalent), add:

1. `on_guild_emojis_update(guild, before, after)` — serialises `after` emoji list to JSON
   and writes to Redis under `CacheKeys.discord_guild_emojis(guild.id)` with `CacheTTL.GUILD_EMOJIS`
   (add this TTL constant if it does not exist, following existing TTL conventions)
2. Update `on_guild_available` (or `on_ready` population logic) to also write the emoji
   cache for each guild

**TDD**: Write unit tests for the handler asserting the cache is written with the correct
key and serialised payload; mark `xfail`; implement; remove `xfail`.

- **Files**:
  - `services/bot/guild_projection.py` (or equivalent event cog) — add handler and update `on_guild_available`
  - `shared/cache/ttl.py` (or equivalent) — add `GUILD_EMOJIS` TTL constant if missing
  - `tests/unit/bot/test_guild_projection.py` — test emoji cache population
- **Success**:
  - `on_guild_emojis_update` writes correct JSON to Redis under `discord:guild_emojis:{guild_id}`
  - `on_guild_available` populates the emoji cache as well as channels/roles
  - TTL constant `GUILD_EMOJIS` exists and is a reasonable duration (e.g. 24 hours)
- **Research References**:
  - #file:../research/20260529-01-web-ui-game-creation-fixes-research.md (Lines 114-127) — bot event handler pattern
- **Dependencies**: Task 4.1 must be complete

---

### Task 4.4: Create `services/api/services/emoji_resolver.py`

Create a new `EmojiResolver` class with method
`resolve_emoji_mentions(text: str, guild_id: str) -> tuple[str, list[dict]]` that:

1. Scans `text` for `:word:` patterns (regex `:\w+:`)
2. Looks up each `word` in the guild emoji list via `DiscordAPIClient.get_guild_emojis()`
3. Replaces matched patterns with `<:name:id>` (static) or `<a:name:id>` (animated)
4. Unknown `:word:` patterns that match no guild emoji are passed through unchanged (not
   an error)
5. Returns `(resolved_text, errors)` — errors list will always be empty (unknown emojis
   are not errors) but the signature is kept consistent for uniform wiring in `games.py`

**TDD**: Write tests for match/no-match/animated cases; mark `xfail`; implement; remove
`xfail`.

- **Files**:
  - `services/api/services/emoji_resolver.py` — new file with `EmojiResolver` class
  - `tests/unit/api/services/test_emoji_resolver.py` — new test file
- **Success**:
  - `:custom_emoji:` replaced with `<:custom_emoji:123456>`
  - `:animated_emoji:` replaced with `<a:animated_emoji:789>`
  - `:unknown:` passed through unchanged
  - Text with no `:word:` patterns returned unchanged
- **Research References**:
  - #file:../research/20260529-01-web-ui-game-creation-fixes-research.md (Lines 98-113) — emoji resolver design and cache client pattern
- **Dependencies**: Task 4.2 must be complete

---

### Task 4.5: Wire `EmojiResolver` into `games.py`

Inject `EmojiResolver` as a dependency in `services/api/services/games.py`. Apply
`resolve_emoji_mentions()` to `description` and `signup_instructions`, accumulating any
errors alongside channel and @mention errors.

**TDD**: Write a test asserting `:custom_emoji:` in `description` is replaced with the
Discord emoji format; mark `xfail`; implement; remove `xfail`.

- **Files**:
  - `services/api/services/games.py` — inject `emoji_resolver`, call `resolve_emoji_mentions()` on `description` and `signup_instructions`
  - `tests/unit/api/services/test_games.py` — test emoji resolution wiring
- **Success**:
  - `:emoji_name:` in `description` replaced with Discord emoji format
  - `:emoji_name:` in `signup_instructions` replaced with Discord emoji format
  - All three resolver types (channel, @mention, emoji) applied and errors accumulated
- **Research References**:
  - #file:../research/20260529-01-web-ui-game-creation-fixes-research.md (Lines 98-113) — emoji resolution design
- **Dependencies**: Tasks 4.3 and 4.4 must be complete

---

## Phase 5: Documentation Update

### Task 5.1: Document discriminator format as unsupported in player guide

Update `docs/PLAYER-GUIDE.md` to note that `username#0` / `username#1234` (the old
Discord discriminator format) is not supported as a participant specifier because Discord
deprecated discriminators. Instruct users to use `@username` (prefix search) or
`<@discord_id>` (direct mention) instead.

- **Files**:
  - `docs/PLAYER-GUIDE.md` — add note about unsupported discriminator format near the participant documentation section
- **Success**:
  - Player guide clearly states `username#discriminator` is not supported
  - Alternatives (`@username`, `<@id>`) are documented
- **Research References**:
  - #file:../research/20260529-01-web-ui-game-creation-fixes-research.md (Lines 92-96) — discriminator no-op decision
- **Dependencies**: None

---

## Dependencies

- Python 3.11+ with `re`, `uuid`, `typing` standard library modules
- Existing `ChannelResolver`, `ParticipantResolver`, and `DiscordAPIClient` classes
- Redis cache infrastructure already in place
- discord.py bot gateway already handling `on_guild_available`

## Success Criteria

- GIF thumbnails animate in Discord announcements
- `@username` in `description`/`signup_instructions` resolves to `<@discord_id>`
- `#channel-name` in `description`/`signup_instructions` resolves to `<#channel_id>`
- `#123` (integer) in `description`/`signup_instructions` passes through without error
- `:emoji_name:` in `description`/`signup_instructions` renders as Discord custom emoji
- `username#discriminator` documented as unsupported in player guide
- All new code covered by unit tests following TDD (RED → GREEN → REFACTOR)
- Full test suite passes with no regressions
