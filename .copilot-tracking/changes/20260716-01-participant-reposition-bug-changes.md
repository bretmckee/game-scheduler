<!-- markdownlint-disable-file -->

# Release Changes: Participant Reposition Bug Fix

**Related Plan**: .copilot-tracking/planning/plans/20260716-01-participant-reposition-bug.plan.md
**Implementation Date**: 2026-07-16

## Summary

Fixes host-initiated repositioning of self-added/role-matched participants in the edit-game UI silently failing to persist, for every signup method except `HOST_SELECTED_WITH_WAITLIST`.

## Changes

### Added

- alembic/versions/77f802eecfc5_backfill_self_added_position_sentinel.py - reversible data migration backfilling non-`HOST_ADDED` rows still at the old default (`0`) to the new sentinel (`32767`), and reversing on downgrade

### Modified

- tests/unit/services/api/routes/test_games_helpers.py - added `TestResolveJoinPosition.test_returns_self_added_with_sentinel_when_no_template`, an `xfail(strict=True)` regression test asserting `_resolve_join_position` returns `(SELF_ADDED, 32767)` when the game has no template (RED phase, Task 1.1); then in Task 1.2, rewrote `test_returns_self_added_when_no_template`/`test_returns_self_added_when_template_has_no_priority_roles`/`TestBuildGameResponseHelpers.test_build_host_response_with_display_data` to assert `32767` and removed the now-duplicate RED-phase xfail test (folded its correct assertion/xfail-removal into the pre-existing `test_returns_self_added_when_no_template`)
- tests/unit/shared/utils/test_participant_sorting.py - added `TestResolveRolePosition.test_no_matching_role_returns_self_added_with_sentinel`, an `xfail(strict=True)` regression test asserting `resolve_role_position` returns `(SELF_ADDED, 32767)` on no role match (RED phase, Task 1.1); then in Task 1.2, rewrote `test_no_matching_role_returns_self_added`/`test_empty_priority_list_returns_self_added` to assert `32767` and removed the now-duplicate RED-phase xfail test
- tests/unit/services/bot/handlers/test_join_game.py - rewrote `TestResolveBotRolePosition.test_no_priority_roles_returns_self_added`/`test_no_template_returns_self_added`/`test_non_member_interaction_returns_self_added`/`test_member_with_no_matching_role_returns_self_added` to assert `(SELF_ADDED, 32767)` (Task 1.2)
- shared/models/participant.py - added `UNPOSITIONED_SENTINEL: Final[int] = 32767` constant; changed `GameParticipant.position`'s `server_default` from `text("0")` to `text(str(UNPOSITIONED_SENTINEL))`; added explanatory comment distinguishing the sentinel from `ROLE_MATCHED`'s meaningful priority-index `position` (Task 1.2)
- services/api/routes/games.py - `_resolve_join_position`'s no-priority-roles branch and `_build_host_response`'s cosmetic host pseudo-participant now use `UNPOSITIONED_SENTINEL` instead of hardcoded `0` (Task 1.2)
- services/bot/handlers/join_game.py - `_resolve_bot_role_position`'s no-priority-roles/non-Member branch now uses `UNPOSITIONED_SENTINEL` instead of hardcoded `0` (Task 1.2)
- shared/utils/participant_sorting.py - `resolve_role_position`'s no-match fallback now returns `UNPOSITIONED_SENTINEL` instead of hardcoded `0`; docstring updated (Task 1.2; this is the fourth hardcoded-`0` site found during Task 1.1 verification, beyond the three the research document listed)
- tests/unit/shared/utils/test_participant_sorting.py - added `TestResolveRolePosition.test_role_matched_position_is_never_the_sentinel`, proving the sentinel change is scoped to the "no match"/`SELF_ADDED` branch only (Task 1.3)
- tests/unit/api/services/test_games.py - added `TestAddNewMentions.test_host_added_participant_uses_caller_supplied_position`, proving a newly added `HOST_ADDED` participant's `position` is the caller-supplied value, not `UNPOSITIONED_SENTINEL` (Task 1.3)

### Removed

## Release Summary

_(populated after all phases complete)_
