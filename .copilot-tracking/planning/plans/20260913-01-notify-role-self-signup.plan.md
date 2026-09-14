---
applyTo: '.copilot-tracking/changes/20260913-01-notify-role-self-signup-changes.md'
---

<!-- markdownlint-disable-file -->

# Task Checklist: Suppress Notify-Role Ping for HOST_SELECTED Games

## Overview

Suppress the `notify_role_ids` Discord role mention/ping in game announcements when a game's `signup_method` is `HOST_SELECTED` (no user can self-join, so pinging is pointless), while leaving the ping unchanged for every other `signup_method`.

## Objectives

- `format_game_announcement` omits the `notify_role_ids` role mention(s) from `content` whenever `signup_method == SignupMethod.HOST_SELECTED`, while still including the host mention and confirmed-participant mentions unchanged.
- `SELF_SIGNUP`, `HOST_SELECTED_WITH_WAITLIST`, and `ROLE_BASED` games continue to ping `notify_role_ids` exactly as today (regression-proofed by tests).
- No database migration, Pydantic schema field, or config/guild toggle is introduced — this is a pure conditional in the single existing formatting choke point.
- The behavior is proven end-to-end against a real Discord message (not just the unit-tested formatter function), including across a `signup_method` edit transition, since `tests/e2e/test_signup_methods.py` already fetches real posted/updated messages for signup-method scenarios.

## Research Summary

### Project Files

- `services/bot/formatters/game_message.py` - `format_game_announcement` (lines 684-807); the role-mention loop to gate is at lines 791-797; imports `GameStatus` from `shared.models` at line 44 (add `SignupMethod` alongside it).
- `services/bot/events/handlers.py` - `_create_game_announcement` (lines 1469-1518) is the single call site that feeds `notify_role_ids` (line 1507) and `signup_method` (line 1504) into `format_game_announcement`; reached by every current Discord-announcement sender and message-refresh path. No change needed here — the gate belongs entirely inside `format_game_announcement`.
- `tests/unit/services/bot/formatters/test_game_message.py` - `TestFormatGameAnnouncement` (class at line 1189) already contains `test_format_game_announcement_with_everyone_role` (line 1679), `test_format_game_announcement_with_regular_roles` (line 1723), and `test_format_game_announcement_with_mixed_roles` (line 1768), all currently passing `signup_method="SELF_SIGNUP"` — the file/class to extend with the new `HOST_SELECTED` suppression case and the multi-signup-method regression case.
- `shared/models/signup_method.py` - `SignupMethod` `StrEnum` (lines 27-33): `SELF_SIGNUP`, `HOST_SELECTED`, `HOST_SELECTED_WITH_WAITLIST`, `ROLE_BASED`. `shared/models/__init__.py` re-exports `SignupMethod` (line 36/55) alongside `GameStatus`, matching the existing single-line import style used in `game_message.py`.
- `services/bot/views/game_view.py` - existing precedent for comparing a `str` `signup_method` parameter against `SignupMethod.HOST_SELECTED.value` (lines 82, 109-111) — the pattern this change follows.
- `tests/e2e/test_signup_methods.py` - already has `test_host_selected_disables_join_button` (line 144), `test_self_signup_enables_join_button` (line 58), `test_edit_game_signup_method_self_to_host` (line 321), and `test_edit_game_signup_method_host_to_self` (line 431), each of which already creates a real game via `POST /api/v1/games`, waits for the real Discord message, and (for the edit tests) edits `signup_method` and waits for the real message update — the natural place to add `notify_role_ids` mention assertions rather than a new file.
- `services/api/routes/games.py` - `notify_role_ids: Annotated[str | None, Form()]` is an accepted JSON-encoded field on both `POST /api/v1/games` (line 754) and `PUT /api/v1/games/{game_id}` (line 752); omitting it on the `PUT` update (as the existing edit tests already do) leaves the previously-set value unchanged, so a test only needs to set it once, at creation.
- `tests/e2e/test_role_based_signup.py` (lines 54-62) - precedent for a session-scoped fixture reading a real Discord test role ID from an env var (`DISCORD_TEST_ROLE_A_ID`, documented in `docs/developer/TESTING.md` "Role-Based Signup E2E Test Roles") — reuse this existing required env var/role rather than introducing a new one.

### External References

- .copilot-tracking/research/20260913-01-notify-role-self-signup-research.md - full research findings, resolved open questions, and recommended approach for this feature.

### Standards References

- .github/instructions/test-driven-development.instructions.md - "TDD for Bug Fixes" / enhanced-existing-code workflow (xfail-proven RED phase, no stub, since `format_game_announcement` already exists) governs Task 1.1/1.2; "Writing Tests for Already-Correct Code" governs the Task 1.3 regression additions for the three unaffected signup methods.
- .github/instructions/python.instructions.md - type hints, docstrings, import ordering, Ruff conventions for the production-code edit.
- .github/instructions/unit-tests.instructions.md - falsifiable assertions, negative-assertion sibling-path requirement (the suppression test's "no role mention" claim is proven by a sibling test where the same `notify_role_ids` DOES ping).

## Implementation Checklist

### [ ] Phase 1: Suppress `notify_role_ids` ping for `HOST_SELECTED` games

- [ ] Task 1.1: RED - Add a failing (xfail) test asserting no role mention for `HOST_SELECTED` games
  - Details: .copilot-tracking/planning/details/20260913-01-notify-role-self-signup-details.md (Lines 15-38)

- [ ] Task 1.2: GREEN - Gate the role-mention loop on `signup_method` and remove the xfail marker
  - Details: .copilot-tracking/planning/details/20260913-01-notify-role-self-signup-details.md (Lines 40-62)

- [ ] Task 1.3: Add regression coverage confirming the other three signup methods still ping
  - Details: .copilot-tracking/planning/details/20260913-01-notify-role-self-signup-details.md (Lines 64-87)

- [ ] Task 1.4: Add e2e coverage proving the real Discord message omits/includes the ping, including across an edit transition
  - Details: .copilot-tracking/planning/details/20260913-01-notify-role-self-signup-details.md (Lines 188-247)

## Dependencies

- None on the separate, in-flight `20260911-01-game-posting-schedule-cleanup` sender-unification work (per research: orthogonal, safe to land independently).
- `uv run pytest tests/unit/services/bot/formatters/test_game_message.py` and `uv run pytest tests/unit` for verification.
- `uv run mypy shared/ services/` for type checking (production-code file touched).
- Task 1.4 requires the full e2e stack (`scripts/run-e2e-tests.sh`, per `.github/instructions/test-execution.instructions.md`) and the `DISCORD_TEST_ROLE_A_ID` test-role env var already required by `tests/e2e/test_role_based_signup.py`; run scoped to `tests/e2e/test_signup_methods.py` rather than the full e2e suite.

## Success Criteria

- A `HOST_SELECTED` game with a non-empty `notify_role_ids` produces `content` containing the host/participant mentions but never the role mention(s).
- `SELF_SIGNUP`, `HOST_SELECTED_WITH_WAITLIST`, and `ROLE_BASED` games continue to ping `notify_role_ids` exactly as today (no regression), verified by explicit tests for each.
- `uv run pytest tests/unit` passes with zero failures/errors and no added `xfail` markers remaining.
- `uv run mypy shared/ services/` is clean.
- No new DB migration, schema field, or config toggle exists anywhere in the diff.
- A real Discord message for a `HOST_SELECTED` game with `notify_role_ids` set does not contain the role mention, and the same scenario for `SELF_SIGNUP` does — proven by `tests/e2e/test_signup_methods.py`.
- Editing a game's `signup_method` from `HOST_SELECTED` to `SELF_SIGNUP` causes the role mention to newly appear on the real, updated Discord message (and the reverse edit causes it to disappear) — proven end-to-end, confirming the resolved "ping on becoming joinable" behavior.
