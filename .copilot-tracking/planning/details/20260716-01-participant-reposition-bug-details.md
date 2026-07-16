<!-- markdownlint-disable-file -->

# Task Details: Participant Reposition Bug Fix

## Research Reference

**Source Research**: .copilot-tracking/research/20260716-01-participant-reposition-bug-research.md

## Phase 1: Sentinel default for self-added/role-based-fallback participants

### Task 1.1: Write failing regression tests for the new sentinel default (RED)

This is a bug fix (the buggy default already exists), so there is no stub to
create — write regression tests asserting the correct (post-fix) behavior and
mark them `xfail(strict=True)` per the "TDD for Bug Fixes" workflow.

Direct codebase verification (beyond the research document, which enumerates
only three call sites) found a **fourth** location hardcoding the same `0`
default: `shared/utils/participant_sorting.py`'s `resolve_role_position`
(lines 101-120) is the shared function both `_resolve_join_position`
(`services/api/routes/games.py:171`, via `_resolve_role_position_for_user`)
and `_resolve_bot_role_position` (`services/bot/handlers/join_game.py:204`)
delegate to once priority roles exist; its own "no match" fallback (line
120, `return (ParticipantType.SELF_ADDED, 0)`) is functionally identical to
the three sites the research document lists and must be fixed identically —
otherwise a user joining a game with priority roles configured, who matches
none of them, would still land on the old `0` default while every other
self-added path uses the new sentinel, reintroducing the exact leapfrog bug
for that one case. This is a straightforward extension of the research's
already-vetted fix, not a new design decision, so no additional research
round-trip is needed.

Add two new tests proving the two distinct hardcoded-literal patterns need
to change (the "no priority roles configured at all" shortcut, and the
"priority roles configured but no match" fallback):

1. `tests/unit/services/api/routes/test_games_helpers.py`'s
   `TestResolveJoinPosition` class — a new test
   `test_returns_self_added_with_sentinel_when_no_template` asserting
   `_resolve_join_position(game_without_template, "discord-123", MagicMock())`
   returns `(ParticipantType.SELF_ADDED, 32767)` (mirrors the existing
   `test_returns_self_added_when_no_template` at lines 919-927, which will be
   rewritten in Task 1.2, not duplicated — this new test exists only to
   provide the RED-phase proof; do not leave both the old and new assertions
   coexisting after Task 1.2).
2. `tests/unit/shared/utils/test_participant_sorting.py`'s
   `TestResolveRolePosition` class — a new test
   `test_no_matching_role_returns_self_added_with_sentinel` asserting
   `resolve_role_position(["role_x"], ["role_a", "role_b"])` returns
   `(ParticipantType.SELF_ADDED, 32767)` (mirrors the existing
   `test_no_matching_role_returns_self_added` at lines 671-674, likewise to
   be rewritten, not duplicated, in Task 1.2).

Mark both new tests
`@pytest.mark.xfail(strict=True, reason="Bug: self-added join paths default position to 0, the smallest possible value, causing future joiners and untouched self-added participants to leapfrog a host's explicit reposition")`.
Run both affected test files with `-v` and confirm both new tests show
`xfailed` before proceeding.

- **Files**:
  - tests/unit/services/api/routes/test_games_helpers.py - add the `test_returns_self_added_with_sentinel_when_no_template` xfail test to `TestResolveJoinPosition`
  - tests/unit/shared/utils/test_participant_sorting.py - add the `test_no_matching_role_returns_self_added_with_sentinel` xfail test to `TestResolveRolePosition`
- **Success**:
  - Both new tests have real assertions (not `pytest.raises(NotImplementedError)`)
  - Both test files show the new test as `xfailed` when run with `-v`; all pre-existing tests in these files still pass unchanged (including the soon-to-be-rewritten `0`-asserting tests, which are still correct descriptions of _current_ behavior at this point)
- **Research References**:
  - .copilot-tracking/research/20260716-01-participant-reposition-bug-research.md (Lines 30-31) - "All self-added join paths default new participants to `(ParticipantType.SELF_ADDED, 0)`"
  - .copilot-tracking/research/20260716-01-participant-reposition-bug-research.md (Lines 64) - why `0` (the smallest possible value) is the root cause of the leapfrog behavior
  - .copilot-tracking/research/20260716-01-participant-reposition-bug-research.md (Lines 66-73) - "The fix that resolves all raised objections" (the sentinel-swap rationale these tests encode)
  - Source: services/api/routes/games.py (Lines 162-176, 355-368) - `_resolve_join_position` and `_resolve_role_position_for_user` current implementation
  - Source: services/bot/handlers/join_game.py (Lines 177-204) - `_resolve_bot_role_position` current implementation, delegates to `resolve_role_position`
  - Source: shared/utils/participant_sorting.py (Lines 101-120) - `resolve_role_position`'s own `(SELF_ADDED, 0)` fallback, the fourth hardcoded site found via direct verification
  - Source: tests/unit/services/api/routes/test_games_helpers.py (Lines 917-938) - `TestResolveJoinPosition`'s two pre-existing `0`-asserting tests to be rewritten in Task 1.2
  - Source: tests/unit/shared/utils/test_participant_sorting.py (Lines 658-679) - `TestResolveRolePosition`'s two pre-existing `0`-asserting tests to be rewritten in Task 1.2
- **Dependencies**:
  - None (first task of the plan)

### Task 1.2: Introduce the `UNPOSITIONED_SENTINEL` constant, update model/join sites, add the Alembic migration (GREEN)

Add a module-level constant to `shared/models/participant.py`, following the
`DEFAULT_MAX_PLAYERS` precedent in `shared/utils/games.py`:

```python
from typing import Final

UNPOSITIONED_SENTINEL: Final[int] = 32767  # SmallInteger max; see ParticipantType docstring
```

Update `GameParticipant.position`'s `server_default` from `text("0")` to
`text(str(UNPOSITIONED_SENTINEL))` (currently `shared/models/participant.py`
line 80). Add a short comment above the column explaining that this is a
maximum-value sentinel for unpositioned self-added/role-based-fallback
participants, not a meaningful priority value (unlike `ROLE_MATCHED`'s
`position`, which is a real priority-role index — see
`resolve_role_position`).

Update all **four** self-added/role-based-fallback hardcoded-`0` sites to
return `UNPOSITIONED_SENTINEL` instead (three from the research document,
plus the shared fallback found in Task 1.1's verification):

- `services/api/routes/games.py:170` (`_resolve_join_position`'s
  no-priority-roles branch) — `return ParticipantType.SELF_ADDED,
UNPOSITIONED_SENTINEL`
- `services/api/routes/games.py:1060` (`_build_host_response`'s synthetic
  host pseudo-participant) — `position=UNPOSITIONED_SENTINEL`. Note in a
  code comment that this field is cosmetic only: `_build_host_response`
  builds a standalone `ParticipantResponse` that is never merged into
  `partition_participants`'s sorted lists (see `_build_game_response`,
  `services/api/routes/games.py:1097-1132`), so this change has no sorting
  effect — it is updated purely for consistency with the new sentinel.
- `services/bot/handlers/join_game.py:197` (`_resolve_bot_role_position`'s
  no-priority-roles/non-Member branch) — `return (ParticipantType.SELF_ADDED,
UNPOSITIONED_SENTINEL)`
- `shared/utils/participant_sorting.py:120` (`resolve_role_position`'s
  no-match fallback) — `return (ParticipantType.SELF_ADDED,
UNPOSITIONED_SENTINEL)`

Import `UNPOSITIONED_SENTINEL` from `shared.models.participant` at each call
site (`services/api/routes/games.py` and `services/bot/handlers/join_game.py`
already import `ParticipantType` from that module;
`shared/utils/participant_sorting.py` already imports `ParticipantType` from
it too — add `UNPOSITIONED_SENTINEL` to that same import).

Rewrite every pre-existing test that asserts the old `(SELF_ADDED, 0)` value
for these four paths — per the phase-isolation "ordering rule," these are
callers of the old default and must be updated in this same task, not
deferred:

- `tests/unit/services/api/routes/test_games_helpers.py`:
  - `TestResolveJoinPosition.test_returns_self_added_when_no_template` (lines 919-927) → assert `position == 32767`
  - `TestResolveJoinPosition.test_returns_self_added_when_template_has_no_priority_roles` (lines 930-938) → assert `position == 32767`
  - `TestBuildHostResponse.test_build_host_response_with_display_data` (lines 403-416) → assert `response.position == 32767`
- `tests/unit/services/bot/handlers/test_join_game.py`'s `TestResolveBotRolePosition`:
  - `test_no_priority_roles_returns_self_added` (lines 56-61) → assert `(ParticipantType.SELF_ADDED, 32767)`
  - `test_no_template_returns_self_added` (lines 64-70) → assert `(ParticipantType.SELF_ADDED, 32767)`
  - `test_non_member_interaction_returns_self_added` (lines 73-79) → assert `(ParticipantType.SELF_ADDED, 32767)`
  - `test_member_with_no_matching_role_returns_self_added` (lines 131-150) → assert `(ParticipantType.SELF_ADDED, 32767)` (this one exercises `resolve_role_position`'s fallback specifically, not the bot's own shortcut)
- `tests/unit/shared/utils/test_participant_sorting.py`'s `TestResolveRolePosition`:
  - `test_no_matching_role_returns_self_added` (lines 671-674) → assert `(ParticipantType.SELF_ADDED, 32767)`
  - `test_empty_priority_list_returns_self_added` (lines 676-679) → assert `(ParticipantType.SELF_ADDED, 32767)`

Do **not** change `TestResolveBotRolePosition.test_member_with_matching_role_returns_self_added`/
`test_everyone_role_excluded_from_user_roles` or `TestResolveRolePosition`'s
`test_highest_priority_role_returns_role_matched_index_0`/
`test_second_priority_role_returns_role_matched_index_1`/
`test_multiple_matching_roles_first_match_wins` — these all assert
`ROLE_MATCHED` results, whose `position` is a real priority-role index, not
the sentinel, and must remain untouched.

Remove the `xfail` markers added in Task 1.1 (do not modify those two
assertions; delete the now-duplicate old assertions they were mirroring as
part of the rewrites above rather than leaving both versions in the file).

Create a new Alembic migration (revision-hash-prefixed filename, following
`alembic/versions/8438728f8184_replace_prefilled_position_with_.py`'s shape):

```python
"""backfill_self_added_position_sentinel

Revision ID: <generated>
Revises: <current head>
Create Date: 2026-07-16 ...

"""

from collections.abc import Sequence

from alembic import op

revision: str = "<generated>"
down_revision: str | None = "<current head>"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Backfill non-HOST_ADDED rows still at the old default (0) to the new sentinel (32767)."""
    op.execute(
        "UPDATE game_participants SET position = 32767 "
        "WHERE position_type != 8000 AND position = 0"
    )


def downgrade() -> None:
    """Restore the old default (0) for non-HOST_ADDED rows at the sentinel (32767)."""
    op.execute(
        "UPDATE game_participants SET position = 0 "
        "WHERE position_type != 8000 AND position = 32767"
    )
```

Do not import `shared.models.participant.UNPOSITIONED_SENTINEL` or
`ParticipantType` into the migration — migrations in this project are
self-contained and use raw literal values (see the `8438728f8184` reference
migration, which hardcodes `8000`/`24000` rather than importing the enum).

Remove the `xfail` markers added in Task 1.1 (do not modify the assertions).

- **Files**:
  - shared/models/participant.py - add `UNPOSITIONED_SENTINEL` constant; change `position`'s `server_default` to it; add explanatory comment
  - services/api/routes/games.py - update `_resolve_join_position` (line 170) and `_build_host_response` (line 1060) to use `UNPOSITIONED_SENTINEL`
  - services/bot/handlers/join_game.py - update `_resolve_bot_role_position` (line 197) to use `UNPOSITIONED_SENTINEL`
  - shared/utils/participant_sorting.py - update `resolve_role_position`'s no-match fallback (line 120) to use `UNPOSITIONED_SENTINEL`
  - alembic/versions/\<hash\>_backfill_self_added_position_sentinel.py - new reversible migration (create via `uv run alembic revision -m "backfill_self_added_position_sentinel"`, then fill in `upgrade()`/`downgrade()`)
  - tests/unit/services/api/routes/test_games_helpers.py - remove `xfail` marker from the Task 1.1 test; rewrite the three `0`-asserting tests listed above
  - tests/unit/services/bot/handlers/test_join_game.py - rewrite the four `0`-asserting `TestResolveBotRolePosition` tests listed above
  - tests/unit/shared/utils/test_participant_sorting.py - remove `xfail` marker from the Task 1.1 test; rewrite the two `0`-asserting `TestResolveRolePosition` tests listed above
- **Success**:
  - `uv run pytest tests/unit/services/api/routes/test_games_helpers.py tests/unit/services/bot/handlers/test_join_game.py tests/unit/shared/utils/test_participant_sorting.py -v` — all tests pass, 0 xfail
  - No test anywhere in the suite still asserts `position == 0` for a `SELF_ADDED` result (confirm via `grep -rn "SELF_ADDED, 0\|ParticipantType.SELF_ADDED\s*$" tests/unit` and inspect any remaining hits)
  - `uv run mypy shared/ services/` passes with no new errors attributable to these files
  - The new migration file exists under `alembic/versions/` with a correct `down_revision` pointing at the current head
- **Research References**:
  - .copilot-tracking/research/20260716-01-participant-reposition-bug-research.md (Lines 83-84) - Recommended Approach steps 1-2 (migration + join-site/model default change)
  - .copilot-tracking/research/20260716-01-participant-reposition-bug-research.md (Lines 47) - Alembic migration filename/structure convention
  - Source: alembic/versions/8438728f8184_replace_prefilled_position_with_.py (Lines 43-96) - reference reversible-migration shape (raw SQL `UPDATE`, no app-code imports)
  - Source: shared/utils/games.py (Lines 24-47) - `DEFAULT_MAX_PLAYERS` module-constant precedent
- **Dependencies**:
  - Task 1.1 completion (tests must exist and show `xfailed` first)

### Task 1.3: Refactor, add edge-case coverage, verify migration up/down

Add coverage beyond what the RED-phase tests needed, per
`.github/instructions/unit-tests.instructions.md` (no coverage theater):

- A test that `ROLE_MATCHED` participants (via `resolve_role_position`,
  unchanged by this fix) still receive their real priority-role-index
  `position` (e.g. `0`, `1`, `2`), not the sentinel — proving the sentinel
  change is scoped to the "no match"/`SELF_ADDED` branch only. The existing
  `test_highest_priority_role_returns_role_matched_index_0`/
  `test_second_priority_role_returns_role_matched_index_1`/
  `test_multiple_matching_roles_first_match_wins` already cover this and
  need no changes — add one further test that explicitly asserts a
  `ROLE_MATCHED` result's `position` is never equal to
  `UNPOSITIONED_SENTINEL`, guarding against a future accidental widening of
  the sentinel branch's condition.
- A test in `tests/unit/services/api/services/test_games_edit_participants.py`
  (or wherever `_add_new_mentions` is already covered) confirming a newly
  added `HOST_ADDED` participant's `position` is exactly the caller-supplied
  value, not `UNPOSITIONED_SENTINEL` — proving the sentinel default is scoped
  to self-added/role-based-fallback joins and never leaks into the
  host-added creation path. (The migration's `position_type != 8000`
  predicate excluding `HOST_ADDED` rows is verified directly by reading the
  SQL, not by a pytest test — migrations are TDD-exempt per this task's
  earlier note.)

Since SQL migration scripts are exempt from the unit-test TDD cycle per
`.github/instructions/test-driven-development.instructions.md` ("use
integration tests instead"), verify the migration manually against the dev
database rather than writing a pytest migration test, following this
project's established convention (see the `8438728f8184` migration's release
notes: "Migration tested and verified on development database"):

- `uv run alembic upgrade head` — confirm it applies cleanly with no errors
- `uv run alembic downgrade -1` — confirm the reverse `UPDATE` runs cleanly
- `uv run alembic upgrade head` again — leave the database at head for
  subsequent phases

Run the full unit suite and mypy as the phase gate before moving to Phase 2:

- `uv run pytest tests/unit` (never `--testmon` manually per `CLAUDE.md`)
- `uv run mypy shared/ services/`

- **Files**:
  - tests/unit/shared/utils/test_participant_sorting.py - add the `ROLE_MATCHED` sentinel-guard edge-case test described above (extend `TestResolveRolePosition` or add alongside it)
  - tests/unit/services/api/services/test_games_edit_participants.py - add the `HOST_ADDED`-unaffected edge-case test described above
- **Success**:
  - New edge-case tests pass with real assertions
  - `uv run alembic upgrade head` / `downgrade -1` / `upgrade head` all succeed with no errors, database left at head
  - `uv run pytest tests/unit` passes in full
  - `uv run mypy shared/ services/` passes with no new errors
- **Research References**:
  - .copilot-tracking/research/20260716-01-participant-reposition-bug-research.md (Lines 77-79) - `ROLE_BASED`'s `position` is meaningful, not a placeholder, so the sentinel must not leak into that branch
  - .copilot-tracking/research/20260716-01-participant-reposition-bug-research.md (Lines 83) - migration safety rationale (no real game approaches 32,767 participants; `HOST_ADDED` rows excluded from the predicate in both directions)
- **Dependencies**:
  - Task 1.2 completion

## Phase 2: Generalize backend position-update matching

### Task 2.1: Write failing regression test for self-added reposition persistence (RED)

`_update_prefilled_participants`/`_update_participant_positions` currently
load and match only `position_type == ParticipantType.HOST_ADDED` rows, so a
self-added participant's `participant_id` is never found and its `position`
write is a silent no-op. This is a bug fix — no stub, `xfail(strict=True)`.

Add a new test to `tests/unit/services/api/services/test_games_edit_participants.py`,
modeled directly on the existing (and still-passing)
`test_update_prefilled_promotes_self_added_participants` (lines 235-283) but
for a non-waitlist signup method where no promotion should occur:

- `test_update_prefilled_persists_self_added_reposition` — build a game with
  `signup_method=SignupMethod.SELF_SIGNUP.value` and a single `SELF_ADDED`
  participant at `position=32767` (the new sentinel, not `0`). Mock
  `mock_db.execute` so the `current_prefilled` (`HOST_ADDED`-only) query
  returns an empty list (as in the existing promotion test), call
  `game_service._update_prefilled_participants(game, [{"participant_id":
participant_id, "position": 1}])`, and assert:
  - `self_added.position == 1` (the write actually took effect)
  - `self_added.position_type == ParticipantType.SELF_ADDED` (unchanged —
    this is not a promotion, unlike the `HOST_SELECTED_WITH_WAITLIST` path)

Mark it `@pytest.mark.xfail(strict=True, reason="Bug: _update_participant_positions only matches HOST_ADDED participants, so a SELF_ADDED participant's reposition is silently ignored")`.
Run `uv run pytest tests/unit/services/api/services/test_games_edit_participants.py -v`
and confirm it shows `xfailed`.

- **Files**:
  - tests/unit/services/api/services/test_games_edit_participants.py - add the new xfail test described above
- **Success**:
  - New test exists with real assertions on both `position` and `position_type`
  - `uv run pytest tests/unit/services/api/services/test_games_edit_participants.py -v` shows the new test as `xfailed`; `test_update_prefilled_promotes_self_added_participants` and all other pre-existing tests in this file still pass unchanged
- **Research References**:
  - .copilot-tracking/research/20260716-01-participant-reposition-bug-research.md (Lines 16-19) - `_update_prefilled_participants`/`_update_participant_positions` `HOST_ADDED`-only filter, root cause
  - .copilot-tracking/research/20260716-01-participant-reposition-bug-research.md (Lines 57) - "Backend silently ignores the update" key discovery
  - Source: services/api/services/games.py (Lines 1416-1485) - current `_update_participant_positions`/`_update_prefilled_participants` implementation
  - Source: tests/unit/services/api/services/test_games_edit_participants.py (Lines 235-283) - `test_update_prefilled_promotes_self_added_participants` reference pattern
- **Dependencies**:
  - Phase 1 completion (the sentinel default must exist so the test's starting `position=32767` is representative of real data)

### Task 2.2: Match on `participant_id` across `game.participants` for position updates, keep removal scoped to `HOST_ADDED` (GREEN)

Change `_update_participant_positions`'s caller in
`_update_prefilled_participants` (`services/api/services/games.py:1484-1485`)
to pass `game.participants` (the full, already-loaded ORM relationship — the
same collection the existing `HOST_SELECTED_WITH_WAITLIST` promotion block at
lines 1467-1479 already iterates directly) instead of the `HOST_ADDED`-only
`current_participants` list, so the position-matching loop in
`_update_participant_positions` (lines 1428-1435) can find and update **any**
participant referenced by `participant_id` in `participant_data_list`,
regardless of `position_type`.

**Do not** widen the `current_prefilled` DB query (lines 1453-1459) or its
use in `_remove_outdated_participants` (line 1482) — that removal path must
stay scoped to `HOST_ADDED` rows only. Widening it would make
`_remove_outdated_participants` delete any self-added/role-matched
participant whose `participant_id` is absent from `participant_data_list`,
which after the Phase 3 frontend change will routinely be true for untouched
participants below the disturbed prefix (they are intentionally omitted from
the payload, not being removed). `removed_participant_ids`/`_remove_participants`
(lines 1347-1372, wired at lines 2052-2053) remains the only mechanism that
can delete a self-added/role-matched participant.

Target shape (adapt to fit; this is guidance, not a literal diff):

```python
# Get current host-added participants (used only for removal-of-cleared-prefill-entries)
current_prefilled = await self.db.execute(
    select(participant_model.GameParticipant).where(
        participant_model.GameParticipant.game_session_id == game.id,
        participant_model.GameParticipant.position_type == ParticipantType.HOST_ADDED,
    )
)
current_participants = current_prefilled.scalars().all()

...

# Remove pre-filled participants not in the existing list (HOST_ADDED only)
await self._remove_outdated_participants(current_participants, existing_participant_ids)

# Update positions for any participant referenced by id, regardless of position_type
self._update_participant_positions(game.participants, participant_data_list)
```

Remove the `xfail` marker added in Task 2.1 (do not modify the assertion).

No pre-existing test in this file patches `_update_participant_positions`'s
argument directly (they exercise it through
`_update_prefilled_participants`), so no other test in
`test_games_edit_participants.py` should need rewriting — confirm this by
running the full file, not just the new test.

Run `uv run pytest tests/unit/services/api/services/test_games_edit_participants.py -v`
and confirm all tests pass (the Task 2.1 test now green; the pre-existing
`test_update_prefilled_promotes_self_added_participants` and the two
Discord-mention tests unchanged and still green).

- **Files**:
  - services/api/services/games.py - change `_update_prefilled_participants`'s call to `_update_participant_positions` to pass `game.participants` instead of the `HOST_ADDED`-only `current_participants`
  - tests/unit/services/api/services/test_games_edit_participants.py - remove `xfail` marker from the Task 2.1 test
- **Success**:
  - `_update_participant_positions` is called with `game.participants` (or an equivalent unrestricted collection), not the `HOST_ADDED`-filtered query result
  - `_remove_outdated_participants` and the `current_prefilled` query it consumes remain unchanged and still scoped to `HOST_ADDED`
  - `uv run pytest tests/unit/services/api/services/test_games_edit_participants.py -v` — all tests pass, 0 xfail, 0 failures
  - `uv run mypy shared/ services/` passes with no new errors attributable to this file
- **Research References**:
  - .copilot-tracking/research/20260716-01-participant-reposition-bug-research.md (Lines 85) - Recommended Approach step 3 (generalize matching by `participant_id`, leave `position_type` untouched outside the waitlist promotion path)
  - .copilot-tracking/research/20260716-01-participant-reposition-bug-research.md (Lines 87) - "Leave `HOST_SELECTED_WITH_WAITLIST`'s promotion logic unchanged" (Recommended Approach step 5)
  - .copilot-tracking/research/20260716-01-participant-reposition-bug-research.md (Lines 75) - why no `position_type` mutation occurs for this path (leave-notification safety)
  - Source: services/api/services/games.py (Lines 1467-1479) - existing `self_added_to_promote` block already iterates `game.participants` directly, the precedent this task follows
- **Dependencies**:
  - Task 2.1 completion

### Task 2.3: Refactor, add edge-case coverage, confirm waitlist promotion path untouched

Add coverage beyond what the RED-phase test needed:

- A test that repositioning a `ROLE_MATCHED` participant's `position` also
  persists when its `position_type` is left unchanged (the write-path fix is
  orthogonal to sort semantics — this only proves the value is no longer
  silently dropped). The separate question of what `ROLE_BASED` reordering
  should _mean_ (converting the participant's bucket entirely) is resolved
  and implemented in Tasks 2.4-2.6 below, not deferred.
- A test that an untouched self-added participant **not** referenced in
  `participant_data_list` is left with its original `position` unchanged and
  is **not** deleted (guards the `_remove_outdated_participants` scoping
  decision made in Task 2.2 against a future regression).

Do not yet run the full `test_games_promotion.py` phase-gate check here —
that check, and the full unit suite/mypy gate, move to Task 2.6 now that
Phase 2 continues with the `ROLE_BASED` conversion work below.

- **Files**:
  - tests/unit/services/api/services/test_games_edit_participants.py - add the two edge-case tests described above
- **Success**:
  - New edge-case tests pass with real assertions
- **Research References**:
  - .copilot-tracking/research/20260716-01-participant-reposition-bug-research.md (Lines 75) - `HOST_SELECTED_WITH_WAITLIST` unaffected/doesn't need the sentinel fix, its own promotion block stays as-is
  - .copilot-tracking/research/20260716-01-participant-reposition-bug-research.md (Lines 98) - testing guidance: confirm `HOST_SELECTED_WITH_WAITLIST` behavior unchanged
- **Dependencies**:
  - Task 2.2 completion

### Task 2.4: Write failing regression tests for `ROLE_BASED` reposition-converts-to-`SELF_ADDED` (RED)

**Decision (supersedes the research document's "Open question: `ROLE_BASED`
signup method")**: when a host explicitly repositions a `ROLE_MATCHED`
participant in a `ROLE_BASED` game, that participant's `position_type`
converts from `ROLE_MATCHED` to `SELF_ADDED`, with an explicit `position`
matching its new display index — routed through the exact same
sentinel/explicit-position mechanism Phases 1-2 already build for plain
self-added repositioning, not a new mechanic and not a promotion to
`HOST_ADDED`. Rationale: "the host has final say" — an explicit manual
reposition overrides the role-priority tier entirely. This is a natural fit,
not a foreign concept, for `ROLE_BASED` games specifically: `resolve_role_position`
already routes any non-matching-role joiner into `SELF_ADDED` (Phase 1's
sentinel-default fix applies to that exact fallback), so `ROLE_BASED` games
already contain a mix of `ROLE_MATCHED` and `SELF_ADDED` participants today —
converting a repositioned participant into that same, already-existing
`SELF_ADDED` bucket reuses structure the signup method already has, rather
than inventing a new one.

This is a bug fix (`ROLE_BASED` reordering has never persisted, the same
failure mode as the rest of this plan) — no stub, `xfail(strict=True)`.

Add two new tests to `tests/unit/services/api/services/test_games_edit_participants.py`,
modeled directly on `test_update_prefilled_promotes_self_added_participants`
(lines 235-283) and the Task 2.1 test added above, but for `SignupMethod.ROLE_BASED`:

1. `test_update_prefilled_converts_role_matched_to_self_added_on_reposition` —
   build a game with `signup_method=SignupMethod.ROLE_BASED.value` and a
   single `ROLE_MATCHED` participant at `position=0` (a real priority-role
   index, not a sentinel). Mock `mock_db.execute` so the `current_prefilled`
   (`HOST_ADDED`-only) query returns an empty list, call
   `game_service._update_prefilled_participants(game, [{"participant_id":
participant_id, "position": 1}])`, and assert:
   - `role_matched.position_type == ParticipantType.SELF_ADDED` (converted —
     not left as `ROLE_MATCHED`, and not promoted to `HOST_ADDED`)
   - `role_matched.position == 1` (the new explicit position from the payload)
2. `test_update_prefilled_leaves_untouched_role_matched_participant_alone` —
   same `ROLE_BASED` game, but with **two** `ROLE_MATCHED` participants
   (`touched` at `position=0`, `untouched` at `position=1`). Call
   `_update_prefilled_participants` with only `touched`'s `participant_id` in
   `participant_data_list` (mirroring how Phase 3's `buildParticipantsPayload`
   omits anything below the highest explicitly-touched index). Assert:
   - `touched.position_type == ParticipantType.SELF_ADDED`, `touched.position == 1`
   - `untouched.position_type == ParticipantType.ROLE_MATCHED` (unchanged —
     never referenced in the payload, so never converted)
   - `untouched.position == 1` (its original real priority-role index,
     numerically unchanged — this is a coincidental numeric match with
     `touched`'s new position, not a collision: they are in different
     `position_type` buckets, so `sort_participants`'s `(position_type,
position, joined_at)` key keeps them from tying)

Mark both new tests `@pytest.mark.xfail(strict=True, reason="Bug: ROLE_BASED reordering has never persisted; ROLE_MATCHED participants are never converted or matched by participant_id, so a host's explicit reposition is silently ignored")`.
Run `uv run pytest tests/unit/services/api/services/test_games_edit_participants.py -v`
and confirm both show `xfailed`.

- **Files**:
  - tests/unit/services/api/services/test_games_edit_participants.py - add the two xfail tests described above
- **Success**:
  - Both new tests have real assertions on `position_type` and `position` (not just "was called")
  - `uv run pytest tests/unit/services/api/services/test_games_edit_participants.py -v` shows both new tests as `xfailed`; all pre-existing tests in this file still pass unchanged
- **Research References**:
  - .copilot-tracking/research/20260716-01-participant-reposition-bug-research.md (Lines 77-79) - the original "Open question: `ROLE_BASED` signup method," now resolved by this decision
  - .copilot-tracking/research/20260716-01-participant-reposition-bug-research.md (Lines 22-24) - `resolve_role_position`'s `(SELF_ADDED, 0)` (now `UNPOSITIONED_SENTINEL`) fallback, proving `ROLE_BASED` games already mix `ROLE_MATCHED` and `SELF_ADDED` participants today
  - Source: tests/unit/services/api/services/test_games_edit_participants.py (Lines 235-283) - `test_update_prefilled_promotes_self_added_participants` reference pattern (same shape, different source/target `position_type`)
- **Dependencies**:
  - Task 2.3 completion

### Task 2.5: Convert repositioned `ROLE_MATCHED` participants to `SELF_ADDED` in `_update_prefilled_participants` (GREEN)

Add a second promotion-shaped block to `_update_prefilled_participants`
(`services/api/services/games.py`), parallel to (but independent of) the
existing `HOST_SELECTED_WITH_WAITLIST` `self_added_to_promote` block
(lines 1467-1479), gated on `game.signup_method == SignupMethod.ROLE_BASED`:

```python
if game.signup_method == SignupMethod.HOST_SELECTED_WITH_WAITLIST:
    self_added_to_promote = [
        p
        for p in game.participants
        if p.id in existing_participant_ids
        and p.position_type == ParticipantType.SELF_ADDED
    ]
    for p in self_added_to_promote:
        position = next(
            d["position"] for d in participant_data_list if d.get("participant_id") == p.id
        )
        p.position_type = ParticipantType.HOST_ADDED
        p.position = position

if game.signup_method == SignupMethod.ROLE_BASED:
    role_matched_to_convert = [
        p
        for p in game.participants
        if p.id in existing_participant_ids
        and p.position_type == ParticipantType.ROLE_MATCHED
    ]
    for p in role_matched_to_convert:
        position = next(
            d["position"] for d in participant_data_list if d.get("participant_id") == p.id
        )
        p.position_type = ParticipantType.SELF_ADDED
        p.position = position
```

`existing_participant_ids` is exactly the same set Phase 3's
`buildParticipantsPayload` populates with the full "disturbed prefix" (every
participant at or above the highest explicitly-touched index) — this block
therefore converts **every** `ROLE_MATCHED` participant included in that
prefix, not only the literally-dragged one. This is a deliberate scope
decision, not an oversight: the wire payload (`{participant_id, position}`)
carries no flag distinguishing "the participant the host literally dragged"
from "a bystander reindexed as a side effect of that drag" (`EditableParticipantList.tsx`'s
`isExplicitlyPositioned` never leaves the frontend), so the backend cannot
and should not try to guess. This exactly mirrors how a bystander plain
`SELF_ADDED` participant already gets its position pinned to an explicit
value merely by being in the prefix (Task 3.3's documented "pin the whole
prefix" behavior) — here the same inclusion additionally flips
`position_type` when the participant's _current_ type is `ROLE_MATCHED`.
`ROLE_MATCHED` participants below the highest explicitly-touched index are
never in `existing_participant_ids` and are therefore never touched by this
block, keeping their real priority-role-index `position` and
`ROLE_MATCHED` type exactly as `resolve_role_position` assigned them.

**Known, intentional consequence** (document this in the changes file, not
just here): because `sort_participants`'s key is `(position_type, position,
joined_at)` and `SELF_ADDED` (24000) always sorts after every remaining
`ROLE_MATCHED` (16000) entry regardless of the assigned explicit `position`,
dragging a `ROLE_MATCHED` participant to a spot that is visually _above_
another, still-unconverted `ROLE_MATCHED` participant will still persist
with the dragged participant sorting _below_ every remaining `ROLE_MATCHED`
participant. This is intended, not a bug: per the decision, an explicit
reposition fully exits the role-priority tier — it is not a same-tier nudge.
If the host wants two `ROLE_MATCHED` participants to end up in a specific
relative order while _both_ keep their role-priority tier, that is
unsupported by this fix (no such action exists in the current edit UI, which
only ever converts on explicit reposition) and is out of scope.

This block only mutates `position_type`/`position` on participants already
present in `game.participants` (no new query, no new removal path) — it does
not interact with `_remove_outdated_participants` (still scoped to
`HOST_ADDED`, unchanged) or with the `HOST_SELECTED_WITH_WAITLIST` block
(mutually exclusive `signup_method`, never both true for the same game).

Remove the `xfail` markers added in Task 2.4 (do not modify the assertions).

- **Files**:
  - services/api/services/games.py - add the `ROLE_BASED`-gated `role_matched_to_convert` block to `_update_prefilled_participants`, alongside (not replacing) the existing `HOST_SELECTED_WITH_WAITLIST` block
  - tests/unit/services/api/services/test_games_edit_participants.py - remove `xfail` markers from the two Task 2.4 tests
- **Success**:
  - A `ROLE_BASED` game's explicitly-repositioned `ROLE_MATCHED` participant is converted to `SELF_ADDED` with the new explicit `position`; an untouched `ROLE_MATCHED` participant keeps its type and priority-index `position`
  - `uv run pytest tests/unit/services/api/services/test_games_edit_participants.py -v` — all tests pass, 0 xfail, 0 failures
  - `uv run mypy shared/ services/` passes with no new errors attributable to this file
- **Research References**:
  - .copilot-tracking/research/20260716-01-participant-reposition-bug-research.md (Lines 77-79) - the open question this task resolves
  - Source: services/api/services/games.py (Lines 1467-1479) - the existing `HOST_SELECTED_WITH_WAITLIST` promotion block this new block is modeled on
  - Source: frontend/src/components/EditableParticipantList.tsx (Lines 86-146) - confirms `isExplicitlyPositioned` never leaves the frontend, so the backend cannot distinguish "literally dragged" from "swept along" and must treat the whole disturbed prefix uniformly
- **Dependencies**:
  - Task 2.4 completion

### Task 2.6: Refactor, add edge-case coverage, confirm mixed-bucket sort/partition and waitlist path untouched

Add coverage beyond what the RED-phase tests needed:

- A test confirming `_add_new_mentions`/the `HOST_SELECTED_WITH_WAITLIST`
  block are unaffected when a `ROLE_BASED` game is edited (the two `if`
  blocks are gated on mutually exclusive `signup_method` values; a quick
  test constructing a `ROLE_BASED` game and asserting no participant's
  `position_type` becomes `HOST_ADDED` guards against a future accidental
  broadening of the waitlist block's condition).
- A test in `tests/unit/shared/utils/test_participant_sorting.py` (or
  extending `TestPartitionParticipants`) confirming a mixed-bucket scenario
  sorts correctly: given one remaining `ROLE_MATCHED` participant (real
  priority index `0`) and one converted `SELF_ADDED` participant (explicit
  `position=1`, simulating the post-conversion state), `sort_participants`
  places the `ROLE_MATCHED` participant first (lower `position_type`)
  regardless of the numeric `position` values on either side — this is
  already-correct, unchanged behavior in `sort_participants`/
  `partition_participants` (no production code change needed here), so
  write this test directly with no `xfail` marker per
  `.github/instructions/test-driven-development.instructions.md`'s "Writing
  Tests for Already-Correct Code" section — it exists to document and lock
  in the interaction, not to drive a new implementation.

Run `uv run pytest tests/unit/services/api/services/test_games_promotion.py -v`
(the dedicated `HOST_SELECTED_WITH_WAITLIST` promotion suite) and confirm it
is entirely unaffected — 0 changes needed, all tests green, proving neither
Task 2.2's nor Task 2.5's generalization disturbed the waitlist promotion
path.

Run the full unit suite and mypy as the phase gate before moving to Phase 3:

- `uv run pytest tests/unit` (never `--testmon` manually per `CLAUDE.md`)
- `uv run mypy shared/ services/`

- **Files**:
  - tests/unit/services/api/services/test_games_edit_participants.py - add the `HOST_SELECTED_WITH_WAITLIST`-unaffected edge-case test described above
  - tests/unit/shared/utils/test_participant_sorting.py - add the mixed-bucket sort/partition test described above
- **Success**:
  - New edge-case tests pass with real assertions
  - `uv run pytest tests/unit/services/api/services/test_games_promotion.py -v` passes unchanged (no test modifications needed in that file)
  - `uv run pytest tests/unit` passes in full
  - `uv run mypy shared/ services/` passes with no new errors
- **Research References**:
  - .copilot-tracking/research/20260716-01-participant-reposition-bug-research.md (Lines 75) - `HOST_SELECTED_WITH_WAITLIST` unaffected/doesn't need the sentinel fix, its own promotion block stays as-is
  - .copilot-tracking/research/20260716-01-participant-reposition-bug-research.md (Lines 98) - testing guidance: confirm `HOST_SELECTED_WITH_WAITLIST` behavior unchanged
- **Dependencies**:
  - Task 2.5 completion

## Phase 3: Frontend disturbed-prefix payload extension

### Task 3.1: Write failing regression tests for the disturbed-prefix payload (RED)

`EditGame.tsx`'s `handleSubmit` (lines 174-191) and `handleSaveAndArchive`
(lines 331-341) each filter `formData.participants` to
`p.mention.trim() && p.isExplicitlyPositioned` — dropping any self-added
participant that was reordered as a side effect of another participant's
move (only the literally-dragged participant is marked
`isExplicitlyPositioned`, per `EditableParticipantList.tsx`'s `moveUp`/
`moveDown`/`handleDrop`, lines 86-146). This is a bug fix — no stub,
`test.failing` per the TDD-for-bug-fixes workflow.

Add tests to `frontend/src/pages/__tests__/EditGame.test.tsx` (extending the
existing `describe('EditGame', ...)` block and its `apiClient.put` mock
pattern used by `it('handles save successfully', ...)` at line 169):

1. `test.failing('includes the full disturbed prefix, not just the literally-moved participant, in the submitted payload', ...)` —
   render `EditGame` with `initialParticipants`/`game.participants` containing
   three `SELF_ADDED` participants (A, B, C, in that display order), simulate
   the host dragging C to the top (so the resulting `formData.participants`
   array is `[C (isExplicitlyPositioned: true), A (unchanged), B (unchanged)]`
   with `preFillPosition` `1, 2, 3` respectively — mirroring exactly what
   `EditableParticipantList.handleDrop` produces), submit the form, and
   assert the `participants` field of the submitted `FormData` (parsed via
   `JSON.parse`) contains entries for **all three** participants (C, A, B)
   with `position` `1, 2, 3` — not just C.
2. `test.failing('excludes untouched participants below the highest explicitly-positioned index', ...)` —
   same three-participant setup, but assert that a fourth untouched
   `SELF_ADDED` participant D displayed **below** C's new highest-touched
   index is **excluded** from the payload entirely (proving the fix does not
   regress into "send everyone always").

Model the `FormData`-parsing/assertion style directly on the existing test at
line 657 (`'sends post_at in FormData when form is submitted with
pre-populated post_at'`), which already extracts and inspects individual
`FormData` fields after calling `fireEvent.submit`/`waitFor`.

Run `npm test -- EditGame` from `frontend/` and confirm both new tests show
as expected failures.

- **Files**:
  - frontend/src/pages/**tests**/EditGame.test.tsx - add the two `test.failing` tests described above
- **Success**:
  - Both new tests have real assertions on the parsed `participants` JSON payload contents (not just "was called")
  - `cd frontend && npm run test -- EditGame` shows both new tests as expected failures; all pre-existing tests in this file still pass
- **Research References**:
  - .copilot-tracking/research/20260716-01-participant-reposition-bug-research.md (Lines 9-15) - `EditableParticipantList.tsx`/`EditGame.tsx`/`GameForm.tsx` current behavior (only the dragged participant marked explicit; submission filter drops everyone else)
  - .copilot-tracking/research/20260716-01-participant-reposition-bug-research.md (Lines 86) - Recommended Approach step 4: extend the submission filter to include the full disturbed prefix, mirroring `HOST_SELECTED_WITH_WAITLIST`'s existing whole-prefix marking
  - Source: frontend/src/components/EditableParticipantList.tsx (Lines 86-146) - `moveUp`/`moveDown`/`handleDrop` (only moved participant marked explicit; every row's `preFillPosition` reindexed on every move)
  - Source: frontend/src/pages/**tests**/EditGame.test.tsx (Lines 657-676) - `FormData`-parsing assertion style to model the new tests on
- **Dependencies**:
  - Phase 2 completion (the backend must already accept a self-added `participant_id` before the frontend payload change has any effect worth testing end-to-end in Phase 4)

### Task 3.2: Extract shared `buildParticipantsPayload` helper and use it in both submit paths (GREEN)

Both `handleSubmit` (lines 175-188) and `handleSaveAndArchive` (lines
331-338) independently duplicate the same
`.filter((p) => p.mention.trim() && p.isExplicitlyPositioned).map(...)`
block. Extract a single module-level helper in `frontend/src/pages/EditGame.tsx`
so the fix applies identically to both save paths instead of only one:

```typescript
/**
 * Build the participants payload for a game-update submission.
 *
 * Includes every participant whose mention is non-empty and who is either
 * explicitly positioned (the participant the host literally moved/added) or
 * displayed at or above the highest explicitly-positioned index — the
 * "disturbed prefix" that was reindexed as a side effect of that move.
 * Participants below that index are omitted entirely and keep whatever
 * position (sentinel or previously-explicit) they already had server-side.
 */
function buildParticipantsPayload(
  participants: ParticipantInput[]
): Array<{ participant_id: string; position: number } | { mention: string; position: number }> {
  const highestExplicitIndex = participants.reduce(
    (max, p, idx) => (p.isExplicitlyPositioned ? idx : max),
    -1
  );
  return participants
    .filter(
      (p, idx) => p.mention.trim() && (p.isExplicitlyPositioned || idx <= highestExplicitIndex)
    )
    .map((p) => {
      if (!p.id.startsWith('temp-')) {
        return { participant_id: p.id, position: p.preFillPosition };
      }
      return { mention: p.resolvedMention ?? p.mention.trim(), position: p.preFillPosition };
    });
}
```

Replace both duplicated blocks with calls to this helper:

```typescript
const participantsList = buildParticipantsPayload(formData.participants);
```

(`handleSaveAndArchive`'s existing block used `p.mention.trim()` rather than
`p.resolvedMention ?? p.mention.trim()` for the temp-id branch — consolidating
into one helper also fixes this pre-existing inconsistency between the two
paths; note this explicitly as a side effect in the changes file, since it is
one extra behavioral change beyond the core bug fix.)

Remove the `test.failing` markers added in Task 3.1 (do not modify the
assertions).

Run `cd frontend && npm run test -- EditGame` and confirm all tests pass (the
two Task 3.1 tests now green; all pre-existing `EditGame.test.tsx` tests,
including the `post_at`/`recur_rule`/archive-branch tests, unchanged and
still green). Run `cd frontend && npm run build` to confirm no TypeScript
errors.

- **Files**:
  - frontend/src/pages/EditGame.tsx - add `buildParticipantsPayload`; replace both duplicated filter/map blocks in `handleSubmit` and `handleSaveAndArchive` with calls to it
  - frontend/src/pages/**tests**/EditGame.test.tsx - remove `test.failing` markers from the two Task 3.1 tests
- **Success**:
  - `handleSubmit` and `handleSaveAndArchive` both call the same `buildParticipantsPayload` helper; no duplicated filter/map logic remains
  - `cd frontend && npm run test -- EditGame` — all tests pass, 0 expected-failures, 0 failures
  - `cd frontend && npm run build` passes with no new TypeScript errors
- **Research References**:
  - .copilot-tracking/research/20260716-01-participant-reposition-bug-research.md (Lines 86) - Recommended Approach step 4, the exact behavior this helper implements
  - .copilot-tracking/research/20260716-01-participant-reposition-bug-research.md (Lines 15) - `GameForm.tsx`'s `HOST_SELECTED_WITH_WAITLIST` branch already marks its whole confirmed prefix explicit, the pattern being generalized
  - Source: frontend/src/pages/EditGame.tsx (Lines 174-191, 330-341) - the two duplicated blocks being consolidated
- **Dependencies**:
  - Task 3.1 completion

### Task 3.3: Refactor, add edge-case coverage, confirm waitlist payload construction unchanged

Add coverage beyond what the RED-phase tests needed:

- A test for two non-contiguous explicit moves (e.g. participant at index 5
  moved to index 1, then a different participant at index 7 moved to index 4) asserting the payload includes every participant from index 0 through
  the new highest explicitly-positioned index, not just the two literally
  moved ones.
- A test documenting the intentional "pin the whole prefix" behavior when a
  brand-new participant is typed in at the bottom via `addParticipant`
  (`EditableParticipantList.tsx:69-78`, which always marks the new entry
  `isExplicitlyPositioned: true` at the last index): assert that every
  existing self-added participant above it is included in the payload with
  its **current, unchanged relative order** as an explicit `position` — note
  in the test's docstring/comment that this is harmless (it freezes the
  already-correct FCFS order into explicit values) and is a deliberate
  consequence of the "highest explicitly-positioned index" rule, not a bug.
- Run the existing `HOST_SELECTED_WITH_WAITLIST`-mode tests in
  `frontend/src/components/__tests__/GameForm.test.tsx` and any
  waitlist-specific `EditGame.test.tsx` coverage and confirm they pass
  unchanged — `buildParticipantList`'s waitlist branch already marks its
  entire confirmed prefix explicit, so `buildParticipantsPayload`'s
  `highestExplicitIndex` computation is a no-op change for that mode.
- A test confirming a `ROLE_MATCHED` participant (in a `ROLE_BASED` game) is
  included in the disturbed-prefix payload identically to a `SELF_ADDED`
  participant when dragged — `GameForm.tsx`'s non-waitlist `buildParticipantList`
  branch (lines 205-221) already sets `isReadOnly: p.position_type !==
ParticipantType.HOST_ADDED` and `isExplicitlyPositioned:
p.position_type === ParticipantType.HOST_ADDED` identically for
  `ROLE_MATCHED` and `SELF_ADDED` entries, and `EditableParticipantList.tsx`'s
  `moveUp`/`moveDown`/`handleDrop` never check `isReadOnly` before allowing a
  reorder, so no frontend code change is required for `ROLE_BASED` support —
  this test exists to lock that fact in as a regression guard, not to drive a
  new implementation. Write it directly with no `test.failing` marker (already-correct
  code) per `.github/instructions/test-driven-development.instructions.md`'s
  "Writing Tests for Already-Correct Code" section.

Run the full frontend suite and build as the phase gate before moving to
Phase 4:

- `cd frontend && npm run test`
- `cd frontend && npm run build`

- **Files**:
  - frontend/src/pages/**tests**/EditGame.test.tsx - add the two edge-case tests described above
- **Success**:
  - New edge-case tests pass with real assertions
  - `cd frontend && npm run test` passes in full
  - `cd frontend && npm run build` passes with no new TypeScript errors
- **Research References**:
  - .copilot-tracking/research/20260716-01-participant-reposition-bug-research.md (Lines 75, 87) - `HOST_SELECTED_WITH_WAITLIST` must remain unaffected by this generalization
- **Dependencies**:
  - Task 3.2 completion

## Phase 4: End-to-end verification

### Task 4.1: Add integration test proving reposition persists across reload

Integration tests are written after the implementation exists (Phases 1-3
are complete by this point), so no RED phase, stub, or `xfail`/`test.failing`
marker applies here per
`.github/instructions/test-driven-development.instructions.md`'s
"Integration Tests (TDD NOT Required)" section — write the test to pass
immediately against the real implementation.

Add two new tests to `tests/integration/test_games_crud.py`, modeled on
`test_update_game_success` (lines 410-442) and
`test_update_game_with_all_optional_form_fields` (lines 445-483):

- `test_update_game_persists_self_added_participant_reposition` — create a
  game via `_create_game_via_api` with the default (`SELF_SIGNUP`) signup
  method, insert a `SELF_ADDED` participant row directly via the test's
  database session fixture with `position=32767` (the sentinel), then `PUT
/api/v1/games/{id}` with `participants=json.dumps([{"participant_id":
<id>, "position": 1}])`. Assert the response is `200`, then either
  re-`GET` the game or re-query the database directly and assert the
  participant's `position == 1` and `position_type` is still `SELF_ADDED`
  (`24000`) — proving both that the write persisted (Phase 2's fix) and that
  no unintended promotion occurred (this is not the
  `HOST_SELECTED_WITH_WAITLIST` path).
- `test_update_game_persists_role_matched_reposition_as_self_added` — create
  a game via `_create_game_via_api` with `signup_method=ROLE_BASED`, insert a
  `ROLE_MATCHED` participant row directly via the test's database session
  fixture with `position=0` (a real priority-role index), then `PUT
/api/v1/games/{id}` with `participants=json.dumps([{"participant_id":
<id>, "position": 1}])`. Assert the response is `200`, then re-query the
  database and assert the participant's `position_type` is now `SELF_ADDED`
  (`24000`, converted) and `position == 1` — proving the Phase 2 Task 2.5
  conversion persists end-to-end through the real API and database, not just
  in the mocked unit tests.

- **Files**:
  - tests/integration/test_games_crud.py - add the two integration tests described above
- **Success**:
  - Both new tests pass against the real API + database with no `xfail`/expected-failure markers
  - `scripts/run-integration-tests.sh tests/integration/test_games_crud.py |& tee output-integration.txt` passes, per `.github/instructions/test-execution.instructions.md` (capture full output with `tee` before filtering; allow adequate timeout)
- **Research References**:
  - .copilot-tracking/research/20260716-01-participant-reposition-bug-research.md (Lines 98) - testing guidance: "reposition a self-added participant in a SELF_SIGNUP game and confirm persistence across reload"
  - .copilot-tracking/research/20260716-01-participant-reposition-bug-research.md (Lines 77-79) - the `ROLE_BASED` open question, now resolved and end-to-end tested by the second test above
  - Source: tests/integration/test_games_crud.py (Lines 410-483) - `test_update_game_success`/`test_update_game_with_all_optional_form_fields` reference patterns for the PUT-endpoint test shape
- **Dependencies**:
  - Phase 3 completion (full stack — migration, backend matching, frontend payload — must all be in place for this end-to-end test to be meaningful)

### Task 4.2: Add leave-game regression-safety tests for repositioned/converted participants

`leave_game_and_notify` (`shared/services/leave_game.py:90-103`) keys its
`host_added_dropout` DM strictly off `position_type == HOST_ADDED`, which
this plan never sets for a merely-repositioned participant: Task 2.2
explicitly avoids any `position_type` change outside the existing
`HOST_SELECTED_WITH_WAITLIST` promotion block, and Task 2.5's `ROLE_BASED`
conversion explicitly converts to `SELF_ADDED`, never `HOST_ADDED`. This
code is therefore already correct with respect to both cases — per
`.github/instructions/test-driven-development.instructions.md`'s "Writing
Tests for Already-Correct Code" section, write these tests directly with no
`xfail` marker; if either fails, that indicates a real problem to fix, not
an expected-failure state.

Add two tests to `tests/unit/shared/services/test_leave_game_shared.py`,
modeled on `test_self_added_leave_with_empty_waitlist_enqueues_nothing`
(around line 164) and `test_host_added_leave_enqueues_dropout_dm_to_host`
(around line 142):

- `test_repositioned_self_added_leave_does_not_enqueue_dropout_dm` — a
  `SELF_ADDED` participant with an explicit small `position` (e.g. `1`,
  simulating a plain self-added participant already repositioned by this
  fix, not the sentinel) leaves; assert no `host_added_dropout` row is
  enqueued (same assertion style as `test_no_host_dropout_dm_when_host_missing`,
  filtering `_bot_rows(mock_db)` for `notification_type ==
"host_added_dropout"` and asserting the result is empty).
- `test_converted_role_matched_leave_does_not_enqueue_dropout_dm` — a
  participant with `position_type=SELF_ADDED` and an explicit small
  `position`, constructed to simulate the _specific_ post-Task-2.5 state (a
  participant that started as `ROLE_MATCHED` and was converted by an
  explicit host reposition, not one that was always `SELF_ADDED`) leaves;
  assert no `host_added_dropout` row is enqueued. This test is functionally
  identical in mechanics to the one above (`leave_game_and_notify` only ever
  inspects the participant's _current_ `position_type`, never its history),
  but exists as a separate, explicitly-named regression guard so the
  `ROLE_BASED` conversion path has its own direct test rather than relying
  on an inference from the plain-`SELF_ADDED` case.

- **Files**:
  - tests/unit/shared/services/test_leave_game_shared.py - add the two regression-safety tests described above
- **Success**:
  - Both new tests pass immediately with no `xfail` marker (already-correct-code path)
  - `uv run pytest tests/unit/shared/services/test_leave_game_shared.py -v` passes in full
- **Research References**:
  - .copilot-tracking/research/20260716-01-participant-reposition-bug-research.md (Lines 29) - `leave_game.py`'s `host_added_dropout` gate, the behavior these tests guard
  - .copilot-tracking/research/20260716-01-participant-reposition-bug-research.md (Lines 73) - "a repositioned self-added participant never triggers the 'host added this person' notification, because they were never promoted to that type" — now also true of a converted `ROLE_MATCHED` participant, which is likewise never promoted to `HOST_ADDED`
  - Source: tests/unit/shared/services/test_leave_game_shared.py (Lines 142-200) - `test_host_added_leave_enqueues_dropout_dm_to_host`/`test_no_host_dropout_dm_when_host_missing` reference patterns
- **Dependencies**:
  - Phase 2 completion (position_type semantics, including the `ROLE_BASED` conversion, finalized)

### Task 4.3: Full-suite verification gate

This is the last phase in this plan. Before considering the overall task
complete, run the full verification suite:

- `uv run pytest tests/unit` (full suite, never `--testmon` manually per `CLAUDE.md`; delete `.testmondata` first if stale)
- `uv run mypy shared/ services/`
- `cd frontend && npm run build`
- `cd frontend && npm run test`
- `scripts/run-integration-tests.sh tests/integration/test_games_crud.py |& tee output-integration.txt`
- `git diff --stat` over `shared/utils/participant_sorting.py` and confirm it
  is empty — `sort_participants`/`partition_participants`/`resolve_role_position`
  are entirely unchanged by this plan; the `ROLE_BASED` decision is
  implemented purely as a `position_type`/`position` mutation in
  `services/api/services/games.py` (Task 2.5), not a sorting-logic change
- Confirm no test in `tests/unit/services/api/services/test_games_promotion.py`
  or `tests/unit/shared/utils/test_participant_sorting.py`'s
  `TestPartitionParticipants` class needed modification — proving
  `HOST_SELECTED_WITH_WAITLIST` behavior is genuinely unchanged, not just
  passing by coincidence
- Confirm the research document's "Open question: `ROLE_BASED` signup
  method" is resolved, not merely re-labeled: `ROLE_MATCHED` participants
  referenced in an edit payload convert to `SELF_ADDED` (Task 2.5), untouched
  ones keep their priority-index `position` and type (Task 2.4's second
  test), no `host_added_dropout` misfires for a converted participant
  leaving (Task 4.2), and the mixed-bucket sort order is locked in by a test
  (Task 2.6)

- **Files**:
  - None (verification only)
- **Success**:
  - All commands and checks above pass
  - `shared/utils/participant_sorting.py` has zero diff
  - No pre-existing `HOST_SELECTED_WITH_WAITLIST`-focused test file required a behavioral change
  - No remaining reference in the plan, details, or changes-tracking files describes `ROLE_BASED` reordering as unresolved
- **Research References**:
  - .copilot-tracking/research/20260716-01-participant-reposition-bug-research.md (Lines 92-100) - Implementation Guidance objectives, key tasks, dependencies, and success criteria in full
  - .copilot-tracking/research/20260716-01-participant-reposition-bug-research.md (Lines 77-79) - the original `ROLE_BASED` open question, resolved by Tasks 2.4-2.6 and re-verified end-to-end here
- **Dependencies**:
  - Task 4.1 and Task 4.2 completion

## Dependencies

- `shared/models/participant.py`'s existing `ParticipantType` enum (no new values added)
- `alembic/versions/8438728f8184_replace_prefilled_position_with_.py` as the reference migration shape
- `uv run pytest tests/unit` (never `pytest --testmon` manually — see `CLAUDE.md`'s testmon warning)
- `uv run mypy shared/ services/`
- `cd frontend && npm run build` / `cd frontend && npm run test`
- `uv run alembic upgrade head` / `uv run alembic downgrade -1` for the new migration
- `scripts/run-integration-tests.sh` for `tests/integration/test_games_crud.py`

## Success Criteria

- `_update_prefilled_participants`/`_update_participant_positions` persist a
  position change for any participant referenced by `participant_id`,
  regardless of `position_type`, while `_remove_outdated_participants` stays
  scoped to `HOST_ADDED` rows only
- New self-added joins (API and bot paths) and the model's `server_default`
  all default `position` to `32767` instead of `0`; existing rows are
  backfilled by the new reversible migration
- `EditGame.tsx` submits the full "disturbed prefix" (every displayed
  participant at or above the highest explicitly-positioned index) via a
  single shared `buildParticipantsPayload` helper used by both
  `handleSubmit` and `handleSaveAndArchive`
- `HOST_SELECTED_WITH_WAITLIST`'s promotion logic and tests
  (`test_update_prefilled_promotes_self_added_participants`,
  `test_games_promotion.py`, `TestPartitionParticipants`) are unchanged
- No `host_added_dropout` DM fires for a repositioned-but-never-promoted
  `SELF_ADDED` participant leaving, nor for a `ROLE_MATCHED` participant
  converted to `SELF_ADDED` by an explicit reposition
- `ROLE_BASED` reordering is implemented, not left as an open question: an
  explicitly-repositioned `ROLE_MATCHED` participant converts to
  `SELF_ADDED` with an explicit `position` (Task 2.5), untouched
  `ROLE_MATCHED` participants keep their type and real priority-index
  `position` (Task 2.4), the resulting mixed-bucket sort order is correct
  and tested (Task 2.6), and the frontend requires no `ROLE_BASED`-specific
  change since `EditableParticipantList.tsx` already permits reordering
  `ROLE_MATCHED` rows identically to `SELF_ADDED` ones (Task 3.3)
- `shared/utils/participant_sorting.py` has zero diff — the `ROLE_BASED`
  decision is implemented entirely as a `position_type`/`position` mutation
  in `services/api/services/games.py`, not a change to sorting/partitioning
  logic
- `uv run pytest tests/unit`, `uv run mypy shared/ services/`,
  `cd frontend && npm run build`, `cd frontend && npm run test`, and
  `scripts/run-integration-tests.sh tests/integration/test_games_crud.py`
  all pass at the end of Phase 4
