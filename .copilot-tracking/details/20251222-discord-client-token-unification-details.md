<!-- markdownlint-disable-file -->

# Task Details: Discord Client Token Unification

## Research Reference

**Source Research**: #file:../research/20251222-discord-client-token-unification-research.md

## Phase 1: Token Detection Infrastructure

### Task 1.1: Implement `_get_auth_header()` method

Add token type detection to DiscordAPIClient based on Discord token format:
- Bot tokens: 3 dot-separated parts (BASE64.TIMESTAMP.SIGNATURE)
- OAuth tokens: Single string without dots

- **Files**:
  - [shared/discord/client.py](shared/discord/client.py) - Add `_get_auth_header()` helper method
- **Success**:
  - Method correctly identifies bot tokens (3 dots)
  - Method correctly identifies OAuth tokens (no dots)
  - Returns proper "Bot {token}" or "Bearer {token}" header
- **Research References**:
  - #file:../research/20251222-discord-client-token-unification-research.md (Lines 44-60) - Token detection implementation
- **Dependencies**:
  - None

### Task 1.2: Add token detection unit tests

Create comprehensive unit tests for token type detection:

- **Files**:
  - [tests/shared/test_discord_client.py](tests/shared/test_discord_client.py) - Add token detection tests
- **Success**:
  - Test validates bot token detection (3 dots → "Bot" prefix)
  - Test validates OAuth token detection (no dots → "Bearer" prefix)
  - Tests pass consistently
- **Research References**:
  - #file:../research/20251222-discord-client-token-unification-research.md (Lines 44-60) - Token format specifications
- **Dependencies**:
  - Task 1.1 completion

## Phase 2: Add Optional Token Parameters

### Task 2.1: Add token parameter to `fetch_guild()`

Make `fetch_guild()` accept any token type while maintaining backward compatibility:

- **Files**:
  - [shared/discord/client.py](shared/discord/client.py) - Update `fetch_guild()` signature and implementation
- **Success**:
  - Method accepts optional `token` parameter
  - Defaults to `self.bot_token` when not specified
  - Uses `_get_auth_header()` for token format detection
  - Existing callers work without changes
- **Research References**:
  - #file:../research/20251222-discord-client-token-unification-research.md (Lines 82-95) - Unified method signature pattern
- **Dependencies**:
  - Phase 1 completion

### Task 2.2: Add token parameter to `fetch_channel()`

Make `fetch_channel()` accept any token type:

- **Files**:
  - [shared/discord/client.py](shared/discord/client.py) - Update `fetch_channel()` signature and implementation
- **Success**:
  - Method accepts optional `token` parameter
  - Defaults to `self.bot_token` when not specified
  - Uses `_get_auth_header()` for token format detection
- **Research References**:
  - #file:../research/20251222-discord-client-token-unification-research.md (Lines 97-106) - Unified fetch_channel pattern
- **Dependencies**:
  - Task 2.1 completion

### Task 2.3: Add token parameter to `fetch_user()`

Make `fetch_user()` accept any token type:

- **Files**:
  - [shared/discord/client.py](shared/discord/client.py) - Update `fetch_user()` signature
- **Success**:
  - Method accepts optional `token` parameter
  - Defaults to `self.bot_token` when not specified
  - Uses `_get_auth_header()` for token format detection
- **Research References**:
  - #file:../research/20251222-discord-client-token-unification-research.md (Lines 62-80) - Unified method signatures
- **Dependencies**:
  - Task 2.2 completion

## Phase 3: Consolidate Guild Methods

### Task 3.1: Create unified `get_guilds()` method

Replace `get_bot_guilds()` and `get_user_guilds()` with single unified method:

- **Files**:
  - [shared/discord/client.py](shared/discord/client.py) - Add `get_guilds()` method merging both implementations
- **Success**:
  - Method accepts optional `token` and `user_id` parameters
  - Defaults to `self.bot_token` when token not specified
  - Merges caching logic from both old methods
  - Uses `_get_auth_header()` for token detection
  - Returns identical data structure as old methods
- **Research References**:
  - #file:../research/20251222-discord-client-token-unification-research.md (Lines 62-80) - Unified get_guilds implementation
  - #file:../research/20251222-discord-client-token-unification-research.md (Lines 108-120) - Migration strategy Phase 3
- **Dependencies**:
  - Phase 2 completion

### Task 3.2: Update callers to use `get_guilds()`

Update all code that calls `get_bot_guilds()` or `get_user_guilds()`:

- **Files**:
  - Search workspace for all usages of `get_bot_guilds()` and `get_user_guilds()`
  - Update each caller to use `get_guilds()` with appropriate parameters
- **Success**:
  - All callers migrated to `get_guilds()`
  - Bot token callers use `get_guilds()` (no token parameter)
  - OAuth callers use `get_guilds(token=access_token, user_id=user_id)`
  - All tests pass after migration
- **Research References**:
  - #file:../research/20251222-discord-client-token-unification-research.md (Lines 122-132) - Migration strategy Phase 4
- **Dependencies**:
  - Task 3.1 completion

### Task 3.3: Deprecate `get_bot_guilds()` and `get_user_guilds()`

Mark old methods as deprecated while maintaining backward compatibility:

- **Files**:
  - [shared/discord/client.py](shared/discord/client.py) - Add deprecation warnings to old methods
- **Success**:
  - Both methods marked with deprecation decorator/warning
  - Methods delegate to `get_guilds()` with appropriate parameters
  - Existing code continues to work but sees deprecation warnings
- **Research References**:
  - #file:../research/20251222-discord-client-token-unification-research.md (Lines 122-132) - Deprecation strategy
- **Dependencies**:
  - Task 3.2 completion

## Phase 4: Integration Testing

### Task 4.1: Verify bot token functionality

Ensure refactored client works correctly with bot tokens:

- **Files**:
  - [tests/integration/test_discord_client.py](tests/integration/test_discord_client.py) - Add/update integration tests
- **Success**:
  - `get_guilds()` works with bot token (no parameter)
  - `fetch_guild()` works with bot token
  - `fetch_channel()` works with bot token
  - `fetch_user()` works with bot token
  - All existing bot token tests pass
- **Research References**:
  - #file:../research/20251222-discord-client-token-unification-research.md (Lines 155-180) - E2E test strategy impact
- **Dependencies**:
  - Phase 3 completion

### Task 4.2: Verify OAuth token functionality

Ensure refactored client works correctly with OAuth tokens:

- **Files**:
  - [tests/integration/test_discord_client.py](tests/integration/test_discord_client.py) - Add OAuth token tests
- **Success**:
  - `get_guilds(token=oauth_token)` works correctly
  - `fetch_guild(guild_id, token=oauth_token)` works correctly
  - `fetch_channel(channel_id, token=oauth_token)` works correctly
  - OAuth token format detected as "Bearer" type
- **Research References**:
  - #file:../research/20251222-discord-client-token-unification-research.md (Lines 138-153) - Benefits of unified approach
- **Dependencies**:
  - Task 4.1 completion

## Phase 5: Cleanup

### Task 5.1: Remove deprecated methods

After deprecation period, remove old methods entirely:

- **Files**:
  - [shared/discord/client.py](shared/discord/client.py) - Delete `get_bot_guilds()` and `get_user_guilds()`
- **Success**:
  - Both deprecated methods removed from codebase
  - No callers remain (verified by grep/search)
  - All tests pass without deprecated methods
  - Code complexity reduced
- **Research References**:
  - #file:../research/20251222-discord-client-token-unification-research.md (Lines 134-136) - Remove deprecated methods
- **Dependencies**:
  - Phase 4 completion
  - All callers migrated

### Task 5.2: Update documentation

Update documentation to reflect unified API:

- **Files**:
  - [shared/discord/client.py](shared/discord/client.py) - Update docstrings
  - Any relevant documentation files
- **Success**:
  - Docstrings reflect unified API design
  - Examples show token parameter usage
  - Migration notes removed (no longer relevant)
  - Documentation matches implementation
- **Research References**:
  - #file:../research/20251222-discord-client-token-unification-research.md (Lines 182-194) - Implementation checklist
- **Dependencies**:
  - Task 5.1 completion

## Dependencies

- Python 3.11+
- Existing Discord API client infrastructure
- Test fixtures for bot and OAuth tokens
- Integration test environment

## Success Criteria

- All existing tests pass with refactored client
- Production behavior unchanged (backward compatible)
- New E2E tests can use admin bot token without special handling
- Code complexity reduced (fewer methods, less duplication)
- API surface simplified and more consistent
- Token type handling centralized in single helper method
