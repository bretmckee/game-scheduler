---
applyTo: '.copilot-tracking/changes/20260816-01-calendar-link-improvements-changes.md'
---

<!-- markdownlint-disable-file -->

# Task Checklist: Discord Embed Calendar Link Improvements

## Overview

Add a self-contained "Add to Google Calendar" quick-add link to the Discord game-announcement embed, and replace the existing authenticated `.ics` Blob-forced-download flow with a short-lived-token + public `inline`-disposition `.ics` route so mobile OSes can hand the file to a calendar app, migrating both in-app export buttons to the same flow.

## Objectives

- Add a second, self-contained "Add to Google Calendar" link to the Discord embed's `Links` field, built entirely from data already available to the bot, with no backend or auth changes.
- Replace the authenticated `.ics` Blob-download flow behind the Discord-embed calendar link with a mint-token-then-real-navigate flow, using a short-lived opaque Redis token and a new public, rate-limited, unauthenticated `.ics`-serving route with `Content-Disposition: inline`.
- Migrate the in-app `ExportButton.tsx` and `GameDetails.tsx` export buttons to the same mint-then-navigate flow.
- Keep `services/api/routes/export.py`'s existing authenticated export endpoint and `CalendarExportService` unchanged and in place (not removed).

## Research Summary

### Project Files

- `services/bot/formatters/game_message.py` - builds the Discord embed; `_add_game_time_fields`'s `Links` field is where the second calendar link is wired in; `create_game_embed` already receives every field the Google-link builder needs
- `services/bot/utils/discord_format.py` - home for the new pure-function Google Calendar URL builder, alongside `format_duration`/`format_discord_timestamp`/`format_rules_section`
- `services/api/auth/tokens.py` - `store_user_tokens`/`get_user_tokens` (L89-173) is the direct template for the new calendar-export-token mint/get functions
- `services/api/routes/export.py` - `export_game`'s permission-check pattern (L92-133) is reused unmodified for the new mint-token route; `generate_calendar_filename` (L54-84) is reused for the public route's filename
- `services/api/routes/public.py` - `get_image`/`head_image` (L59-165) is the direct template for the new public, rate-limited, unauthenticated `.ics`-serving route (second `APIRouter` in the same file)
- `services/api/services/calendar_export.py` - `CalendarExportService.export_game` (L55-104) trusts a pre-computed `can_export` boolean from its caller; the public route relies on this to avoid re-authenticating
- `services/api/dependencies/permissions.py` - `can_export_game` (L677-727) reused unmodified by the new mint-token route
- `shared/cache/ttl.py`, `shared/cache/keys.py`, `shared/cache/operations.py` - one new constant/staticmethod/enum-member each, following existing conventions exactly
- `shared/models/game.py` - `title` is `String(200)`, `where` is unbounded `Text` (L58, L62) - drives the Google-link builder's explicit length guards
- `frontend/src/pages/DownloadCalendar.tsx` - current fetch+Blob flow, rewritten to mint-then-`window.location.href`-navigate
- `frontend/src/components/ExportButton.tsx`, `frontend/src/pages/GameDetails.tsx` - in-app export buttons migrated to the same flow

### External References

- .copilot-tracking/research/20260816-01-calendar-link-improvements-research.md - full research findings for both improvements
- Source: [InteractionDesignFoundation/add-event-to-calendar-docs — google.md](https://github.com/InteractionDesignFoundation/add-event-to-calendar-docs/blob/main/services/google.md) - Google Calendar quick-add `TEMPLATE` URL scheme, `dates=` format, encoding rules

### Standards References

- .github/instructions/test-driven-development.instructions.md - RED (stub + xfail/`.failing`) → GREEN (implement, remove markers) → REFACTOR for every new function/route/component in this plan
- .github/instructions/unit-tests.instructions.md - exact-value assertions (constructed URLs, exact `set_json`/`get_json` call args), no weak `assert_called_once()`-only checks
- .github/instructions/fastapi-transaction-patterns.instructions.md - both new routes are read-only (no `db.commit()` obligations)
- .github/instructions/api-authorization.instructions.md - the mint-token route must reuse `can_export_game` unmodified, with no inline authorization code; 404 for non-members, 403 for members without permission
- .github/instructions/integration-tests.instructions.md - new public-route integration tests run via `scripts/run-integration-tests.sh`, piped through `tee`
- .github/instructions/test-execution.instructions.md - never invoke integration/e2e scripts with bare `pytest`

## Implementation Checklist

### [x] Phase 1: Google Calendar Quick-Add URL Builder (bot-side, self-contained)

- [x] Task 1.1: RED — stub `build_google_calendar_url` in `services/bot/utils/discord_format.py` and write xfail tests with exact-URL assertions (full data, missing description/location/duration, naive-vs-aware `scheduled_at`, title/location/description truncation, special-character encoding)
  - Details: .copilot-tracking/planning/details/20260816-01-calendar-link-improvements-details.md (Lines 11-55)

- [x] Task 1.2: GREEN — implement `build_google_calendar_url` and `_truncate_for_calendar_link`, remove xfail markers
  - Details: .copilot-tracking/planning/details/20260816-01-calendar-link-improvements-details.md (Lines 56-94)

### [x] Phase 2: Wire Google Calendar Link into Discord Embed Links Field

- [x] Task 2.1: RED — add `google_calendar_url` parameter to `_add_game_time_fields`; write xfail tests for the two-link `Links` field, including a length-guard test with near-max title (200 chars) and long `where` asserting the field value stays under 1024 chars
  - Details: .copilot-tracking/planning/details/20260816-01-calendar-link-improvements-details.md (Lines 97-118)

- [x] Task 2.2: GREEN — wire `build_google_calendar_url` into `create_game_embed`/`_add_game_time_fields`, remove xfail markers
  - Details: .copilot-tracking/planning/details/20260816-01-calendar-link-improvements-details.md (Lines 119-154)

- [x] Task 2.3: REFACTOR — optional e2e coverage for the Google Calendar link in `tests/e2e/helpers/discord.py`/`tests/e2e/test_game_announcement.py`
  - Details: .copilot-tracking/planning/details/20260816-01-calendar-link-improvements-details.md (Lines 155-166)

### [x] Phase 3: Redis-Backed Calendar Export Token Helpers (API backend)

- [x] Task 3.1: Add `CacheTTL.CALENDAR_EXPORT_TOKEN` and `CacheOperation.CALENDAR_EXPORT_TOKEN_LOOKUP` constants with direct (non-xfail) tests
  - Details: .copilot-tracking/planning/details/20260816-01-calendar-link-improvements-details.md (Lines 170-186)

- [x] Task 3.2: RED — stub `CacheKeys.calendar_export_token` and write xfail test
  - Details: .copilot-tracking/planning/details/20260816-01-calendar-link-improvements-details.md (Lines 188-217)

- [x] Task 3.3: GREEN — implement `CacheKeys.calendar_export_token`, remove xfail marker
  - Details: .copilot-tracking/planning/details/20260816-01-calendar-link-improvements-details.md (Lines 219-235)

- [x] Task 3.4: RED — stub `mint_calendar_export_token`/`get_calendar_export_token` in `services/api/auth/tokens.py` and write xfail tests (exact `set_json`/`get_json`/`cache_get` call-arg assertions, malformed-data handling)
  - Details: .copilot-tracking/planning/details/20260816-01-calendar-link-improvements-details.md (Lines 237-279)

- [x] Task 3.5: GREEN — implement both token functions (unencrypted, TTL-only expiry, no delete-on-read), remove xfail markers
  - Details: .copilot-tracking/planning/details/20260816-01-calendar-link-improvements-details.md (Lines 281-316)

### [ ] Phase 4: Authenticated Mint-Token Route (`services/api/routes/export.py`)

- [ ] Task 4.1: RED — add `CalendarExportTokenResponse` schema, stub `POST /api/v1/export/game/{game_id}/token`, write xfail tests (host success, not found, permission denied, participant success)
  - Details: .copilot-tracking/planning/details/20260816-01-calendar-link-improvements-details.md (Lines 320-374)

- [ ] Task 4.2: GREEN — implement `mint_calendar_token` reusing `can_export_game` unmodified, remove xfail markers
  - Details: .copilot-tracking/planning/details/20260816-01-calendar-link-improvements-details.md (Lines 376-400)

### [ ] Phase 5: Public Unauthenticated `.ics` Route + App Registration + Integration Tests

- [ ] Task 5.1: RED — add `calendar_router` (second `APIRouter`) to `services/api/routes/public.py`, stub `get_calendar_export`, write xfail unit tests (success, missing-extension token, token-not-found 404, game-deleted-after-mint 404, TestClient rate-limited path)
  - Details: .copilot-tracking/planning/details/20260816-01-calendar-link-improvements-details.md (Lines 404-445)

- [ ] Task 5.2: GREEN — implement `get_calendar_export` (token→game_id, `CalendarExportService.export_game(..., can_export=True)`, `inline` Content-Disposition with `filename=`), register `public.calendar_router` in `services/api/app.py`, remove xfail markers
  - Details: .copilot-tracking/planning/details/20260816-01-calendar-link-improvements-details.md (Lines 447-507)

- [ ] Task 5.3: Add integration tests for the public `.ics` route under `tests/integration/services/api/routes/`, run via `scripts/run-integration-tests.sh`
  - Details: .copilot-tracking/planning/details/20260816-01-calendar-link-improvements-details.md (Lines 509-528)

### [ ] Phase 6: Frontend Shared Mint Helper + `DownloadCalendar.tsx` Rewrite

- [ ] Task 6.1: RED — create `frontend/src/api/calendarExport.ts` stub (`mintCalendarExportToken`, `buildCalendarExportUrl`); rewrite `DownloadCalendar.test.tsx` with `test.failing` cases (mint success/navigate, 403/404/generic mint failures, error-alert-close navigation); retain the unchanged loading-spinner test as-is
  - Details: .copilot-tracking/planning/details/20260816-01-calendar-link-improvements-details.md (Lines 532-565)

- [ ] Task 6.2: GREEN — implement the mint helper and rewrite `DownloadCalendar.tsx` to mint-then-`window.location.href`-navigate, removing the old fetch+Blob code, remove `.failing` markers
  - Details: .copilot-tracking/planning/details/20260816-01-calendar-link-improvements-details.md (Lines 567-596)

### [ ] Phase 7: Frontend `ExportButton.tsx` / `GameDetails.tsx` Migration

- [ ] Task 7.1: RED — create `ExportButton.test.tsx` (new file) and add calendar-export tests to `GameDetails` tests, all `test.failing`, mocking the Phase 6 mint helper
  - Details: .copilot-tracking/planning/details/20260816-01-calendar-link-improvements-details.md (Lines 600-621)

- [ ] Task 7.2: GREEN — migrate both components' handlers to mint-then-navigate, removing the `axios.get(..., { responseType: 'blob' })` Blob-download code, remove `.failing` markers
  - Details: .copilot-tracking/planning/details/20260816-01-calendar-link-improvements-details.md (Lines 623-639)

## Dependencies

- Python 3.13+, `uv run pytest`, `uv run mypy` for all backend phases (1-5)
- Node/`npm` (Vitest, `npm run build`) for frontend phases (6-7)
- Existing Redis (`shared.cache`) infrastructure — no new infra
- No new environment variables, config fields, or database migrations required

## Success Criteria

- Discord embed's `Links` field renders both the existing download-calendar link and a correctly-encoded Google Calendar quick-add link, for games with and without optional fields, staying under Discord's 1024-character field cap even with a long `where` and near-max `title`
- Tapping the Discord-embed calendar link, or either in-app Export button, results in a `Content-Disposition: inline` `text/calendar` response rather than a forced download (verified by header assertions in unit/integration tests)
- The new public `.ics` route 404s on missing/expired tokens and never re-runs `can_export_game`
- The existing authenticated `GET /api/v1/export/game/{game_id}` endpoint and `CalendarExportService` remain functional and unchanged
- `uv run pytest tests/unit`, `uv run mypy shared/ services/`, `cd frontend && npm run build`, `cd frontend && npm run test`, and `scripts/run-integration-tests.sh` all pass
