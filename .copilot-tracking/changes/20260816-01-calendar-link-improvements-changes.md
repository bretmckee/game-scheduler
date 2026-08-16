<!-- markdownlint-disable-file -->

# Release Changes: Discord Embed Calendar Link Improvements

**Related Plan**: .copilot-tracking/planning/plans/20260816-01-calendar-link-improvements.plan.md
**Implementation Date**: 2026-08-16

## Summary

Adds a self-contained "Add to Google Calendar" quick-add link to the Discord game-announcement embed, and replaces the authenticated `.ics` Blob-forced-download flow with a short-lived-token + public `inline`-disposition `.ics` route.

## Changes

### Added

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

### Removed
