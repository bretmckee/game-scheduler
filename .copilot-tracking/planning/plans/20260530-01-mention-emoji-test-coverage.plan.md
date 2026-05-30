---
applyTo: '.copilot-tracking/planning/changes/20260530-01-mention-emoji-test-coverage-changes.md'
---

<!-- markdownlint-disable-file -->

# Task Checklist: Mention and Emoji Resolution Test Coverage

## Overview

Add integration and e2e test coverage for the user/channel/emoji mention resolution pipeline in game text fields.

## Objectives

- Verify the custom emoji round-trip (forward resolution + reverse render) for title, description, and signup_instructions via integration tests
- Verify channel mention and user mention reverse-render in description via e2e test augmentation
- Verify channel mention resolution in signup_instructions via e2e test augmentation
- Add `DISCORD_TEST_EMOJI_NAME` optional env var so custom emoji assertions can run when available and skip gracefully when absent

## Research Summary

### Project Files

- `services/api/services/emoji_resolver.py` — `resolve_emoji_mentions()` (forward) and `render_emoji_for_display()` (reverse)
- `services/api/services/channel_resolver.py` — `resolve_channel_mentions()` (forward) and `render_text_for_display()` (reverse, handles both `<#id>` and `<@id>`)
- `services/api/services/participant_resolver.py` — `resolve_mentions_in_text()` forward resolution (safe only for `@username` input format)
- `services/api/routes/games.py` — `_render_text_fields()` applies all reverse renders; `GameResponse` always returns display-form values
- `tests/integration/test_games_where_display.py` — template for new integration tests
- `tests/e2e/test_channel_mentions.py` — e2e test to augment (Phase 2.1)
- `tests/e2e/test_join_notification.py` — e2e test to augment (Phase 2.2)
- `tests/integration/conftest.py` — `seed_bot_freshness` autouse fixture sets `gen="1"` for projection keys
- `config.template/env.template` — optional env var template (line 383)
- `compose.e2e.yaml` — optional env var passthrough (line 150)

### External References

- #file:../research/20260530-01-mention-emoji-test-coverage-research.md — full analysis of resolution pipeline, seed helpers, complete test code, and augmentation code

### Standards References

- #file:../../.github/instructions/python.instructions.md — Python conventions
- #file:../../.github/instructions/test-driven-development.instructions.md — TDD rules; retrofitting tests for already-correct code: no stubs, no xfail, tests pass immediately
- #file:../../.github/instructions/unit-tests.instructions.md — test quality standards

## Implementation Checklist

### [x] Phase 1: Integration Tests

- [x] Task 1.1: Create `tests/integration/test_games_field_display.py` with three tests
  - Details: .copilot-tracking/planning/details/20260530-01-mention-emoji-test-coverage-details.md (Lines 11-51)

### [ ] Phase 2: Augment Existing E2E Tests

- [ ] Task 2.1: Augment `test_channel_mention_in_location_displays_as_discord_link` with description field and `embed.description` assertions
  - Details: .copilot-tracking/planning/details/20260530-01-mention-emoji-test-coverage-details.md (Lines 54-81)

- [ ] Task 2.2: Augment `test_join_notification_with_signup_instructions` with channel mention and optional emoji in signup_instructions
  - Details: .copilot-tracking/planning/details/20260530-01-mention-emoji-test-coverage-details.md (Lines 82-108)

### [ ] Phase 3: Add `DISCORD_TEST_EMOJI_NAME` Environment Variable

- [ ] Task 3.1: Add commented-out `DISCORD_TEST_EMOJI_NAME` entry to `config.template/env.template`
  - Details: .copilot-tracking/planning/details/20260530-01-mention-emoji-test-coverage-details.md (Lines 111-129)

- [ ] Task 3.2: Add `DISCORD_TEST_EMOJI_NAME: ${DISCORD_TEST_EMOJI_NAME:-}` to `compose.e2e.yaml`
  - Details: .copilot-tracking/planning/details/20260530-01-mention-emoji-test-coverage-details.md (Lines 130-143)

- [ ] Task 3.3: Add "Custom Emoji E2E Testing" section to `docs/developer/TESTING.md`
  - Details: .copilot-tracking/planning/details/20260530-01-mention-emoji-test-coverage-details.md (Lines 144-157)

## Dependencies

- Integration test infrastructure (Docker Compose via `scripts/run-integration-tests.sh`)
- E2E test infrastructure (Docker Compose via `scripts/run-e2e-tests.sh`)
- Existing integration fixtures: `create_user`, `create_guild`, `create_channel`, `create_template`, `seed_redis_cache`

## Success Criteria

- `scripts/run-integration-tests.sh tests/integration/test_games_field_display.py` passes (3 tests)
- E2E augmented tests pass for channel and user mention assertions
- E2E emoji assertions skip gracefully when `DISCORD_TEST_EMOJI_NAME` is absent
- `DISCORD_TEST_EMOJI_NAME` is documented and wired through `env.template` and `compose.e2e.yaml`
