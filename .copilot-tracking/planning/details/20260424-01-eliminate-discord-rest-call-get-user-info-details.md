<!-- markdownlint-disable-file -->

# Task Details: Eliminate Discord REST Call in GET /api/v1/auth/user

## Research Reference

**Source Research**: #file:../research/20260424-01-eliminate-discord-rest-call-get-user-info-research.md

## Phase 1: Update Token Storage Layer

### Task 1.1 (RED): Write Failing Tests for username/avatar in Token Storage

Add `xfail`-marked tests to `test_tokens.py` asserting `store_user_tokens` stores `username` and `avatar` and that `get_user_tokens` returns them. These tests will show as `xfailed` until Task 1.2 is complete.

- **Files**:
  - `tests/unit/services/api/auth/test_tokens.py` — add tests for username/avatar round-trip
- **Test cases to add** (each marked `@pytest.mark.xfail(reason="username/avatar not yet stored in session", strict=True)`):
  - `test_store_user_tokens_stores_username` — round-trips a non-empty `username`
  - `test_store_user_tokens_stores_avatar` — round-trips a non-None `avatar` hash
  - `test_store_user_tokens_stores_none_avatar` — round-trips `None` avatar (no avatar set)
- **Success**:
  - `uv run pytest tests/unit/services/api/auth/test_tokens.py -v` shows new tests as `xfailed`
- **Research References**:
  - #file:../research/20260424-01-eliminate-discord-rest-call-get-user-info-research.md (Lines 36-47) — existing test structure and missing coverage analysis
- **Dependencies**:
  - None

### Task 1.2 (GREEN): Update store_user_tokens and get_user_tokens

Update `services/api/auth/tokens.py` to accept and persist `username` and `avatar` alongside the existing token fields.

- **Files**:
  - `services/api/auth/tokens.py` — add `username: str` and `avatar: str | None` params to `store_user_tokens`; include both in `session_data`; include `"username"` and `"avatar"` in the `get_user_tokens` return dict
- **Success**:
  - `uv run pytest tests/unit/services/api/auth/test_tokens.py -v` — all three new tests pass (still with `xfail` markers, showing as unexpected pass); all existing tests still pass
- **Research References**:
  - #file:../research/20260424-01-eliminate-discord-rest-call-get-user-info-research.md (Lines 33-35) — current `store_user_tokens`/`get_user_tokens` structure
  - #file:../research/20260424-01-eliminate-discord-rest-call-get-user-info-research.md (Lines 105-107) — implementation guidance for this change
- **Dependencies**:
  - Task 1.1 complete

### Task 1.3 (REFACTOR): Remove xfail Markers from Token Tests

Remove `@pytest.mark.xfail` from the three tests added in Task 1.1.

- **Files**:
  - `tests/unit/services/api/auth/test_tokens.py` — remove `xfail` markers only; no assertion changes
- **Success**:
  - `uv run pytest tests/unit/services/api/auth/test_tokens.py -v` — all tests pass (no xfail, no xpass)
- **Dependencies**:
  - Task 1.2 complete

## Phase 2: Update OAuth Callback to Persist Profile Fields

### Task 2.1 (RED): Write Failing Test for Callback Passing username/avatar to store_user_tokens

Add an `xfail`-marked test (or update an existing callback test) asserting that `store_user_tokens` is called with `username` and `avatar` keyword arguments. The test will show as `xfailed` until Task 2.2 is complete.

- **Files**:
  - `tests/unit/services/api/routes/test_auth_routes.py` — add or update a callback test to assert `username=` and `avatar=` are passed to `store_user_tokens`
- **Success**:
  - `uv run pytest tests/unit/services/api/routes/test_auth_routes.py -v -k callback` shows the new/updated test as `xfailed`
- **Research References**:
  - #file:../research/20260424-01-eliminate-discord-rest-call-get-user-info-research.md (Lines 53-56) — key discovery that callback already calls `GET /users/@me` and has `username`/`avatar` available
  - #file:../research/20260424-01-eliminate-discord-rest-call-get-user-info-research.md (Lines 108-109) — implementation guidance for callback change
- **Dependencies**:
  - Phase 1 complete

### Task 2.2 (GREEN): Update callback to Pass username and avatar to store_user_tokens

Update the `callback` handler in `services/api/routes/auth.py` to pass `username=user_data["username"]` and `avatar=user_data.get("avatar")` to `store_user_tokens`.

- **Files**:
  - `services/api/routes/auth.py` — update the `store_user_tokens(...)` call in the `callback` handler
- **Success**:
  - `uv run pytest tests/unit/services/api/routes/test_auth_routes.py -v -k callback` — updated test unexpectedly passes (xpass); all other callback tests still pass
- **Research References**:
  - #file:../research/20260424-01-eliminate-discord-rest-call-get-user-info-research.md (Lines 25-30) — `get_user_from_token` return payload fields available at callback time
  - #file:../research/20260424-01-eliminate-discord-rest-call-get-user-info-research.md (Lines 108-109) — implementation guidance
- **Dependencies**:
  - Task 2.1 complete

### Task 2.3 (REFACTOR): Remove xfail Markers from Callback Tests

Remove `@pytest.mark.xfail` from the callback test(s) updated in Task 2.1.

- **Files**:
  - `tests/unit/services/api/routes/test_auth_routes.py` — remove `xfail` markers only; no assertion changes
- **Success**:
  - `uv run pytest tests/unit/services/api/routes/test_auth_routes.py -v -k callback` — all tests pass cleanly
- **Dependencies**:
  - Task 2.2 complete

## Phase 3: Simplify get_user_info Route

### Task 3.1 (RED): Update test_get_user_info_no_guilds_field for Session-Sourced Response

Update `test_get_user_info_no_guilds_field` (line 167 in `test_auth_routes.py`) to match the new `get_user_info` behavior: remove the `tokens.is_token_expired` and `oauth2.get_user_from_token` patches; add `"username"` and `"avatar"` to the `token_data` mock dict. This test will fail until Task 3.3 is complete.

- **Files**:
  - `tests/unit/services/api/routes/test_auth_routes.py` — update `test_get_user_info_no_guilds_field`
- **Success**:
  - Running only this test fails (because `get_user_info` still calls `oauth2.get_user_from_token`)
- **Research References**:
  - #file:../research/20260424-01-eliminate-discord-rest-call-get-user-info-research.md (Lines 48-52) — existing test structure for `get_user_info`
  - #file:../research/20260424-01-eliminate-discord-rest-call-get-user-info-research.md (Lines 110-120) — implementation guidance for the route change
- **Dependencies**:
  - Phase 2 complete

### Task 3.2: Delete test_get_user_info_expired_token_refresh_failure

Delete the `test_get_user_info_expired_token_refresh_failure` test (line 201 in `test_auth_routes.py`). The token refresh code path it tests will no longer exist after Task 3.3.

- **Files**:
  - `tests/unit/services/api/routes/test_auth_routes.py` — delete `test_get_user_info_expired_token_refresh_failure`
- **Success**:
  - Test no longer appears in `uv run pytest tests/unit/services/api/routes/test_auth_routes.py --collect-only`
- **Research References**:
  - #file:../research/20260424-01-eliminate-discord-rest-call-get-user-info-research.md (Lines 48-52) — existing test that covers the removed code path
- **Dependencies**:
  - Task 3.1 complete

### Task 3.3 (GREEN): Simplify get_user_info to Read from Session Data Only

Replace the body of `get_user_info` in `services/api/routes/auth.py`: remove the token-expiry-check, token-refresh block, and the `oauth2.get_user_from_token` call and its surrounding try/except. Return `UserInfoResponse` fields directly from `token_data`. Remove `_db` parameter if it is no longer used by this route.

- **Files**:
  - `services/api/routes/auth.py` — simplify `get_user_info` as described
- **New implementation**:
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
- **Success**:
  - `uv run pytest tests/unit/services/api/routes/test_auth_routes.py -v` — all tests pass, including the updated `test_get_user_info_no_guilds_field`
  - `get_user_info` has no import or call referencing `oauth2`
- **Research References**:
  - #file:../research/20260424-01-eliminate-discord-rest-call-get-user-info-research.md (Lines 57-80) — root cause analysis and proposed route behavior
  - #file:../research/20260424-01-eliminate-discord-rest-call-get-user-info-research.md (Lines 110-120) — complete implementation guidance
- **Dependencies**:
  - Tasks 3.1 and 3.2 complete

## Dependencies

- No new imports or external dependencies required

## Success Criteria

- `GET /api/v1/auth/user` no longer calls `GET https://discord.com/api/v10/users/@me`
- `get_user_info` no longer imports or calls anything from `oauth2`
- All unit tests pass with no new failures
