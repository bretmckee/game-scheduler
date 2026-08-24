---
mode: agent
model: Claude Sonnet 4.6
---

<!-- markdownlint-disable-file -->

# Implementation Prompt: Move Game Reminders from DMs to Location Channel/Thread Posts (+ Host DM-Only Opt-Out)

## Task Overview

Phases 1–3 (hybrid channel-post + waitlist DM delivery, e2e rewrite) are
already implemented and committed on `develop`. This prompt covers the
remaining extension phases 4–6: a per-game "Always send reminders as DMs"
checkbox (default off, game-only) that short-circuits the location-channel
resolution so every reminder takes the full DM fan-out path.

## Implementation Instructions

### Step 1: Create Changes Tracking File

You WILL create `20260823-01-reminder-channel-post-changes.md` in
`.copilot-tracking/changes/` if it does not exist. It already exists with
Phase 1–3 entries — append new phase sections rather than rewriting history.

### Step 2: Execute Implementation

You WILL follow `.github/instructions/task-implementation.instructions.md`
You WILL systematically implement
`.copilot-tracking/planning/plans/20260823-01-reminder-channel-post.plan.md`
task-by-task, starting at Phase 4 (Phases 1–3 are complete and checked off).
You WILL follow ALL project standards and conventions:

- `.github/instructions/python.instructions.md` for all Python code
- `.github/instructions/test-driven-development.instructions.md` for the
  RED→GREEN→REFACTOR cycle
- `.github/instructions/unit-tests.instructions.md` for behavioral assertions
  on real arguments (no coverage theater)
- `.github/instructions/reactjs.instructions.md` +
  `.github/instructions/typescript-5-es2022.instructions.md` for frontend work
- `.github/instructions/self-explanatory-code-commenting.instructions.md` for
  commenting style
- `.github/instructions/containerization-docker-best-practices.instructions.md`
  is NOT applicable (no Docker changes)

**CRITICAL**: By default, you WILL stop after each Phase and each Task for user
review. The user may tell you at the start of the session (or at any point) to
run through multiple phases or tasks without stopping — follow whatever cadence
they specify instead of this default.
**CRITICAL**: You WILL NOT commit changes unless the user explicitly tells you
to commit. Completing a phase does NOT trigger a commit. Announce that the
phase is complete and wait for the user to say "commit" or similar before
running `git commit`.

When the user does request a commit, use this format for phase commits:

```
feat: Phase N - {{description, including feature context if non-obvious}}

- {{change bullet 1}}
- {{change bullet 2}}

Rationale: {{why this phase does what it does}}
```

**CRITICAL**: Before marking any Phase complete or committing its changes, you
MUST verify ALL pre-commit gates pass:

- `uv run pytest tests/unit` — Python unit tests
- `uv run mypy shared/ services/` — type checking (mypy failures block commits
  exactly like test failures)
- `cd frontend && npm run build` — TypeScript build (Phase 6; any frontend change)
- `cd frontend && npm run test` — frontend unit tests (Phase 6; any frontend change)
- Integration tests (`scripts/run-integration-tests.sh |& tee output-integration.txt`)
  only if Task 4.3's integration coverage requires verification in this session;
  follow `.github/instructions/test-execution.instructions.md` for output capture
  rules (≥600000ms timeout)

A phase is not done until all applicable gates are green. Writing tests and
committing them without executing them is a pre-commit gate failure.

### Step 3: Cleanup

When ALL Phases are checked off (`[x]`) and completed you WILL do the following:

1. You WILL provide a markdown style link and a summary of all changes from
   `.copilot-tracking/changes/20260823-01-reminder-channel-post-changes.md` to
   the user:
   - You WILL keep the overall summary brief
   - You WILL add spacing around any lists
   - You MUST wrap any reference to a file in a markdown style link

2. You WILL provide markdown style links to
   `.copilot-tracking/planning/plans/20260823-01-reminder-channel-post.plan.md`,
   `.copilot-tracking/planning/details/20260823-01-reminder-channel-post-details.md`,
   and
   `.copilot-tracking/research/20260823-01-reminder-channel-post-research.md`
   documents. You WILL recommend cleaning these files up as well.

## Success Criteria

- [ ] Changes tracking file updated with Phase 4–6 entries
- [ ] All plan items implemented with working code
- [ ] All detailed specifications satisfied
- [ ] Project conventions followed
- [ ] All relevant coding conventions followed
- [ ] All new and modified code passes lint and has unit tests
- [ ] Changes file updated continuously
- [ ] Line numbers updated if any referenced files changed
