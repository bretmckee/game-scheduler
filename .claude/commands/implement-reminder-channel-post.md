---
description: 'Implement hybrid game reminder delivery: channel/thread post for confirmed + host, waitlist DM, full DM fallback'
---

<!-- markdownlint-disable-file -->

# Implementation Prompt: Move Game Reminders from DMs to Location Channel/Thread Posts

## Task Overview

Deliver game reminders as a single post in the game's location channel/thread
(mentioning confirmed participants + host) when `where` resolves to exactly one
channel, plus a DM to the first waitlisted participant. Preserve the existing
full DM fan-out (confirmed + first waitlisted + host) as a fallback when the
location is empty/ambiguous or the channel post fails. No schema, queue, or API
changes.

## Implementation Instructions

### Step 1: Create Changes Tracking File

You WILL create `20260823-01-reminder-channel-post-changes.md` in
`.copilot-tracking/changes/` if it does not exist.

### Step 2: Execute Implementation

You WILL follow `.github/instructions/task-implementation.instructions.md`
You WILL systematically implement
`.copilot-tracking/planning/plans/20260823-01-reminder-channel-post.plan.md`
task-by-task
You WILL follow ALL project standards and conventions:

- `.github/instructions/python.instructions.md` for all Python code
- `.github/instructions/test-driven-development.instructions.md` for the
  RED→GREEN→REFACTOR cycle (stubs land in the same phase as the tests that
  import them)
- `.github/instructions/unit-tests.instructions.md` for behavioral assertions
  on real arguments (no coverage theater)
- `.github/instructions/self-explanatory-code-commenting.instructions.md` for
  commenting style
- `.github/instructions/test-execution.instructions.md` for e2e output capture

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
- `scripts/run-e2e-tests.sh tests/e2e/test_game_reminder.py |& tee output-e2e.txt`
  — for Phase 3 only; follow `.github/instructions/test-execution.instructions.md`
  for output capture rules (≥900000ms timeout)

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

- [ ] Changes tracking file created
- [ ] All plan items implemented with working code
- [ ] All detailed specifications satisfied
- [ ] Project conventions followed
- [ ] All relevant coding conventions followed
- [ ] All new and modified code passes lint and has unit tests
- [ ] Changes file updated continuously
- [ ] Line numbers updated if any referenced files changed
