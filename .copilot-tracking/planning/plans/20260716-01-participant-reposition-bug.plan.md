---
applyTo: '.copilot-tracking/changes/20260716-01-participant-reposition-bug-changes.md'
---

<!-- markdownlint-disable-file -->

# Task Checklist: Participant Reposition Bug Fix

## Overview

Fix host-initiated repositioning of self-added/role-matched participants in the edit-game UI silently failing to persist, for every signup method, including `ROLE_BASED` (which converts a repositioned participant out of the role-priority tier), except `HOST_SELECTED_WITH_WAITLIST`.

## Objectives

- A host dragging/moving a self-added or role-matched participant in the edit-game UI has that reposition persisted to the database, for `SELF_SIGNUP` and `HOST_SELECTED` (non-waitlist) games
- Untouched self-added participants and all future Discord joiners continue to sort after any explicitly host-rearranged participants (no FCFS-breaking leapfrog, in either direction)
- `HOST_SELECTED_WITH_WAITLIST`'s existing `SELF_ADDED` → `HOST_ADDED` promotion mechanic is unchanged
- No spurious `host_added_dropout` DM fires when a merely-repositioned (never actually host-added) participant leaves, nor for a `ROLE_MATCHED` participant converted to `SELF_ADDED` by a reposition
- **`ROLE_BASED` decision (resolves the research document's open question)**: an explicitly-repositioned `ROLE_MATCHED` participant converts its `position_type` to `SELF_ADDED` with an explicit `position` matching its new display index, routed through the same sentinel/explicit-position mechanism as plain self-added repositioning — "the host has final say" overrides the role-priority tier entirely, rather than inventing a new mechanic or promoting to `HOST_ADDED`. Untouched `ROLE_MATCHED` participants keep their real priority-role-index `position` and type.

## Research Summary

### Project Files

- `services/api/services/games.py` - `_update_prefilled_participants`/`_update_participant_positions` (silently ignore self-added participants), `_add_new_mentions`, `_remove_outdated_participants`, `update_game` (call-site wiring at lines 2052-2057); also where the new `ROLE_BASED`-gated `ROLE_MATCHED`→`SELF_ADDED` conversion block is added, parallel to the existing `HOST_SELECTED_WITH_WAITLIST` promotion block (lines 1467-1479)
- `shared/models/participant.py` - `ParticipantType` enum, `GameParticipant.position`/`.position_type` columns and `server_default`
- `shared/utils/participant_sorting.py` - `sort_participants`, `partition_participants`, `resolve_role_position` (bucketed sort semantics; `ROLE_BASED` position is meaningful, not a sentinel; this file has zero diff in the final plan — the `ROLE_BASED` decision is implemented as a `position_type` mutation in `games.py`, not a sorting-logic change)
- `shared/services/leave_game.py` - `leave_game_and_notify`'s `position_type == HOST_ADDED` dropout-notification gate (must remain unaffected)
- `services/bot/handlers/join_game.py` - `_resolve_bot_role_position` (bot-side self-join default)
- `services/api/routes/games.py` - `_resolve_join_position` (API-side self-join default), `_build_host_response` (cosmetic host pseudo-participant field, not part of any sorted list)
- `frontend/src/components/EditableParticipantList.tsx` - `moveUp`/`moveDown`/`handleDrop`/`addParticipant` (mark only the literally-moved participant `isExplicitlyPositioned`, but always reindex every displayed row's `preFillPosition`)
- `frontend/src/pages/EditGame.tsx` - `handleSubmit`/`handleSaveAndArchive` (duplicated participant-payload filter that drops any non-`isExplicitlyPositioned` participant before it ever reaches the backend)
- `frontend/src/components/GameForm.tsx` - `buildParticipantList` (the `HOST_SELECTED_WITH_WAITLIST` branch already marks its whole confirmed prefix `isExplicitlyPositioned: true`, the pattern this fix generalizes to every other signup method)
- `alembic/versions/8438728f8184_replace_prefilled_position_with_.py` - reference migration shape (reversible data-migration `UPDATE` + `alter_column`, no app-code imports)
- `tests/unit/services/api/services/test_games_edit_participants.py` - `test_update_prefilled_promotes_self_added_participants` (the `HOST_SELECTED_WITH_WAITLIST` promotion test that must keep passing unchanged)
- `tests/unit/shared/services/test_leave_game_shared.py` - `test_host_added_leave_enqueues_dropout_dm_to_host` (existing dropout-notification test; regression-safety companion test added here)
- `tests/integration/test_games_crud.py` - `PUT /api/v1/games/{id}` integration test pattern (`_setup_game_context`, `_create_game_via_api`, session-cookie `httpx.AsyncClient`)

### External References

- .copilot-tracking/research/20260716-01-participant-reposition-bug-research.md - full root-cause analysis, rejected alternatives, and recommended sentinel-default approach. The research document's "Open question: `ROLE_BASED` signup method" (its Lines 77-79) is superseded by a since-made product decision, incorporated into this plan's Phase 2 (Tasks 2.4-2.6): explicit reposition converts `ROLE_MATCHED` → `SELF_ADDED` rather than leaving `ROLE_BASED` reordering unresolved

### Standards References

- .github/instructions/test-driven-development.instructions.md - "TDD for Bug Fixes" workflow (no stub, `xfail(strict=True)`/`test.failing` then remove) governs Phases 1-3; SQL migration scripts are explicitly TDD-exempt (verified via `alembic upgrade`/`downgrade`, not pytest); Phase 4's integration tests are written after the fix exists, so no RED phase there
- .github/instructions/unit-tests.instructions.md - falsifiable-assertion requirements for every new/rewritten test
- .github/instructions/python.instructions.md - Python style/typing conventions for all backend changes
- .github/instructions/reactjs.instructions.md / .github/instructions/typescript-5-es2022.instructions.md - conventions for the `EditGame.tsx`/`EditableParticipantList.tsx` changes
- .github/instructions/test-execution.instructions.md - rules for invoking `scripts/run-integration-tests.sh` (tee output, minimum timeout)

## Implementation Checklist

### [x] Phase 1: Sentinel default for self-added/role-based-fallback participants

- [x] Task 1.1: Write failing regression tests for the new sentinel default (RED)
  - Details: .copilot-tracking/planning/details/20260716-01-participant-reposition-bug-details.md (Lines 11-76)

- [x] Task 1.2: Introduce the `UNPOSITIONED_SENTINEL` constant, update model/join sites, add the Alembic migration (GREEN)
  - Details: .copilot-tracking/planning/details/20260716-01-participant-reposition-bug-details.md (Lines 77-219)

- [x] Task 1.3: Refactor, add edge-case coverage, verify migration up/down
  - Details: .copilot-tracking/planning/details/20260716-01-participant-reposition-bug-details.md (Lines 220-276)

### [x] Phase 2: Generalize backend position-update matching, including the `ROLE_BASED` decision

- [x] Task 2.1: Write failing regression test for self-added reposition persistence (RED)
  - Details: .copilot-tracking/planning/details/20260716-01-participant-reposition-bug-details.md (Lines 279-318)

- [x] Task 2.2: Match on `participant_id` across `game.participants` for position updates, keep removal scoped to `HOST_ADDED` (GREEN)
  - Details: .copilot-tracking/planning/details/20260716-01-participant-reposition-bug-details.md (Lines 319-391)

- [x] Task 2.3: Refactor, add edge-case coverage, confirm waitlist promotion path untouched
  - Details: .copilot-tracking/planning/details/20260716-01-participant-reposition-bug-details.md (Lines 392-420)

- [x] Task 2.4: Write failing regression tests for `ROLE_BASED` reposition-converts-to-`SELF_ADDED` (RED)
  - Details: .copilot-tracking/planning/details/20260716-01-participant-reposition-bug-details.md (Lines 421-487)

- [x] Task 2.5: Convert repositioned `ROLE_MATCHED` participants to `SELF_ADDED` in `_update_prefilled_participants` (GREEN)
  - Details: .copilot-tracking/planning/details/20260716-01-participant-reposition-bug-details.md (Lines 488-579)

- [x] Task 2.6: Refactor, add edge-case coverage, confirm mixed-bucket sort/partition and waitlist path untouched
  - Details: .copilot-tracking/planning/details/20260716-01-participant-reposition-bug-details.md (Lines 580-628)

### [x] Phase 3: Frontend disturbed-prefix payload extension

- [x] Task 3.1: Write failing regression tests for the disturbed-prefix payload (RED)
  - Details: .copilot-tracking/planning/details/20260716-01-participant-reposition-bug-details.md (Lines 631-682)

- [x] Task 3.2: Extract shared `buildParticipantsPayload` helper and use it in both submit paths (GREEN)
  - Details: .copilot-tracking/planning/details/20260716-01-participant-reposition-bug-details.md (Lines 683-754)

- [x] Task 3.3: Refactor, add edge-case coverage, confirm waitlist payload construction unchanged and `ROLE_MATCHED` reorderable identically to `SELF_ADDED`
  - Details: .copilot-tracking/planning/details/20260716-01-participant-reposition-bug-details.md (Lines 755-809)

### [x] Phase 4: End-to-end verification

- [x] Task 4.1: Add integration tests proving reposition (including `ROLE_BASED` conversion) persists across reload
  - Details: .copilot-tracking/planning/details/20260716-01-participant-reposition-bug-details.md (Lines 812-858)

- [x] Task 4.2: Add leave-game regression-safety tests for repositioned/converted participants
  - Details: .copilot-tracking/planning/details/20260716-01-participant-reposition-bug-details.md (Lines 859-908)

- [x] Task 4.3: Full-suite verification gate
  - Details: .copilot-tracking/planning/details/20260716-01-participant-reposition-bug-details.md (Lines 909-949)

## Dependencies

- `uv run pytest tests/unit` (never `pytest --testmon` manually per `CLAUDE.md`)
- `uv run mypy shared/ services/`
- `cd frontend && npm run build` and `cd frontend && npm run test`
- `uv run alembic upgrade head` / `uv run alembic downgrade -1` for the new migration
- `scripts/run-integration-tests.sh tests/integration/test_games_crud.py |& tee output-integration.txt`
- No new schema columns or `ParticipantType` values; no changes to `HOST_SELECTED_WITH_WAITLIST`'s promotion logic

## Success Criteria

- Dragging/moving a self-joined participant in the edit UI persists across save/reload for `SELF_SIGNUP` and `HOST_SELECTED`
- A subsequent new Discord joiner still lands after any host-rearranged participants (sentinel default keeps future joins sorting last)
- No `host_added_dropout` DM fires when a merely-repositioned (never promoted to `HOST_ADDED`) participant leaves, nor for a `ROLE_MATCHED` participant converted to `SELF_ADDED` by a reposition
- `HOST_SELECTED_WITH_WAITLIST`'s promotion behavior (`test_update_prefilled_promotes_self_added_participants` and the waitlist integration/unit suite) is unchanged
- `ROLE_BASED` reordering is implemented: an explicitly-repositioned `ROLE_MATCHED` participant converts to `SELF_ADDED` with an explicit `position`; untouched `ROLE_MATCHED` participants keep their type and priority-index `position`; the mixed-bucket sort order is correct and tested; `shared/utils/participant_sorting.py` has zero diff (the decision is implemented as a `position_type` mutation in `services/api/services/games.py`, not a sorting-logic change)
- `uv run pytest tests/unit`, `uv run mypy shared/ services/`, `cd frontend && npm run build`, `cd frontend && npm run test`, and the targeted integration test all pass at the end of Phase 4
