<!-- markdownlint-disable-file -->

# Changes: Eliminate Discord REST Call in GET /api/v1/auth/user

## Summary

Store `username` and `avatar` in the Redis session at OAuth callback time so `GET /api/v1/auth/user` can be served entirely from the session cache without calling Discord.

## Added

- `tests/unit/services/api/auth/test_tokens.py` — added three tests for `username`/`avatar` round-trip via `store_user_tokens`/`get_user_tokens`
- `tests/unit/services/api/routes/test_auth_routes.py` — added `test_callback_passes_username_and_avatar_to_store_user_tokens` asserting `username` and `avatar` are forwarded to `store_user_tokens`; updated `test_get_user_info_no_guilds_field` to assert session-sourced `username`/`avatar` without `oauth2` patches; deleted `test_get_user_info_expired_token_refresh_failure` (tests code path that no longer exists)

## Modified

- `services/api/auth/tokens.py` — added `username: str` and `avatar: str | None` params to `store_user_tokens`; included both in `session_data`; included `username` and `avatar` in the `get_user_tokens` return dict; updated `session_data` type annotation to `dict[str, str | bool | None]`
- `services/api/routes/auth.py` — updated `callback` handler to pass `username=user_data.get("username", "")` and `avatar=user_data.get("avatar")` to `store_user_tokens`; replaced `get_user_info` body with a direct session-read, removing token-expiry check, token-refresh block, and `oauth2.get_user_from_token` call

## Removed

_(none yet)_
