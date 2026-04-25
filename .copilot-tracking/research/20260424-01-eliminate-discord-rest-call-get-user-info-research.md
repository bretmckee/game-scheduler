<!-- markdownlint-disable-file -->

# Task Research Notes: Eliminate Discord REST call in GET /api/v1/auth/user

## Research Executed

### File Analysis

- `services/api/routes/auth.py`
  - `get_user_info` handler (line 209) calls `oauth2.get_user_from_token(access_token)` on every request
  - Also performs token refresh before that call — which only exists to get a fresh access token for the Discord call
  - `current_user.user.discord_id` is already available from the session (no extra DB or API call needed)
  - `id`, `user_uuid`, `can_be_maintainer`, `is_maintainer` are all available without calling Discord

- `services/api/auth/oauth2.py`
  - `get_user_from_token(access_token)` delegates to `discord.get_user_info(access_token)`

- `shared/discord/client.py`
  - `get_user_info(access_token)` — OAuth Bearer call to `/users/@me`, **no caching**
  - Returns: `id`, `username`, `avatar` (raw hash e.g. `"a_1234abcd"`), `discriminator`, `global_name`, etc.

- `shared/schemas/auth.py`
  - `UserInfoResponse.avatar` — raw avatar **hash** (not a URL)
  - `CurrentUser.user` has `.discord_id: str` — available from the session without any extra call

- `shared/cache/projection.py`
  - Stores `avatar_url` (fully constructed CDN URL) per guild member — **cannot substitute** for the avatar hash without reverse-parsing the URL
  - Also requires `is_bot_fresh()` check and a valid guild ID; unsuitable as a general user-info source

- `services/api/auth/tokens.py`
  - `store_user_tokens()`: currently stores `user_id`, encrypted `access_token`/`refresh_token`, `expires_at`, `can_be_maintainer`, `is_maintainer`
  - `get_user_tokens()`: returns a dict with those same fields — `username` and `avatar` are not currently stored
  - Session TTL is 24 hours (`CacheTTL.SESSION = 86400`)

- `tests/unit/services/api/auth/test_tokens.py`
  - Tests `store_user_tokens` for `can_be_maintainer` flag and `get_user_tokens` for maintainer flag round-trip
  - No existing tests for `username`/`avatar` fields (not currently stored)

- `tests/unit/services/api/routes/test_auth_routes.py`
  - `TestGetUserInfo.test_get_user_info_no_guilds_field` (line 167): mocks `oauth2.get_user_from_token` and `tokens.is_token_expired`
  - `TestGetUserInfo.test_get_user_info_expired_token_refresh_failure` (line 201): tests token refresh path that will be removed

### Code Search Results

- OAuth token exchange (`discord.exchange_code`) returns only: `access_token`, `token_type`, `expires_in`, `refresh_token`, `scope` — **no user identity**
- `identify` scope grants permission to call `GET /users/@me`; it does not embed user data in the token response
- The callback's `get_user_from_token` call is the **one necessary** `GET /users/@me` — `username` and `avatar` hash are available there and currently discarded

## Key Discoveries

### Root Cause

`GET /api/v1/auth/user` always makes an uncached OAuth REST call to Discord because:

1. `get_user_info` calls `oauth2.get_user_from_token(access_token)` to get `username` and `avatar`
2. `get_user_from_token` calls `discord.get_user_info(access_token)` — an uncached `GET /users/@me` on every request

The callback handler already calls `get_user_from_token` once (legitimately, to obtain `discord_id`). At that point `username` and `avatar` hash are available in `user_data` but are discarded. The session stores only OAuth tokens and maintainer flags — not the profile fields.

### Why the Projection Cache Is Not the Right Source

`UserInfoResponse.avatar` is the raw avatar **hash** (e.g. `"a_1234abcd"`). The projection stores `avatar_url` — the fully constructed CDN URL. Extracting the hash from the URL would be fragile. Additionally, reading from the projection requires a guild ID, an `is_bot_fresh()` check, and introduces a 503 failure mode — all unnecessary complexity for what amounts to a profile display field.

### Why Token Refresh Is No Longer Needed in This Route

The entire token-expiry-check + refresh block exists only to get a fresh `access_token` to pass to `get_user_from_token`. Once `username` and `avatar` are stored in the session at callback time, `get_user_info` no longer uses the access token at all. The token refresh block becomes dead code and should be removed.

### Current vs. Proposed Route Behavior

**Current** `get_user_info`:

```
1. get_user_tokens(session_token)     → Redis hit
2. is_token_expired(expires_at)       → in-memory check
3. [if expired] refresh_access_token  → Discord REST call (slow, avoidable)
4. get_user_from_token(access_token)  → Discord REST call (slow, ALWAYS)
```

**Proposed** `get_user_info`:

```
1. get_user_tokens(session_token)     → Redis hit (username + avatar already there)
```

### Where `username` and `avatar` Come From

The OAuth callback already calls `GET /users/@me` once to get `discord_id`. That response also contains `username` and `avatar`. They must be stored in the session at that point and are available for the lifetime of the session (24 hours) — same as `can_be_maintainer` and `is_maintainer`.

## Recommended Approach

Store `username` and `avatar` in the session at callback time (`store_user_tokens`), then read them back from `get_user_tokens` in `get_user_info`. No additional REST calls. No new dependencies. No failure modes beyond the existing session lookup.

## Implementation Guidance

- **Objectives**: Eliminate the unconditional Discord REST call on every `GET /api/v1/auth/user` request

- **Key Tasks**:
  1. **`services/api/auth/tokens.py`** — `store_user_tokens`:
     - Add `username: str` and `avatar: str | None` parameters
     - Store both in `session_data` alongside existing fields
     - Update `get_user_tokens` return dict to include `"username"` and `"avatar"`

  2. **`services/api/routes/auth.py`** — `callback`:
     - Pass `username=user_data["username"]` and `avatar=user_data.get("avatar")` to `store_user_tokens`

  3. **`services/api/routes/auth.py`** — `get_user_info`:
     - Remove the entire token-expiry-check and token-refresh block
     - Remove the `_db` parameter (verify no other usage before removing)
     - Replace `await oauth2.get_user_from_token(access_token)` and its surrounding try/except with direct reads from `token_data`:
       ```python
       return auth_schemas.UserInfoResponse(
           id=current_user.user.discord_id,
           user_uuid=str(current_user.user.id),
           username=token_data["username"],
           avatar=token_data.get("avatar"),
           can_be_maintainer=bool(token_data.get("can_be_maintainer")),
           is_maintainer=bool(token_data.get("is_maintainer")),
       )
       ```

  4. **`tests/unit/services/api/auth/test_tokens.py`**:
     - Add tests verifying `store_user_tokens` stores `username` and `avatar`
     - Add test verifying `get_user_tokens` returns `username` and `avatar`

  5. **`tests/unit/services/api/routes/test_auth_routes.py`**:
     - `test_get_user_info_no_guilds_field`: remove patches for `tokens.is_token_expired` and `oauth2.get_user_from_token`; add `"username"` and `"avatar"` to the `token_data` mock dict
     - `test_get_user_info_expired_token_refresh_failure`: **delete** — the token refresh path no longer exists in `get_user_info`
     - Callback tests: update `store_user_tokens` call expectations to include `username` and `avatar`

- **Dependencies**: None — no new imports or infrastructure required

- **Success Criteria**:
  - `GET /api/v1/auth/user` no longer logs `GET https://discord.com/api/v10/users/@me`
  - All existing unit tests pass
  - `get_user_info` no longer imports or calls anything from `oauth2`
