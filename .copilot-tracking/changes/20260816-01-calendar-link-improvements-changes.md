<!-- markdownlint-disable-file -->

# Release Changes: Discord Embed Calendar Link Improvements

**Related Plan**: .copilot-tracking/planning/plans/20260816-01-calendar-link-improvements.plan.md
**Implementation Date**: 2026-08-16

## Summary

Adds a self-contained "Add to Google Calendar" quick-add link to the Discord game-announcement embed, and replaces the authenticated `.ics` Blob-forced-download flow with a short-lived-token + public `inline`-disposition `.ics` route.

## Changes

### Added

- shared/schemas/export.py - new file, `CalendarExportTokenResponse` Pydantic schema for the mint-token endpoint (Task 4.1, RED)
- tests/integration/services/api/routes/test_public_calendar.py - new file, 3 integration tests for the public `.ics` route: success without auth, unknown token 404, expired (Redis-key-deleted) token 404 (Task 5.3)

### Modified

- services/bot/utils/discord_format.py - added `build_google_calendar_url` stub (raises `NotImplementedError`) and its supporting module constants (`_GOOGLE_CALENDAR_BASE_URL`, `_GOOGLE_CALENDAR_DEFAULT_DURATION_MINUTES`, `_GOOGLE_CALENDAR_TITLE_MAX_LENGTH`, `_GOOGLE_CALENDAR_LOCATION_MAX_LENGTH`) (Task 1.1, RED)
- tests/unit/services/bot/utils/test_discord_format.py - added `TestBuildGoogleCalendarUrl` with 9 xfail tests asserting exact Google Calendar quick-add URLs (Task 1.1, RED)
- services/bot/utils/discord_format.py - implemented `build_google_calendar_url` (UTC-normalizing naive `scheduled_at`, defaulting duration to 120m, omitting `details`/`location` params when absent) and `_truncate_for_calendar_link` helper; removed the `NotImplementedError` stub (Task 1.2, GREEN)
- tests/unit/services/bot/utils/test_discord_format.py - removed `xfail` markers from the 9 `TestBuildGoogleCalendarUrl` tests (assertions unchanged) (Task 1.2, GREEN)
- tests/unit/services/bot/formatters/test_game_message.py - added 4 xfail tests: two-link `Links` field rendering (present/omitted), a long-input length-guard on `create_game_embed`, and `create_game_embed` threading a Google Calendar URL into the `Links` field (Task 2.1, RED)
- services/bot/formatters/game_message.py - `_add_game_time_fields` gained a trailing `google_calendar_url` parameter rendered as a second `Links`-field line; `create_game_embed` now computes it via `build_google_calendar_url` and threads it through (Task 2.2, GREEN)
- tests/unit/services/bot/formatters/test_game_message.py - removed `xfail` markers from the 4 Task 2.1 tests (assertions unchanged) (Task 2.2, GREEN)
- tests/e2e/helpers/discord.py - `_verify_links_field` now also asserts `calendar.google.com` appears in the Links field when a `game_id` is expected (Task 2.3, optional e2e coverage)
- tests/e2e/test_game_announcement.py - updated the announcement test's docstring to mention the Google Calendar quick-add URL assertion (Task 2.3, optional e2e coverage)
- shared/cache/ttl.py - added `CacheTTL.CALENDAR_EXPORT_TOKEN = 300` (Task 3.1)
- tests/unit/shared/cache/test_ttl.py - added `test_calendar_export_token_ttl` (Task 3.1)
- shared/cache/operations.py - added `CacheOperation.CALENDAR_EXPORT_TOKEN_LOOKUP` member (Task 3.1)
- tests/unit/shared/cache/test_operations.py - added the new member to `_EXPECTED_OPERATIONS` and a value-assertion test (Task 3.1)
- shared/cache/keys.py - added `CacheKeys.calendar_export_token` stub (`NotImplementedError`) (Task 3.2, RED)
- tests/unit/shared/cache/test_keys.py - added xfail `test_calendar_export_token_key` (Task 3.2, RED)
- shared/cache/keys.py - implemented `CacheKeys.calendar_export_token` (Task 3.3, GREEN)
- tests/unit/shared/cache/test_keys.py - removed xfail marker from `test_calendar_export_token_key` (Task 3.3, GREEN)
- services/api/auth/tokens.py - added `mint_calendar_export_token`/`get_calendar_export_token` stubs (`NotImplementedError`) (Task 3.4, RED)
- tests/unit/services/api/auth/test_tokens.py - added 5 xfail tests covering mint (exact `set_json` call args, UUID4-format token) and get (hit, miss, malformed data) (Task 3.4, RED)
- services/api/auth/tokens.py - implemented `mint_calendar_export_token`/`get_calendar_export_token` (unencrypted, TTL-only expiry via `CacheTTL.CALENDAR_EXPORT_TOKEN`, no delete-on-read); added `CacheKeys` import (Task 3.5, GREEN)
- tests/unit/services/api/auth/test_tokens.py - removed xfail markers from the 5 Task 3.4 tests (assertions unchanged) (Task 3.5, GREEN)
- services/api/routes/export.py - added stub `POST /game/{game_id}/token` route (`mint_calendar_token`, raises `NotImplementedError`) and `CalendarExportTokenResponse` import (Task 4.1, RED)
- tests/unit/services/api/routes/test_export.py - added 4 xfail tests: host success, not-found (404), permission-denied (403), participant success (Task 4.1, RED)
- services/api/routes/export.py - implemented `mint_calendar_token`: fetches the game, reuses `permissions_deps.can_export_game(...)` unmodified, raises 403 when it returns `False`, then calls `tokens.mint_calendar_export_token(game_id)` and returns `CalendarExportTokenResponse`; added `tokens` import (Task 4.2, GREEN)
- tests/unit/services/api/routes/test_export.py - removed xfail markers from the 4 Task 4.1 tests (assertions unchanged) (Task 4.2, GREEN)
- services/api/routes/public.py - added `calendar_router` (second `APIRouter`, prefix `/api/v1/public/calendar`) and stub `get_calendar_export` route (raises `NotImplementedError`) (Task 5.1, RED)
- tests/unit/services/api/routes/test_public.py - added `sample_game`/`calendar_app` fixtures and 5 xfail tests: success, missing-extension token, token-not-found 404, game-deleted-after-mint 404, TestClient rate-limited path (Task 5.1, RED)
- services/api/routes/public.py - implemented `get_calendar_export`: resolves the token via `tokens.get_calendar_export_token`, opens a `get_bypass_db_session()` (BYPASSRLS) session to look up the `GameSession` and call `CalendarExportService.export_game(..., can_export=True)`, returns `inline; filename="..."` Content-Disposition; added imports (`tokens`, `generate_calendar_filename`, `CalendarExportService`, `GameSession`, `get_bypass_db_session`) (Task 5.2, GREEN)
- services/api/app.py - registered `app.include_router(public.calendar_router)` (Task 5.2, GREEN)
- tests/unit/services/api/routes/test_public.py - removed xfail markers from the 5 Task 5.1 tests; updated them (and the route's signature) to open a mocked `get_bypass_db_session()` context manager instead of a `Depends(get_db)`-injected session, since `get_calendar_export` no longer takes a `db` parameter (Task 5.2, GREEN)

### Removed
