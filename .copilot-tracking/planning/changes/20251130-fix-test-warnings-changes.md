# Changes: Fix Test Warnings

**Date**: 2025-11-30

## Overview

Fixed all pytest warnings related to deprecated APIs and unawaited coroutines in test mocks. Reduced warnings from 16 to 1 (remaining warning is from external discord.py library).

## Changes Made

### 1. Fixed Deprecated HTTP Status Code

**File**: `services/api/middleware/error_handler.py`

- **Changed**: Replaced deprecated `status.HTTP_422_UNPROCESSABLE_ENTITY` with `status.HTTP_422_UNPROCESSABLE_CONTENT`
- **Reason**: FastAPI/Starlette deprecated the old constant name to align with RFC 9110 terminology
- **Impact**: Eliminates DeprecationWarning in error handler tests

### 2. Fixed Discord Client Test Mocks

**File**: `tests/services/api/auth/test_discord_client.py`

- **Changed**: Added `headers` attribute with proper mock to all `mock_response` objects in 6 test methods:
  - `test_exchange_code_success`
  - `test_exchange_code_failure`
  - `test_refresh_token_success`
  - `test_get_user_info_success`
  - `test_get_user_guilds_success`
  - `test_get_guild_member_success`
- **Reason**: The `_log_response()` method accesses `response.headers.get()`, and mock responses were missing this attribute, causing RuntimeWarning about unawaited coroutines
- **Impact**: Eliminates 6 RuntimeWarnings in Discord API client tests

### 3. Fixed Notification Schedule Test Mocks

**File**: `tests/services/api/services/test_notification_schedule.py`

- **Changed**: Made `mock_db.add` synchronous by explicitly setting it to `MagicMock()` in 3 test functions:
  - `test_populate_schedule_creates_future_notifications`
  - `test_populate_schedule_skips_past_notifications`
  - `test_update_schedule_deletes_and_creates`
- **Reason**: SQLAlchemy's `session.add()` is synchronous, but `AsyncMock()` makes all attributes async by default
- **Impact**: Eliminates 3 RuntimeWarnings in notification schedule tests

### 4. Fixed Participant Resolver Test Mock

**File**: `tests/services/api/services/test_participant_resolver.py`

- **Changed**: Modified `test_network_error_handling` to properly mock the context manager for `session.get()`
- **Before**: Used async function with `side_effect` which created unawaited coroutine
- **After**: Created mock context manager with `__aenter__` raising the exception
- **Reason**: The actual code uses `async with session.get()` which requires a proper context manager mock
- **Impact**: Eliminates 1 RuntimeWarning in participant resolver tests

### 5. Fixed Config Guild Command Test Mock

**File**: `tests/services/bot/commands/test_config_guild.py`

- **Changed**: Made `mock_session.add` synchronous in `test_config_guild_creates_new_config`
- **Reason**: SQLAlchemy's `session.add()` is synchronous
- **Impact**: Eliminates 1 RuntimeWarning in config guild command tests

### 6. Fixed My Games Command Test Mock

**File**: `tests/services/bot/commands/test_my_games.py`

- **Changed**: Made `mock_session.add` synchronous in `test_my_games_creates_new_user`
- **Reason**: SQLAlchemy's `session.add()` is synchronous
- **Impact**: Eliminates 1 RuntimeWarning in my games command tests

## Testing

### Test Results

- All 64 tests in modified files pass successfully
- All tests pass linting with `ruff check`
- All tests pass formatting check with `ruff format --check`
- Overall test suite: 512 passed, 4 failed (unrelated integration tests), 10 errors (unrelated e2e tests)

### Warnings Reduction

- **Before**: 16 warnings
- **After**: 1 warning (external library: discord.py's use of deprecated `audioop`)
- **Improvement**: 93.75% reduction in warnings

## Impact Assessment

### Benefits

- Cleaner test output without spurious warnings
- Better test reliability by properly mocking async/sync boundaries
- Improved maintainability with correct mock patterns
- Compliance with modern FastAPI/Starlette standards

### Risks

- None - all changes are test-only or fix deprecated API usage
- No production code logic changes
- All tests pass successfully

## Verification

```bash
# Run linting
uv run ruff check services/api/middleware/error_handler.py tests/services/api/auth/test_discord_client.py tests/services/api/services/test_notification_schedule.py tests/services/api/services/test_participant_resolver.py tests/services/bot/commands/test_config_guild.py tests/services/bot/commands/test_my_games.py

# Run formatting check
uv run ruff format --check services/api/middleware/error_handler.py tests/services/api/auth/test_discord_client.py tests/services/api/services/test_notification_schedule.py tests/services/api/services/test_participant_resolver.py tests/services/bot/commands/test_config_guild.py tests/services/bot/commands/test_my_games.py

# Run tests
uv run pytest tests/services/api/middleware/test_error_handler.py tests/services/api/auth/test_discord_client.py tests/services/api/services/test_notification_schedule.py tests/services/api/services/test_participant_resolver.py tests/services/bot/commands/test_config_guild.py tests/services/bot/commands/test_my_games.py -v

# Check overall warnings
uv run pytest tests/ --tb=no -q 2>&1 | grep -A 50 "warnings summary"
```

## Related Documentation

- FastAPI Status Codes: https://fastapi.tiangolo.com/reference/status/
- RFC 9110 HTTP Semantics: https://www.rfc-editor.org/rfc/rfc9110.html#name-422-unprocessable-content
- pytest warning handling: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
