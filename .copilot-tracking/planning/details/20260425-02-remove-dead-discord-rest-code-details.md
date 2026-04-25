<!-- markdownlint-disable-file -->

# Task Details: Remove Dead Discord REST Methods

## Research Reference

**Source Research**: #file:../research/20260425-02-remove-dead-discord-rest-code-research.md

## Phase 1: Remove dead methods from shared/discord/client.py

### Task 1.1: Remove batch OTEL metric declarations

Delete the three module-level batch metric variables and their `create_histogram`/`create_counter` calls. These are only referenced inside the dead `get_guild_members_batch()` method.

- **File**: `shared/discord/client.py` lines 56–68
- **Remove**: `_batch_size_histogram`, `_batch_not_found_counter`, `_batch_duration_histogram` declarations
- **Success**: No `_batch_size_histogram`, `_batch_not_found_counter`, or `_batch_duration_histogram` in the file
- **Research References**:
  - #file:../research/20260425-02-remove-dead-discord-rest-code-research.md (Lines 83–93) — batch metrics section
- **Dependencies**: None

### Task 1.2: Remove guild fetching method group

Delete `get_guilds()`, `_handle_rate_limit_response()`, `_process_guilds_response()`, and `_fetch_guilds_uncached()`. These four methods form a closed chain with no production callers.

- **File**: `shared/discord/client.py`
  - `get_guilds()`: lines 387–441
  - `_handle_rate_limit_response()`: lines 507–544
  - `_process_guilds_response()`: lines 545–580
  - `_fetch_guilds_uncached()`: lines 581–616
- **Success**: None of these method names appear in `shared/discord/client.py`
- **Research References**:
  - #file:../research/20260425-02-remove-dead-discord-rest-code-research.md (Lines 9–12) — dead method table entries for these methods
- **Dependencies**: Task 1.1 complete

### Task 1.3: Remove user and guild member method group

Delete `fetch_user()`, `get_guild_member()`, `get_guild_members_batch()`, and `get_current_user_guild_member()`. None have production callers.

- **File**: `shared/discord/client.py`
  - `fetch_user()`: lines 713–738
  - `get_guild_member()`: lines 739–768
  - `get_guild_members_batch()`: lines 769–818
  - `get_current_user_guild_member()`: lines 819–847
- **Note**: `_get_or_fetch()` (lines 442–464) is called by active methods — must be kept
- **Success**: None of these method names appear in `shared/discord/client.py`
- **Research References**:
  - #file:../research/20260425-02-remove-dead-discord-rest-code-research.md (Lines 13–19) — dead method table entries
  - #file:../research/20260425-02-remove-dead-discord-rest-code-research.md (Lines 43–48) — side effects on `_get_or_fetch`
- **Dependencies**: Task 1.1 complete

### Task 1.4: Remove module-level fetch_user_display_name_safe

Delete the module-level `fetch_user_display_name_safe()` function. It calls the dead `fetch_user()` and has no production callers.

- **File**: `shared/discord/client.py` lines 889–912
- **Success**: `fetch_user_display_name_safe` does not appear in `shared/discord/client.py`
- **Research References**:
  - #file:../research/20260425-02-remove-dead-discord-rest-code-research.md (Lines 25–26) — dead method table entry
- **Dependencies**: Task 1.3 complete

## Phase 2: Remove dead code from oauth2.py and cache/operations.py

### Task 2.1: Remove get_user_guilds from oauth2.py

Delete the `get_user_guilds()` function. All production routes use `member_projection.get_user_guilds()` (Redis) instead.

- **File**: `services/api/auth/oauth2.py` lines 169–191
- **Note**: Also remove `get_user_guilds` from any `__all__` list or import if it becomes unused
- **Success**: `get_user_guilds` does not appear in `services/api/auth/oauth2.py`
- **Research References**:
  - #file:../research/20260425-02-remove-dead-discord-rest-code-research.md (Lines 29–31) — dead wrapper table entry
- **Dependencies**: None (independent of Phase 1)

### Task 2.2: Remove dead CacheOperation enum entries

Remove `FETCH_USER`, `GET_GUILD_MEMBER`, and `GET_USER_GUILDS` from the `CacheOperation` enum. `GET_APPLICATION_INFO` is active and must be kept.

- **File**: `shared/cache/operations.py`
  - Remove `FETCH_USER = "fetch_user"` (line 60)
  - Remove `GET_GUILD_MEMBER = "get_guild_member"` (line 61)
  - Remove `GET_USER_GUILDS = "get_user_guilds"` (line 63)
  - Keep `GET_APPLICATION_INFO = "get_application_info"` (line 62)
- **Success**: Only the three named entries are removed; all other entries remain
- **Research References**:
  - #file:../research/20260425-02-remove-dead-discord-rest-code-research.md (Lines 98–105) — cache operations section
- **Dependencies**: Phases 1 and 2.1 complete (no remaining code references these entries)

## Phase 3: Remove dead tests from test_discord_api_client.py

### Task 3.1: Delete TestGuildMethods class

The entire class covers `test_get_guilds_*` tests — all dead.

- **File**: `tests/unit/shared/discord/test_discord_api_client.py` lines 760–883
- **Success**: `class TestGuildMethods` does not appear in the file
- **Research References**:
  - #file:../research/20260425-02-remove-dead-discord-rest-code-research.md (Lines 52–58) — dead test class table
- **Dependencies**: Phase 1 complete

### Task 3.2: Delete TestUnifiedTokenFunctionality class

All 7 tests in this class are dead (`test_get_guilds_*` and `test_fetch_user_with_oauth_token`).

- **File**: `tests/unit/shared/discord/test_discord_api_client.py` lines 884–1107
- **Success**: `class TestUnifiedTokenFunctionality` does not appear in the file
- **Research References**:
  - #file:../research/20260425-02-remove-dead-discord-rest-code-research.md (Lines 52–58) — dead test class table
- **Dependencies**: Phase 1 complete

### Task 3.3: Remove dead tests from TestCachedResourceMethods

Remove only `test_fetch_user_cache_miss` and `test_fetch_user_cache_hit`. The class stays (`fetch_channel` and `fetch_guild` tests are active).

- **File**: `tests/unit/shared/discord/test_discord_api_client.py`
  - `test_fetch_user_cache_miss`: lines 1141–1166
  - `test_fetch_user_cache_hit`: lines 1167–1180
- **Success**: `TestCachedResourceMethods` remains with only 2 active tests
- **Research References**:
  - #file:../research/20260425-02-remove-dead-discord-rest-code-research.md (Lines 52–58) — dead test table
- **Dependencies**: Tasks 3.1 and 3.2 may shift line numbers; verify before editing

### Task 3.4: Delete standalone function and two whole dead classes

- **File**: `tests/unit/shared/discord/test_discord_api_client.py`
  - Standalone function `test_get_guilds_uses_api_base_url`: lines ~1697–1715
  - Class `TestProcessGuildsResponseHttpError`: lines ~1750–1822
  - Class `TestFetchGuildsUncachedSafetyRaise`: lines ~1823–1851
- **Success**: None of these names appear in the file
- **Research References**:
  - #file:../research/20260425-02-remove-dead-discord-rest-code-research.md (Lines 52–58) — dead test table
- **Dependencies**: Prior removals may shift line numbers; verify before editing

### Task 3.5: Remove dead fetch_user_display_name_safe tests from TestHelperFunctions

Remove three `test_fetch_user_display_name_safe_*` methods from `TestHelperFunctions`. The class stays.

- **File**: `tests/unit/shared/discord/test_discord_api_client.py`
  - `test_fetch_user_display_name_safe_success`: line ~1926
  - `test_fetch_user_display_name_safe_error`: line ~1936
  - `test_fetch_user_display_name_safe_uses_global_client_when_none`: line ~1946
- **Success**: No `test_fetch_user_display_name_safe_*` methods in the file
- **Research References**:
  - #file:../research/20260425-02-remove-dead-discord-rest-code-research.md (Lines 52–58) — dead test table
- **Dependencies**: Prior removals shift line numbers; search by name

### Task 3.6: Remove dead tests from TestReadThroughDelegatesToGetOrFetch; delete TestGetCurrentUserGuildMember

- **File**: `tests/unit/shared/discord/test_discord_api_client.py`
  - Remove `test_fetch_user_delegates_to_get_or_fetch` (line ~2191)
  - Remove `test_get_guild_member_delegates_to_get_or_fetch` (line ~2205)
  - Delete entire `TestGetCurrentUserGuildMember` class (lines ~2219–2246)
- **Success**: `TestGetCurrentUserGuildMember` is gone; `TestReadThroughDelegatesToGetOrFetch` has no `fetch_user` or `guild_member` tests
- **Research References**:
  - #file:../research/20260425-02-remove-dead-discord-rest-code-research.md (Lines 52–58) — dead test table
- **Dependencies**: Prior removals shift line numbers; search by name

### Task 3.7: Update active TestGetOrFetch tests to replace removed CacheOperation.FETCH_USER

Two tests in `TestGetOrFetch` pass `CacheOperation.FETCH_USER` as an example value to `_get_or_fetch`. Replace with `CacheOperation.FETCH_GUILD`.

- **File**: `tests/unit/shared/discord/test_discord_api_client.py`
  - `test_duration_recorded_on_hit`: line ~2125 — change `CacheOperation.FETCH_USER` → `CacheOperation.FETCH_GUILD`
  - `test_duration_recorded_on_miss`: line ~2149 — change `CacheOperation.FETCH_USER` → `CacheOperation.FETCH_GUILD`
- **Success**: `CacheOperation.FETCH_USER` does not appear anywhere in the test file
- **Research References**:
  - #file:../research/20260425-02-remove-dead-discord-rest-code-research.md (Lines 83–93) — cache operations note
- **Dependencies**: Task 2.2 complete (enum entry removed)

## Phase 4: Remove dead tests from test_oauth2.py

### Task 4.1: Remove test_get_user_guilds from TestOAuth2Flow

Delete the `test_get_user_guilds` test method. Remove the `get_user_guilds` import if it becomes unused.

- **File**: `tests/unit/services/api/auth/test_oauth2.py` lines 142–158
- **Success**: `test_get_user_guilds` and `get_user_guilds` do not appear in the file
- **Research References**:
  - #file:../research/20260425-02-remove-dead-discord-rest-code-research.md (Lines 62–63) — dead tests in test_oauth2.py
- **Dependencies**: Phase 2.1 complete

## Phase 5: Verify

### Task 5.1: Run unit tests and grep for removed names

- **Commands**:
  - `uv run pytest tests/unit -x -q`
  - `grep -rn "get_guild_members_batch\|fetch_user_display_name_safe\|CacheOperation\.FETCH_USER\|CacheOperation\.GET_GUILD_MEMBER\|CacheOperation\.GET_USER_GUILDS" services/ shared/ tests/ --include="*.py"` — should return zero results
- **Success**: All tests pass; grep returns no matches
- **Research References**:
  - #file:../research/20260425-02-remove-dead-discord-rest-code-research.md (Lines 113–118) — success criteria
- **Dependencies**: All prior phases complete

## Dependencies

- No external dependencies — all production callers were removed in prior work

## Success Criteria

- All unit tests pass
- No references to removed method or enum names in `services/`, `shared/`, or `tests/`
- `CacheOperation` enum has no `FETCH_USER`, `GET_GUILD_MEMBER`, or `GET_USER_GUILDS` entries
