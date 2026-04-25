<!-- markdownlint-disable-file -->

# Task Research Notes: Remove Dead Discord REST Methods and Their Tests

## Research Executed

### File Analysis

- `shared/discord/client.py`
  - Contains `DiscordAPIClient` with methods that are no longer called from any production path
  - Contains module-level helper `fetch_user_display_name_safe()` with no production callers
- `services/api/auth/oauth2.py`
  - Contains `get_user_guilds()` wrapper around `discord_client.get_guilds()` — no production callers
  - Contains `get_user_from_token()` wrapper around `discord_client.get_user_info()` — still used (OAuth callback); NOT dead
- `tests/unit/shared/discord/test_discord_api_client.py`
  - 109 total tests; several full test classes cover the dead methods exclusively
- `tests/unit/services/api/auth/test_oauth2.py`
  - Contains `TestGetUserFromToken` and tests for `get_user_guilds()` wrapper — those wrapping dead methods are dead too

### Code Search Results

- `get_guilds` in `services/` (non-test, non-definition)
  - One caller: `services/api/auth/oauth2.py:184` inside the dead `get_user_guilds()` wrapper
- `get_guild_member` / `get_guild_members_batch` in `services/`
  - Zero production callers; only test files reference them
- `fetch_user` (the `DiscordAPIClient` method) in `services/`
  - Zero production callers
- `get_current_user_guild_member` in `services/`
  - Zero production callers (removed from auth flow in changes file `20260418-01`)
- `fetch_user_display_name_safe` in `services/` and `shared/`
  - Zero production callers (only appears in its own test)
- `oauth2.get_user_guilds` (production routes, not tests)
  - Zero callers; all production code uses `member_projection.get_user_guilds()` (Redis)

### Project Conventions

- Dead code removed without replacement; associated tests removed too
- `access_token` parameters already deprecated to `_access_token` in some callers; this removal is a continuation of that pattern
- The `_get_or_fetch` helper and `_fetch_guilds_uncached` are only reachable via the dead methods; they also become dead

## Key Discoveries

### What Is Dead vs What Is Not

| Method                            | Location                            | Status     | Reason                                                       |
| --------------------------------- | ----------------------------------- | ---------- | ------------------------------------------------------------ |
| `get_guilds()`                    | `DiscordAPIClient`                  | **Dead**   | Only called from dead `oauth2.get_user_guilds()`             |
| `_fetch_guilds_uncached()`        | `DiscordAPIClient`                  | **Dead**   | Only called from `get_guilds()`                              |
| `_handle_rate_limit_response()`   | `DiscordAPIClient`                  | **Dead**   | Only called from `_fetch_guilds_uncached()`                  |
| `_process_guilds_response()`      | `DiscordAPIClient`                  | **Dead**   | Only called from `_fetch_guilds_uncached()`                  |
| `get_guild_member()`              | `DiscordAPIClient`                  | **Dead**   | No production callers                                        |
| `get_guild_members_batch()`       | `DiscordAPIClient`                  | **Dead**   | No production callers                                        |
| `fetch_user()`                    | `DiscordAPIClient`                  | **Dead**   | No production callers                                        |
| `get_current_user_guild_member()` | `DiscordAPIClient`                  | **Dead**   | No production callers                                        |
| `fetch_user_display_name_safe()`  | `shared/discord/client.py` (module) | **Dead**   | No production callers                                        |
| `oauth2.get_user_guilds()`        | `services/api/auth/oauth2.py`       | **Dead**   | No production callers                                        |
| `get_user_info()`                 | `DiscordAPIClient`                  | **Active** | Called from `oauth2.get_user_from_token()` at OAuth callback |
| `get_application_info()`          | `DiscordAPIClient`                  | **Active** | Called from `oauth2.is_app_maintainer()`                     |
| `exchange_code()`                 | `DiscordAPIClient`                  | **Active** | OAuth2 plumbing                                              |
| `refresh_token()`                 | `DiscordAPIClient`                  | **Active** | OAuth2 plumbing                                              |
| `fetch_channel()`                 | `DiscordAPIClient`                  | **Active** | Used by `fetch_channel_name_safe()` which has callers        |
| `fetch_guild()`                   | `DiscordAPIClient`                  | **Active** | Used by `fetch_guild_name_safe()` which has callers          |
| `fetch_guild_roles()`             | `DiscordAPIClient`                  | **Active** | Used in guilds route                                         |
| `get_guild_channels()`            | `DiscordAPIClient`                  | **Active** | Used in guild service and channel resolver                   |

### Side Effects on `_get_or_fetch`

`_get_or_fetch()` is called by `fetch_user()`, `get_guild_member()`, `get_application_info()`, `fetch_channel()`, `fetch_guild()`, and `fetch_guild_roles()`. Since some active methods still use it, `_get_or_fetch` must be **kept**. Only the dead _callers_ are removed.

### Dead Test Classes in `test_discord_api_client.py`

| Class                                  | Lines     | Tests | Notes                                                                        |
| -------------------------------------- | --------- | ----- | ---------------------------------------------------------------------------- |
| `TestUserDataMethods`                  | 705–758   | 2     | `test_get_user_info_*` — `get_user_info` is still active; keep these         |
| `TestGuildMethods`                     | 760–1107  | ~20   | Mix: `test_get_guilds_*` are dead; `test_get_guild_channels_*` are active    |
| `TestGuildMemberMethods`               | 1181–1411 | 14    | All dead — `get_guild_member*`                                               |
| `TestGetCurrentUserGuildMember`        | 2219–2245 | 2     | All dead                                                                     |
| `TestUnifiedTokenFunctionality`        | 884–1107  | ~8    | `test_fetch_user_*` dead; `test_get_guild_channels_*` active                 |
| `TestGetUserInfoNetworkError`          | 1717–1738 | 1     | `get_user_info` is still active; keep                                        |
| `TestReadThroughDelegatesToGetOrFetch` | 2157–2217 | 2     | `test_fetch_user_delegates_*` dead; `test_get_guild_member_delegates_*` dead |

**Note:** `TestGuildMethods` and `TestUnifiedTokenFunctionality` are mixed — individual test functions must be removed rather than deleting whole classes.

### Dead Tests in `test_oauth2.py`

- `test_get_user_guilds_*` — wrapper is dead

### `BATCH_DURATION_HISTOGRAM` and counters

Metrics `_batch_size_histogram`, `_batch_not_found_counter`, `_batch_duration_histogram` are only referenced inside the dead `get_guild_members_batch()`. They should be removed along with it.

## Recommended Approach

Remove all dead methods and their test coverage in a single commit. Work file by file:

1. **`shared/discord/client.py`** — delete methods: `get_guilds`, `_fetch_guilds_uncached`, `_handle_rate_limit_response`, `_process_guilds_response`, `get_guild_member`, `get_guild_members_batch`, `fetch_user`, `get_current_user_guild_member`, and module-level `fetch_user_display_name_safe`. Also delete the three batch metrics (`_batch_size_histogram`, `_batch_not_found_counter`, `_batch_duration_histogram`) and their `create_histogram`/`create_counter` calls.

2. **`services/api/auth/oauth2.py`** — delete `get_user_guilds()` function.

3. **`tests/unit/shared/discord/test_discord_api_client.py`** — delete `TestGuildMemberMethods`, `TestGetCurrentUserGuildMember`, and the entirety of dead individual test functions inside `TestGuildMethods` (all `get_guilds_*` tests) and `TestUnifiedTokenFunctionality` (all `fetch_user_*` tests). Delete `test_fetch_user_display_name_safe_*` from `TestHelperFunctions`. Delete `test_fetch_user_delegates_*` and `test_get_guild_member_delegates_*` from `TestReadThroughDelegatesToGetOrFetch`.

4. **`tests/unit/services/api/auth/test_oauth2.py`** — delete `test_get_user_guilds_*` test(s).

5. **`shared/cache/operations.py`** — delete `FETCH_USER`, `GET_GUILD_MEMBER`, `GET_APPLICATION_INFO` entries if no other code uses them (verify first).

## Implementation Guidance

- **Objectives**: Remove all dead REST methods from `DiscordAPIClient`, their wrappers in `oauth2.py`, and all corresponding tests
- **Key Tasks**:
  1. Delete dead methods from `shared/discord/client.py`
  2. Delete `oauth2.get_user_guilds()` from `services/api/auth/oauth2.py`
  3. Remove associated test functions/classes
  4. Run unit tests to confirm nothing breaks
- **Dependencies**: None — all callers have already been removed in prior work
- **Success Criteria**: All tests pass; `grep` for the removed method names in `services/` and `shared/` returns zero results
