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
- services/api/services/games.py - `_update_prefilled_participants` now calls `_update_participant_positions(game.participants, ...)` instead of the `HOST_ADDED`-only `current_participants`, so a position write for any participant (`SELF_ADDED`, `ROLE_MATCHED`) matched by `participant_id` actually persists; `_remove_outdated_participants` remains scoped to the `HOST_ADDED`-only query, unchanged (Task 2.2); added a `ROLE_BASED`-gated block, parallel to the existing `HOST_SELECTED_WITH_WAITLIST` promotion block, that converts any explicitly-repositioned `ROLE_MATCHED` participant to `SELF_ADDED` with its new explicit `position` (Task 2.5)
- tests/unit/services/api/services/test_games_edit_participants.py - added `test_update_prefilled_persists_self_added_reposition` (xfail RED then GREEN, Tasks 2.1/2.2), `test_update_prefilled_persists_role_matched_reposition_without_converting` and `test_update_prefilled_leaves_untouched_self_added_participant_alone` (Task 2.3 edge cases), `test_update_prefilled_converts_role_matched_to_self_added_on_reposition` and `test_update_prefilled_leaves_untouched_role_matched_participant_alone` (xfail RED then GREEN, Tasks 2.4/2.5), and `test_update_prefilled_role_based_game_never_promotes_to_host_added` (Task 2.6 edge case guarding the two signup-method-gated blocks' mutual exclusivity)
- tests/unit/shared/utils/test_participant_sorting.py - added `TestSortParticipants.test_remaining_role_matched_sorts_before_converted_self_added`, a no-xfail test (already-correct code) locking in that a mixed bucket of one remaining `ROLE_MATCHED` and one converted `SELF_ADDED` participant sorts `ROLE_MATCHED` first regardless of numeric `position` (Task 2.6)

**Known, intentional consequence of Task 2.5** (documented per the plan): because `sort_participants`'s key is `(position_type, position, joined_at)` and `SELF_ADDED` (24000) always sorts after every remaining `ROLE_MATCHED` (16000) entry, dragging a `ROLE_MATCHED` participant to a spot visually above another still-unconverted `ROLE_MATCHED` participant will still persist with the dragged participant sorting below every remaining `ROLE_MATCHED` participant. This is intended: an explicit reposition fully exits the role-priority tier, it is not a same-tier nudge. Reordering two participants while both keep their role-priority tier is unsupported (no such UI action exists) and out of scope.

- frontend/src/pages/EditGame.tsx - extracted a module-level `buildParticipantsPayload` helper (the "disturbed prefix" rule: include every participant that is either explicitly positioned or displayed at/above the highest explicitly-positioned index) and replaced the duplicated `.filter(...).map(...)` blocks in both `handleSubmit` and `handleSaveAndArchive` with calls to it, so a host-repositioned self-added/role-matched participant's move actually reaches the backend from either save path
- frontend/src/pages/**tests**/EditGame.test.tsx - added `it.fails` regression tests for the disturbed-prefix payload (RED phase, Task 3.1: `includes the full disturbed prefix...`/`excludes untouched participants below the highest explicitly-positioned index`), removed the `.fails` markers after implementing the fix (GREEN, Task 3.2), and added edge-case coverage (Task 3.3): two non-contiguous explicit moves, the `addParticipant` "pin the whole prefix" side effect, and a `ROLE_MATCHED` participant behaving identically to `SELF_ADDED` when dragged in a `ROLE_BASED` game

**Side effect noted per the plan**: consolidating both save paths into one helper also fixes a pre-existing inconsistency — `handleSaveAndArchive`'s duplicated block previously used `p.mention.trim()` for the temp-id branch instead of `p.resolvedMention ?? p.mention.trim()` (which `handleSubmit` already used), so a disambiguated-but-unsaved mention typed via "Save and Archive" now resolves the same way it already did via "Save Changes".

- tests/integration/test_games_crud.py - extended `_setup_game_context` with an optional `allowed_signup_methods` param and `_create_game_via_api` with an optional `signup_method` param (both default to prior behavior when omitted); added `test_update_game_persists_self_added_participant_reposition` and `test_update_game_persists_role_matched_reposition_as_self_added` (Task 4.1), proving the full migration/backend/frontend-contract stack persists a reposition (and the `ROLE_BASED` conversion) through the real API and database
- tests/unit/shared/services/test_leave_game_shared.py - added `test_repositioned_self_added_leave_does_not_enqueue_dropout_dm` and `test_converted_role_matched_leave_does_not_enqueue_dropout_dm` (Task 4.2, already-correct-code regression guards, no `xfail`), confirming `leave_game_and_notify`'s `host_added_dropout` gate never misfires for a merely-repositioned or role-converted `SELF_ADDED` participant

### Removed

## Release Summary

**Total Files Affected**: 17

### Files Created (2)

- alembic/versions/77f802eecfc5_backfill_self_added_position_sentinel.py - reversible data migration backfilling the old `0` default to the new `32767` sentinel for non-`HOST_ADDED` rows
- .copilot-tracking/changes/20260716-01-participant-reposition-bug-changes.md - this changes-tracking file

### Files Modified (15)

- shared/models/participant.py - `UNPOSITIONED_SENTINEL` constant; `position` column's `server_default` changed from `0` to the sentinel
- services/api/routes/games.py - `_resolve_join_position`/`_build_host_response` use the sentinel instead of hardcoded `0`
- services/bot/handlers/join_game.py - `_resolve_bot_role_position` uses the sentinel instead of hardcoded `0`
- shared/utils/participant_sorting.py - `resolve_role_position`'s no-match fallback uses the sentinel instead of hardcoded `0` (its only change; `sort_participants`/`partition_participants` have zero diff)
- services/api/services/games.py - `_update_prefilled_participants` matches position updates by `participant_id` across `game.participants` (any `position_type`), not just `HOST_ADDED`; adds the `ROLE_BASED`-gated `ROLE_MATCHED`→`SELF_ADDED` conversion block
- frontend/src/pages/EditGame.tsx - shared `buildParticipantsPayload` helper implementing the disturbed-prefix rule, used by both `handleSubmit` and `handleSaveAndArchive`
- tests/unit/services/api/routes/test_games_helpers.py - sentinel-value test rewrites
- tests/unit/shared/utils/test_participant_sorting.py - sentinel-value test rewrites; new sentinel-guard, mixed-bucket-sort, and `ROLE_MATCHED`-position edge-case tests
- tests/unit/services/bot/handlers/test_join_game.py - sentinel-value test rewrites
- tests/unit/api/services/test_games.py - new `HOST_ADDED`-unaffected-by-sentinel edge-case test
- tests/unit/services/api/services/test_games_edit_participants.py - new reposition-persistence and `ROLE_BASED`-conversion tests, plus edge-case coverage
- frontend/src/pages/**tests**/EditGame.test.tsx - new disturbed-prefix payload tests and edge-case coverage
- tests/integration/test_games_crud.py - helper extensions plus two new end-to-end reposition-persistence tests
- tests/unit/shared/services/test_leave_game_shared.py - two new dropout-notification regression guards
- .copilot-tracking/planning/plans/20260716-01-participant-reposition-bug.plan.md - all phases/tasks marked complete

### Files Removed (0)

None.

### Dependencies & Infrastructure

- **New Dependencies**: None
- **Updated Dependencies**: None
- **Infrastructure Changes**: None
- **Configuration Updates**: None (one new Alembic migration, applied/reversed/reapplied and verified during Phase 1)

### Deployment Notes

Run `alembic upgrade head` as part of deployment to apply the `77f802eecfc5` migration before the new sentinel-dependent code paths go live. No other manual steps required. The `ROLE_BASED` decision documented in this plan (explicit reposition converts `ROLE_MATCHED` → `SELF_ADDED`, "the host has final say") is a behavior change worth calling out to hosts of `ROLE_BASED` games, though it requires no configuration change.
