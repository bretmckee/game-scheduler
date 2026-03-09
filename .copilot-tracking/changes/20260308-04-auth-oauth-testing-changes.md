---
applyTo: '.copilot-tracking/plans/20260308-04-auth-oauth-testing.plan.md'
---

<!-- markdownlint-disable-file -->

# Changes: Auth Route Testing via Fake Discord Server

## Summary

Enabling full integration-test coverage for all 5 auth endpoints by making Discord API URLs configurable and standing up a fake Discord HTTP service.

## Added

- `tests/unit/shared/discord/test_client.py` — Added `discord_client_fake_base` fixture, `_mock_session_returning` helper, and 4 tests verifying `api_base_url` controls all HTTP request URLs (`exchange_code`, `refresh_token`, `get_user_info`, `get_guilds`) — Tasks 1.2/1.3

## Modified

- `shared/discord/client.py` — Added `api_base_url: str = "https://discord.com/api/v10"` parameter to `DiscordAPIClient.__init__`; added `self._token_url`, `self._user_url`, `self._guilds_url` instance attributes derived from `api_base_url`; replaced all internal module-level URL constant usages with instance attributes across all 12 methods; removed the four module-level URL constants entirely — Tasks 1.1/1.3/1.4
- `tests/unit/shared/discord/test_client.py` — Removed `DISCORD_API_BASE` import (constant deleted); hardcoded expected URL in `test_get_application_info_uses_correct_url`; added `MagicMock` to imports — Tasks 1.2/1.4

## Removed

<!-- Files removed by implementation -->

---

## Phase Progress

### Phase 1: `DiscordAPIClient` URL Refactor (TDD) — COMPLETE ✓

All Tasks 1.1–1.4 complete. 153 unit tests pass; 0 lint violations.
