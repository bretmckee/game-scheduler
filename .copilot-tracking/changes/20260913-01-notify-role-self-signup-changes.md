<!-- markdownlint-disable-file -->

# Release Changes: Suppress Notify-Role Ping for HOST_SELECTED Games

**Related Plan**: 20260913-01-notify-role-self-signup.plan.md
**Implementation Date**: 2026-09-14

## Summary

Suppresses the `notify_role_ids` Discord role mention/ping in game announcements when a game's `signup_method` is `HOST_SELECTED` (no user can self-join, so pinging is pointless), while leaving the ping unchanged for every other `signup_method`.

## Changes

### Added

- tests/unit/services/bot/formatters/test_game_message.py - Added `test_format_game_announcement_host_selected_suppresses_role_mention` (Task 1.1/1.2 RED/GREEN), `test_format_game_announcement_host_selected_with_waitlist_still_pings`, and `test_format_game_announcement_role_based_still_pings` (Task 1.3 regression coverage)
- tests/e2e/test_signup_methods.py - Added session-scoped `notify_role_id` fixture (Task 1.4)

### Modified

- services/bot/formatters/game_message.py - Imported `SignupMethod`; gated the role-mention loop on `signup_method != SignupMethod.HOST_SELECTED.value` (Task 1.2)
- tests/e2e/test_signup_methods.py - Extended `test_self_signup_enables_join_button`, `test_host_selected_disables_join_button`, `test_edit_game_signup_method_self_to_host`, and `test_edit_game_signup_method_host_to_self` with `notify_role_ids` mention assertions against real Discord messages (Task 1.4)

### Removed

## Release Summary

**Total Files Affected**: 3

### Files Created (0)

None

### Files Modified (3)

- services/bot/formatters/game_message.py
- tests/unit/services/bot/formatters/test_game_message.py
- tests/e2e/test_signup_methods.py

### Files Removed (0)

None

### Dependencies & Infrastructure

- **New Dependencies**: None
- **Updated Dependencies**: None
- **Infrastructure Changes**: None
- **Configuration Updates**: None

### Testing Requirements

- `uv run pytest tests/unit/services/bot/formatters/test_game_message.py -k host_selected_suppresses_role_mention -v` — RED confirmed `1 xfailed` before Task 1.2, GREEN confirmed `1 passed` after
- `uv run pytest tests/unit` — 2577 passed, no xfail markers remaining
- `uv run mypy shared/ services/` — clean
- `uv run ruff check` on all touched files — clean
- `SKIP_STARTUP=1 ./scripts/run-e2e-tests.sh tests/e2e/test_signup_methods.py` — Task 1.4 gate, run against the real Discord test guild; 6 passed (final clean run, environment torn down after)

### Deviation from the plan/details doc (Task 1.4)

The details doc assumed `POST /api/v1/games` accepts a `notify_role_ids` form
field. It does not — `GameCreateRequest` has no such field, and
`_build_game_session` always copies `notify_role_ids` from the template at
creation time (confirmed in the research doc's own "no existing coupling"
finding, which this detail contradicted). Only `PUT /api/v1/games/{id}`
accepts `notify_role_ids`. The first e2e run against the as-written details
(passing `notify_role_ids` in the create `game_data`) proved this: the field
was silently dropped by FastAPI's Form binding, and 3 of 4 extended tests
failed because the "presence" assertions found only the host mention.

Fix applied: each extended test now sets `notify_role_ids` via a `PUT` (after
creation for the two single-state tests; after the initial creation but
before the signup-method-changing `PUT` for the two edit-transition tests),
then waits for the resulting Discord message edit before asserting. For the
two suppression checks (`HOST_SELECTED`, where the message content is
expected to stay textually identical since the ping is suppressed), the wait
predicate is `msg.edited_at is not None` rather than a content diff, since
there is no textual change to poll for — this still proves the edit landed
before checking content, so the assertion is against the post-edit state
rather than a state that never had a role configured at all.
