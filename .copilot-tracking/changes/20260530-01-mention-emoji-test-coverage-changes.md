# Changes: Mention and Emoji Resolution Test Coverage

## Summary

Add integration and e2e test coverage for the user/channel/emoji mention
resolution pipeline in game text fields.

---

## Phase 1: Integration Tests

### Added

- `tests/integration/test_games_field_display.py` — three integration tests
  verifying the full resolution pipeline for custom emoji round-trip, channel
  mention in description, and user mention reverse-render

---

## Phase 2: Augment Existing E2E Tests

_(not yet implemented)_

---

## Phase 3: Add `DISCORD_TEST_EMOJI_NAME` Environment Variable

_(not yet implemented)_
