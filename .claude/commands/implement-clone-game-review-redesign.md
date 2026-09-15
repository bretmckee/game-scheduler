---
description: 'Implement the clone-game review/edit-before-create redesign (GameForm-based clone screen, CloneGameRequest delegating to create_game, submitted-list-driven deadline carryover, real post_at via delegation)'
---

<!-- markdownlint-disable-file -->

# Implementation Prompt: Clone Game Review/Edit-Before-Create Redesign

## Implementation Instructions

### Step 1: Create Changes Tracking File

You WILL create `20260915-01-clone-game-review-redesign-changes.md` in `.copilot-tracking/changes/` if
it does not exist.

### Step 2: Execute Implementation

You WILL follow `.github/instructions/task-implementation.instructions.md`
You WILL systematically implement `.copilot-tracking/planning/plans/20260915-01-clone-game-review-redesign.plan.md`
task-by-task
You WILL follow ALL project standards and conventions:

- `.github/instructions/python.instructions.md` for all Python code
- `.github/instructions/test-driven-development.instructions.md` and
  `.github/instructions/unit-tests.instructions.md` for every phase (backend Python phases 1-6 and
  frontend TypeScript phases 8-9 both require RED→GREEN→REFACTOR; phases 7 and 10 are integration/e2e and
  do not require stubs/xfail markers)
- `.github/instructions/fastapi-transaction-patterns.instructions.md` for `services/api/services/games.py`,
  `services/api/services/participant_resolver.py`, and `services/api/routes/games.py`
- `.github/instructions/reactjs.instructions.md` and `.github/instructions/typescript-5-es2022.instructions.md`
  for `frontend/src/pages/CloneGame.tsx`
- `.github/instructions/self-explanatory-code-commenting.instructions.md` for commenting style

**CRITICAL**: By default, you WILL stop after each Phase and each Task for user review. The user may
tell you at the start of the session (or at any point) to run through multiple phases or tasks without
stopping — follow whatever cadence they specify instead of this default.
**CRITICAL**: You WILL NOT commit changes unless the user explicitly tells you to commit. Completing a
phase does NOT trigger a commit. Announce that the phase is complete and wait for the user to say
"commit" or similar before running `git commit`.

When the user does request a commit, use this format for phase commits:

```
feat: Phase N - {{description, including feature context if non-obvious}}

- {{change bullet 1}}
- {{change bullet 2}}

Rationale: {{why this phase does what it does}}
```

**CRITICAL**: Before marking any Phase complete or committing its changes, you MUST verify ALL pre-commit
gates pass:

- `uv run pytest tests/unit` — Python unit tests
- `uv run mypy shared/ services/` — type checking (mypy failures block commits exactly like test
  failures)
- `cd frontend && npm run build` — TypeScript build (Phases 8-9 change frontend files)
- `cd frontend && npm run test` — frontend tests (Phases 8-9 change frontend files)
- `scripts/run-integration-tests.sh |& tee output-integration.txt` — for Phases 4, 6, 7 (they write or
  modify integration tests); follow `.github/instructions/test-execution.instructions.md` for output
  capture rules
- `scripts/run-e2e-tests.sh |& tee output-e2e.txt` — for Phase 10; follow
  `.github/instructions/test-execution.instructions.md` for output capture rules

A phase is not done until all applicable gates are green. Writing tests and committing them without
executing them is a pre-commit gate failure.

**Never run `pytest --testmon` or `pytest --testmon-nocollect` manually** — use
`uv run pytest tests/unit` per `.github/instructions` conventions; running testmon manually desyncs the
pre-commit diff-coverage hook.

**Note on Phase 4's test-file restructuring**: `tests/unit/services/test_clone_game.py`'s existing
fixtures mock the entire `db` object with one generic return value from every `db.execute(...)` call.
Once `clone_game` delegates to `create_game` (which makes many distinct, differently-shaped DB calls),
that fixture pattern no longer works. Per the details file, restructure these tests to mock
`self.create_game` directly (verifying `clone_game`'s own orchestration: permission gate, constructed
`GameCreateRequest` payload, `default_host_user_id`/`host_user_id` split, additive image/deadline steps)
rather than re-mocking every one of `create_game`'s internal DB round-trips. Full-pipeline behaviors
(template loading, real mention resolution, real role checks) belong in the integration suite (Phase 7),
not in this mock-based unit file.

### Step 3: Cleanup

When ALL Phases are checked off (`[x]`) and completed you WILL do the following:

1. You WILL provide a markdown style link and a summary of all changes from
   `.copilot-tracking/changes/20260915-01-clone-game-review-redesign-changes.md` to the user:
   - You WILL keep the overall summary brief
   - You WILL add spacing around any lists
   - You MUST wrap any reference to a file in a markdown style link

2. You WILL provide markdown style links to
   `.copilot-tracking/planning/plans/20260915-01-clone-game-review-redesign.plan.md`,
   `.copilot-tracking/planning/details/20260915-01-clone-game-review-redesign-details.md`,
   `.copilot-tracking/research/20260915-01-clone-game-review-redesign-research.md`, and
   `.copilot-tracking/research/20260911-01-game-posting-schedule-cleanup-research.md`. You WILL
   recommend cleaning these files up as well (noting that the sibling research/plan doc's remaining
   Parts 2/6/8 — picker-affordance fix, sender unification, dead-code deletion, new metric — remain
   unimplemented and out of scope for this effort, and would need their own future planning pass if
   still desired).

## Success Criteria

- [ ] Changes tracking file created
- [ ] All 10 plan phases implemented with working code, each independently committable
- [ ] All detailed specifications in the details file satisfied
- [ ] Project conventions followed, including TDD RED→GREEN→REFACTOR for every new/enhanced production
      code phase (1-6, 8-9) and no-stub/no-xfail tests for integration/e2e phases (7, 10)
- [ ] `clone_game` delegates its entire mechanical pipeline to `create_game`; no re-implemented
      host-resolution, template-loading, free-text-resolution, or roster-construction logic remains in
      `clone_game` itself
- [ ] `resolve_mentions_in_text`'s regex fix lands before `clone_game` starts delegating to `create_game`
- [ ] `default_host_user_id` correctly decouples the bot-manager-permission-check subject from the
      default-host-when-omitted value
- [ ] The host-role-permission recheck against the carried-over/overridden host is implemented as an
      intentional behavior change, not bypassed
- [ ] Every cloned game has a concrete, non-NULL `post_at`, and the redesigned clone screen's
      "Schedule Posting" picker is fully wired, not a no-op — achieved via delegation, with no dedicated
      publish/announcement code added to `clone_game`
- [ ] All new and modified code passes lint, mypy, and has unit tests
- [ ] Changes file updated continuously
- [ ] Line numbers updated in planning files if any referenced source files changed materially during
      implementation
