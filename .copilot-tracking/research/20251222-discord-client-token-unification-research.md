<!-- markdownlint-disable-file -->
# Task Research Notes: Discord Client Token Unification

## Research Executed

### Discord API Documentation Analysis
- #fetch:https://discord.com/developers/docs/resources/guild#get-guild
  - No authentication restrictions - accepts any valid auth token
  - No "bot only" designation found
- #fetch:https://discord.com/developers/docs/resources/channel#get-channel
  - No authentication restrictions - accepts any valid auth token
- #fetch:https://discord.com/developers/docs/resources/user#get-user
  - No authentication restrictions - accepts any valid auth token

### Current Implementation Analysis
- File: `shared/discord/client.py`
  - `get_bot_guilds()`: Hardcoded to use `Bot {self.bot_token}` header
  - `get_user_guilds(access_token)`: Uses `Bearer {access_token}` header
  - `fetch_guild()`, `fetch_channel()`, `fetch_user()`: All hardcoded to use `Bot {self.bot_token}`
  - Methods split by token type rather than functionality

### Token Format Research
- **Bot tokens**: BASE64_USER_ID.TIMESTAMP.HMAC_SIGNATURE (3 dot-separated parts)
- **OAuth tokens**: Single random string without dots
- **Discord API requirements**:
  - Bot tokens: `Authorization: Bot {token}`
  - OAuth tokens: `Authorization: Bearer {token}`

## Key Discoveries

### Artificial Separation
The current bot/OAuth split in `DiscordAPIClient` is an **implementation artifact**, not a Discord API requirement:

1. **Same endpoints accept both token types**: `/guilds/{id}`, `/channels/{id}`, `/users/{id}` all work with either Bot or Bearer tokens
2. **Methods duplicated by token type**: `get_bot_guilds()` vs `get_user_guilds()` perform identical operations
3. **Token type is a header format detail**: Only difference is "Bot" vs "Bearer" prefix in Authorization header

### Current Architecture Problems
```python
# Artificial split creates unnecessary complexity
async def get_bot_guilds(self):
    """Uses self.bot_token - no parameters"""
    headers = {"Authorization": f"Bot {self.bot_token}"}
    # ... implementation

async def get_user_guilds(self, access_token: str, user_id: str | None):
    """Requires OAuth token parameter"""
    headers = {"Authorization": f"Bearer {access_token}"}
    # ... nearly identical implementation

async def fetch_guild(self, guild_id: str):
    """Hardcoded to bot token - inflexible"""
    headers = {"Authorization": f"Bot {self.bot_token}"}
```

**Issues:**
- Code duplication (same logic, different headers)
- Inflexibility (methods locked to specific token types)
- Complexity (callers must know which method to use)
- E2E testing complications (bot tokens don't work with "user" methods)

## Recommended Approach: Unified Token API

### Core Design Principle
**Discord API operations should accept any token, defaulting to bot token when not specified.**

### Token Detection Implementation
```python
def _get_auth_header(self, token: str) -> str:
    """
    Detect token type and return appropriate Authorization header.

    Bot tokens have 3 dot-separated parts: BASE64.TIMESTAMP.SIGNATURE
    OAuth tokens are single strings without dots.
    """
    if token.count('.') == 2:
        return f"Bot {token}"
    else:
        return f"Bearer {token}"
```

### Unified Method Signatures
```python
async def get_guilds(
    self,
    token: str | None = None,
    user_id: str | None = None
) -> list[dict[str, Any]]:
    """
    Fetch guilds for any authenticated identity.

    Args:
        token: OAuth or bot token (defaults to self.bot_token)
        user_id: Optional user ID for cache key

    Returns:
        List of guild objects
    """
    token = token or self.bot_token
    cache_key = cache_keys.CacheKeys.user_guilds(user_id) if user_id else None

    # ... caching logic

    headers = {"Authorization": self._get_auth_header(token)}
    # ... fetch from Discord API

async def fetch_guild(
    self,
    guild_id: str,
    token: str | None = None
) -> dict[str, Any]:
    """
    Fetch guild information using any token.

    Args:
        guild_id: Discord guild ID
        token: OAuth or bot token (defaults to self.bot_token)
    """
    token = token or self.bot_token
    headers = {"Authorization": self._get_auth_header(token)}
    # ... implementation

async def fetch_channel(
    self,
    channel_id: str,
    token: str | None = None
) -> dict[str, Any]:
    """Fetch channel info using any token."""
    token = token or self.bot_token
    headers = {"Authorization": self._get_auth_header(token)}
    # ... implementation
```

### Migration Strategy

**Phase 1: Add Token Detection**
1. Implement `_get_auth_header(token)` helper
2. Add to existing tests to verify bot/OAuth tokens handled correctly

**Phase 2: Add Optional Token Parameters**
```python
# Add token parameter to existing methods (backward compatible)
async def fetch_guild(self, guild_id: str, token: str | None = None):
    token = token or self.bot_token  # Defaults to current behavior
    headers = {"Authorization": self._get_auth_header(token)}
```

**Phase 3: Consolidate Duplicate Methods**
```python
# Replace get_bot_guilds() and get_user_guilds() with unified get_guilds()
async def get_guilds(self, token: str | None = None, user_id: str | None = None):
    token = token or self.bot_token
    headers = {"Authorization": self._get_auth_header(token)}
    # Merge caching logic from both methods
```

**Phase 4: Deprecate Old Methods**
```python
@deprecated("Use get_guilds() with token parameter")
async def get_bot_guilds(self):
    return await self.get_guilds(token=self.bot_token)

@deprecated("Use get_guilds() with token and user_id parameters")
async def get_user_guilds(self, access_token: str, user_id: str | None = None):
    return await self.get_guilds(token=access_token, user_id=user_id)
```

**Phase 5: Remove Deprecated Methods**
- After callers updated, remove old methods entirely

## Benefits of Unified Approach

### 1. Simplicity
- One method per Discord API operation (not bot vs user variants)
- Consistent API surface across all operations
- Easier to understand and maintain

### 2. Flexibility
- Any caller can use bot token OR OAuth token
- E2E tests can use admin bot token naturally
- Production code works identically with either token type

### 3. Reduced Duplication
- Single implementation per operation
- Token type handling centralized in `_get_auth_header()`
- Caching logic unified

### 4. Future-Proof
- If Discord adds new token types, only `_get_auth_header()` needs updating
- API remains stable regardless of internal token format changes

### 5. Better Testing
- E2E tests use same methods as production
- Unit tests can easily swap token types
- Integration tests benefit from unified interface

## Impact on E2E Test Strategy

**Before Unification:**
- E2E tests need special authentication handling
- Admin bot token requires different code paths
- Must work around artificial bot/user split

**After Unification:**
- E2E tests use same API as production
- Admin bot token works with all methods naturally
- No special cases needed for testing

**E2E Implementation Simplifies to:**
```python
# Extract bot Discord ID from token
admin_bot_id = extract_bot_discord_id(os.environ["DISCORD_ADMIN_TOKEN"])

# Create session with admin bot token (unified API handles it)
session_token = await tokens.store_user_tokens(
    user_id=admin_bot_id,
    access_token=os.environ["DISCORD_ADMIN_TOKEN"]
)

# Sync guilds using admin bot token (no special handling needed)
response = await authenticated_client.post("/api/v1/guilds/sync")
```

## Implementation Checklist

- [ ] Implement `_get_auth_header(token)` with token detection
- [ ] Add unit tests for bot token detection (3 dots)
- [ ] Add unit tests for OAuth token detection (no dots)
- [ ] Add optional `token` parameter to all fetch methods
- [ ] Verify backward compatibility (defaults to `self.bot_token`)
- [ ] Create unified `get_guilds(token, user_id)` method
- [ ] Merge caching logic from `get_bot_guilds()` and `get_user_guilds()`
- [ ] Update callers to use unified `get_guilds()`
- [ ] Deprecate `get_bot_guilds()` and `get_user_guilds()`
- [ ] Update integration tests to verify token flexibility
- [ ] Remove deprecated methods after migration complete
- [ ] Update documentation to reflect unified API

## Success Criteria

1. All existing tests pass with refactored client
2. Production behavior unchanged (backward compatible)
3. New E2E tests can use admin bot token without special handling
4. Code complexity reduced (fewer methods, less duplication)
5. API surface simplified and more consistent

## Next Steps

1. **Implement token unification refactor** (this research document)
2. **Merge to main** after tests pass
3. **Resume E2E test work** using simplified unified API
4. **Validate E2E approach** still correct with refactored client
