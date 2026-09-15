---
applyTo: '.copilot-tracking/changes/20260915-01-clone-game-review-redesign-changes.md'
---

<!-- markdownlint-disable-file -->

# Task Checklist: Clone Game Review/Edit-Before-Create Redesign

## Overview

Replace `frontend/src/pages/CloneGame.tsx`'s bespoke small form with a `GameForm`-based, edit-before-create
clone screen, and rebuild `clone_game` as a thin orchestration layer that constructs a real
`GameCreateRequest` from the submitted clone form and delegates the entire mechanical pipeline (template
loading, host resolution, free-text mention/channel/emoji resolution, participant resolution and roster
creation, deferred/immediate publish) to `create_game`, adding back only two genuinely new, additive
behaviors: image carry-over-by-reference when no new file is uploaded, and deadline-carryover scheduling
re-derived from the submitted roster.

## Objectives

- Nothing is created server-side (no `GameSession`, no participants, no Discord announcement) until the
  host submits the redesigned clone form.
- `clone_game` builds a fully-resolved `GameCreateRequest`-shaped payload (reusing `source_game.template_id`)
  from the submitted `CloneGameRequest` + `source_game` fallbacks, with every field already final, and
  delegates to `create_game`'s real pipeline rather than re-implementing an override-diff/field-copy model.
- Delegating into `create_game` means clone now re-runs `create_game`'s own host-role-permission check
  against the carried-over/overridden host — a check today's `clone_game` skips entirely. This is
  intentional and implemented, not bypassed.
- The submitted participant list is authoritative for the new game's roster "for free" via `create_game`'s
  own `initial_participants` pipeline (no clone-specific roster-construction code remains); only
  deadline-carryover scheduling needs new, additive logic re-derived from the submitted list matched back
  to the source game's own confirmed/waitlist partition by `discord_id`.
- Every cloned game gets a concrete, working `post_at` (deferred vs. immediate publish) entirely as a
  side effect of delegation — no dedicated `post_at`/`AnnouncementLoop` migration phase is needed, unlike
  the sibling `post_at`-cleanup doc's original Part 7 scope, because `create_game`'s pipeline already
  implements it.
- Images continue to carry over by reference (`increment_image_ref`) when no new file is attached, but
  — because `GameForm`'s file-upload inputs are unconditionally rendered even in create mode — a host can
  also attach a genuinely new thumbnail/banner while cloning, which flows through `create_game`'s existing
  raw-upload path unchanged.
- A pre-existing regex gap in `resolve_mentions_in_text` (no exclusion for tokens already inside a
  resolved `<@discord_id>`) is fixed before delegation ships, since delegating unconditionally re-runs
  mention resolution against inherited free-text fields that may already contain resolved mentions.

## Research Summary

### Project Files

- `frontend/src/pages/CloneGame.tsx` - bespoke small form to be fully replaced with a `GameForm`-based,
  two-stage screen.
- `frontend/src/components/GameForm.tsx` - reused unmodified in `mode='create'`, prepopulated from a
  real fetched source game; no `channels`/`roles` fetch dependency beyond a synthesized single-item
  channel list.
- `services/api/schemas/clone_game.py` - `CloneGameRequest` gains override fields, `post_at`,
  `participants`; no `channel_id`, `rewards`, `allowed_player_role_ids`, or `notify_role_ids` fields
  (none of these are overridable anywhere in the system today, verified against current code).
- `services/api/services/games.py` - `clone_game` rewritten to delegate to `create_game`; `create_game`/
  `_resolve_game_host` gain a small additive `default_host_user_id` parameter; `_apply_deadline_carryover`
  and friends reused unchanged.
- `services/api/services/participant_resolver.py` - `resolve_mentions_in_text`'s regex gains a `(?<!<)`
  lookbehind (prerequisite fix for safe delegation).
- `services/api/routes/games.py` - `clone_game` route rewritten to multipart `Form()`/`File()`, mirroring
  `create_game`'s route; `_handle_game_operation_errors`'s type union widened.
- `shared/utils/participant_sorting.py` - `partition_participants`/`PartitionedParticipants` (unchanged,
  reused for source-side eligibility classification only).
- `shared/schemas/game.py` - `GameCreateRequest` as the field-shape template for the new `CloneGameRequest`
  fields, and as documentation of exactly which fields `create_game` does/does not support overriding
  (notably: no `channel_id`, no `rewards`).
- `tests/unit/schemas/test_clone_game_schema.py`, `tests/unit/services/test_clone_game.py`,
  `tests/unit/services/api/services/test_participant_resolver.py`, `tests/unit/services/api/services/test_games_service.py`,
  `tests/integration/test_clone_game_endpoint.py`, `tests/e2e/test_clone_game_e2e.py`,
  `frontend/src/pages/__tests__/CloneGame.test.tsx` - all require rewrites/extensions per phase.

### External References

- .copilot-tracking/research/20260915-01-clone-game-review-redesign-research.md - primary research. The
  "Backend architecture revision: reuse `create_game`'s pipeline instead of an override-diff schema"
  section (lines 159-176) is authoritative and supersedes this document's own "Central open question"
  (lines 106-117), "Technical Requirements" (177-186), and "Implementation Guidance" (191-203) sections.
- .copilot-tracking/research/20260911-01-game-posting-schedule-cleanup-research.md - sibling research;
  cited for historical motivation only. Its Part 7 recommendation is satisfied entirely as a side effect
  of delegating to `create_game` (verified in this planning session: `create_game`'s existing
  `_persist_and_publish` already implements the deferred/immediate-publish branch Part 7 calls for).

### Standards References

- .github/instructions/python.instructions.md, .github/instructions/test-driven-development.instructions.md,
  .github/instructions/unit-tests.instructions.md - apply to all `services/api/schemas/clone_game.py`,
  `services/api/services/games.py`, and `services/api/services/participant_resolver.py` changes.
- .github/instructions/fastapi-transaction-patterns.instructions.md - `services/api/services/games.py`
  is in its explicit scope path.
- .github/instructions/reactjs.instructions.md, .github/instructions/typescript-5-es2022.instructions.md -
  apply to `CloneGame.tsx` changes.

## Implementation Checklist

### [x] Phase 1: Fix `resolve_mentions_in_text`'s Regex To Skip Already-Resolved `<@id>` Tokens

- [x] Task 1.1: Add a `(?<!<)` lookbehind to the mention-token regex, matching the existing pattern in
      `channel_resolver.py`'s `#`-mention regex; add regression tests
  - Details: .copilot-tracking/planning/details/20260915-01-clone-game-review-redesign-details.md (Lines 155-180)

### [ ] Phase 2: Extend `CloneGameRequest` With Override Fields, `post_at`, and `participants`

- [ ] Task 2.1: Add the 13 new optional fields (no `channel_id`, `rewards`, `allowed_player_role_ids`, or
      `notify_role_ids` — none are overridable anywhere in the system)
  - Details: .copilot-tracking/planning/details/20260915-01-clone-game-review-redesign-details.md (Lines 182-225)
- [ ] Task 2.2: TDD cycle for the new schema tests
  - Details: .copilot-tracking/planning/details/20260915-01-clone-game-review-redesign-details.md (Lines 227-236)

### [ ] Phase 3: Add `default_host_user_id` To `create_game`/`_resolve_game_host`

- [ ] Task 3.1: Thread a separate default-host identity through host resolution so the bot-manager
      permission-check subject (`current_user`) and the default host (`source_game.host_id`) can differ
  - Details: .copilot-tracking/planning/details/20260915-01-clone-game-review-redesign-details.md (Lines 238-305)

### [ ] Phase 4: Rewrite `clone_game` To Delegate To `create_game`; Wire Route-Level `ValidationError` Handling

- [ ] Task 4.1: Replace `clone_game`'s body with a `create_game` delegation plus unconditional
      image-reference carry-over; widen `_handle_game_operation_errors`'s type union; rewrite the route's
      try/except
  - Details: .copilot-tracking/planning/details/20260915-01-clone-game-review-redesign-details.md (Lines 307-501)
- [ ] Task 4.2: TDD cycle and test-file restructuring (mock `self.create_game` rather than every internal
      DB call it makes)
  - Details: .copilot-tracking/planning/details/20260915-01-clone-game-review-redesign-details.md (Lines 472-502)

### [ ] Phase 5: Re-Add Deadline-Carryover Scheduling (Additive, Submitted-List-Driven)

- [ ] Task 5.1: Compute carryover-eligible groups from the source game's own partition, filtered to the
      final submitted roster by `discord_id`, and call `_apply_deadline_carryover` unchanged
  - Details: .copilot-tracking/planning/details/20260915-01-clone-game-review-redesign-details.md (Lines 504-566)

### [ ] Phase 6: Multipart Route + Raw Image Upload, With Ref-Copy Fallback

- [ ] Task 6.1: `clone_game` accepts raw image bytes forwarded to `create_game`; ref-copy becomes
      conditional on "no new file uploaded"
  - Details: .copilot-tracking/planning/details/20260915-01-clone-game-review-redesign-details.md (Lines 568-608)
- [ ] Task 6.2: Rewrite the clone route to multipart `Form()`/`File()`, mirroring `create_game`'s route
  - Details: .copilot-tracking/planning/details/20260915-01-clone-game-review-redesign-details.md (Lines 610-684)

### [ ] Phase 7: Full Integration Test Pass Against the New Request Contract

- [ ] Task 7.1: Expand `tests/integration/test_clone_game_endpoint.py` to exercise overrides, host
      override and its new permission recheck, submitted-participant roster/deadline behavior, image
      upload vs. ref-copy, and `post_at` deferred/immediate behavior end-to-end
  - Details: .copilot-tracking/planning/details/20260915-01-clone-game-review-redesign-details.md (Lines 686-709)

### [ ] Phase 8: Rebuild `CloneGame.tsx` — Two-Stage `GameForm`-Based Screen

- [ ] Task 8.1: Stub the two-stage page shape (carryover/deadline preamble → frozen-`initialData`
      `GameForm` mount, no `/channels` or `/roles` fetch needed) and write failing (`test.failing`)
      component tests, deleting the 16 tests against the old bespoke UI
  - Details: .copilot-tracking/planning/details/20260915-01-clone-game-review-redesign-details.md (Lines 711-766)
- [ ] Task 8.2: Implement Stage 1/Stage 2 rendering; remove `test.failing` markers
  - Details: .copilot-tracking/planning/details/20260915-01-clone-game-review-redesign-details.md (Lines 768-776)
- [ ] Task 8.3: Refactor and add edge-case tests (`HOST_SELECTED_WITH_WAITLIST` source, image-carryover
      no-crash, fetch-error/loading states)
  - Details: .copilot-tracking/planning/details/20260915-01-clone-game-review-redesign-details.md (Lines 778-788)

### [ ] Phase 9: Wire `CloneGame.tsx`'s Submit Handler to the Extended Clone Endpoint

- [ ] Task 9.1: Write failing submit-handler tests covering the full `GameFormData` → multipart
      `CloneGameRequest` field mapping (including raw file uploads) and the `invalid_mentions`
      error-handling path
  - Details: .copilot-tracking/planning/details/20260915-01-clone-game-review-redesign-details.md (Lines 790-820)
- [ ] Task 9.2: Implement the submit handler; remove `test.failing` markers
  - Details: .copilot-tracking/planning/details/20260915-01-clone-game-review-redesign-details.md (Lines 822-828)
- [ ] Task 9.3: Refactor and full end-to-end frontend flow verification
  - Details: .copilot-tracking/planning/details/20260915-01-clone-game-review-redesign-details.md (Lines 830-838)

### [ ] Phase 10: Update the E2E Test to Reflect Title-At-Clone-Time

- [ ] Task 10.1: Remove the post-clone rename workaround from `tests/e2e/test_clone_game_e2e.py`; set the
      title directly via the clone request's override field
  - Details: .copilot-tracking/planning/details/20260915-01-clone-game-review-redesign-details.md (Lines 840-857)

## Dependencies

- Python: pytest, mypy, Pydantic v2, SQLAlchemy async (existing project stack, no new packages).
- TypeScript/React: Vitest/RTL, MUI `DateTimePicker`/`Select`, existing `GameForm`/`EditableParticipantList`
  components (unmodified).
- No new database migration required.
- Phase ordering (restated from the details file): Phase 1 must precede Phase 4 (safe delegation for
  inherited free-text fields depends on the regex fix); Phase 2 must precede Phase 4 (schema fields must
  exist before `clone_game` reads them); Phase 3 must precede Phase 4 (`default_host_user_id` parameter);
  Phase 4 must precede Phase 5 (deadline-carryover needs the delegated `new_game`); Phases 4-5 must
  precede Phase 6 (the route rewrite should happen once, after the service body is stable); Phase 7
  depends on Phases 1-6; Phases 8-9 (frontend) depend on Phase 2's final field names and Phase 6's final
  multipart contract; Phase 10 depends on all prior phases.

## Success Criteria

- A host can clone a game, edit every `GameForm`-exposed field plus the clone-specific carryover/deadline
  options and the participant roster, and submit once — nothing is created server-side before that
  submit.
- `clone_game` contains no re-implemented host-resolution, template-loading, free-text-resolution, or
  participant-roster-construction logic — all of it is delegated to `create_game`; only image
  ref-copy-vs-upload and deadline-carryover-eligibility remain as clone-specific additive code.
- The host-role-permission recheck against the carried-over/overridden host is implemented as an
  intentional, tested behavior change, not bypassed.
- The submitted participant list is authoritative for the new game's roster; deadline-carryover
  reconfirmation is created only for participants present in both the submission and the source game's
  matching carryover-eligible group (matched by discord_id).
- Every cloned game has a concrete, non-NULL `post_at`; the "Schedule Posting" picker is fully functional;
  cloning still posts its Discord announcement correctly, entirely via delegation to `create_game`.
- `uv run pytest tests/unit`, `uv run mypy shared/ services/`, `cd frontend && npm run build`,
  `cd frontend && npm run test` all pass; updated integration/e2e suites pass per
  `.github/instructions/test-execution.instructions.md`.
