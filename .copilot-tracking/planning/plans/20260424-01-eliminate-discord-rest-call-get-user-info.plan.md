---
applyTo: '.copilot-tracking/changes/20260424-01-eliminate-discord-rest-call-get-user-info-changes.md'
---

<!-- markdownlint-disable-file -->

# Task Checklist: Eliminate Discord REST Call in GET /api/v1/auth/user

## Overview

Store `username` and `avatar` in the Redis session at OAuth callback time so `GET /api/v1/auth/user` can be served entirely from the session cache without calling Discord.

## Objectives

- Eliminate the unconditional `GET /users/@me` REST call on every `GET /api/v1/auth/user` request
- Remove the now-dead token-expiry-check and token-refresh block from `get_user_info`
- Add tests for the new `username`/`avatar` session fields; keep all existing tests passing

## Research Summary

### Project Files

- `services/api/auth/tokens.py` — token storage layer; needs `username`/`avatar` params
- `services/api/routes/auth.py` — `callback` and `get_user_info` handlers
- `tests/unit/services/api/auth/test_tokens.py` — unit tests for token storage
- `tests/unit/services/api/routes/test_auth_routes.py` — route handler tests

### External References

- #file:../research/20260424-01-eliminate-discord-rest-call-get-user-info-research.md — root-cause analysis, current vs. proposed route behavior, and complete implementation guidance

## Implementation Checklist

### [ ] Phase 1: Update Token Storage Layer

- [ ] Task 1.1 (RED): Write failing tests for `username`/`avatar` in token storage
  - Details: .copilot-tracking/planning/details/20260424-01-eliminate-discord-rest-call-get-user-info-details.md (Lines 11-27)

- [ ] Task 1.2 (GREEN): Update `store_user_tokens` and `get_user_tokens` to persist `username` and `avatar`
  - Details: .copilot-tracking/planning/details/20260424-01-eliminate-discord-rest-call-get-user-info-details.md (Lines 28-41)

- [ ] Task 1.3 (REFACTOR): Remove `xfail` markers from token tests
  - Details: .copilot-tracking/planning/details/20260424-01-eliminate-discord-rest-call-get-user-info-details.md (Lines 42-52)

### [ ] Phase 2: Update OAuth Callback to Persist Profile Fields

- [ ] Task 2.1 (RED): Write failing test asserting `callback` passes `username`/`avatar` to `store_user_tokens`
  - Details: .copilot-tracking/planning/details/20260424-01-eliminate-discord-rest-call-get-user-info-details.md (Lines 55-68)

- [ ] Task 2.2 (GREEN): Update `callback` to pass `username` and `avatar` to `store_user_tokens`
  - Details: .copilot-tracking/planning/details/20260424-01-eliminate-discord-rest-call-get-user-info-details.md (Lines 69-82)

- [ ] Task 2.3 (REFACTOR): Remove `xfail` markers from callback tests
  - Details: .copilot-tracking/planning/details/20260424-01-eliminate-discord-rest-call-get-user-info-details.md (Lines 83-93)

### [ ] Phase 3: Simplify get_user_info Route

- [ ] Task 3.1 (RED): Update `test_get_user_info_no_guilds_field` to expect session-sourced response (will fail until 3.3)
  - Details: .copilot-tracking/planning/details/20260424-01-eliminate-discord-rest-call-get-user-info-details.md (Lines 96-109)

- [ ] Task 3.2: Delete `test_get_user_info_expired_token_refresh_failure`
  - Details: .copilot-tracking/planning/details/20260424-01-eliminate-discord-rest-call-get-user-info-details.md (Lines 110-122)

- [ ] Task 3.3 (GREEN): Simplify `get_user_info` to read from session data only, removing refresh block and REST call
  - Details: .copilot-tracking/planning/details/20260424-01-eliminate-discord-rest-call-get-user-info-details.md (Lines 123-148)

## Dependencies

- No new imports or external dependencies required

## Success Criteria

- `GET /api/v1/auth/user` no longer calls `GET https://discord.com/api/v10/users/@me`
- `get_user_info` no longer imports or calls anything from `oauth2`
- All unit tests pass with no new failures
