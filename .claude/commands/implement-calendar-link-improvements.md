---
description: 'Implement the Google Calendar quick-add embed link and the mint-token public .ics route/frontend migration'
---

<!-- markdownlint-disable-file -->

# Implementation Prompt: Discord Embed Calendar Link Improvements

## Implementation Instructions

### Step 1: Create Changes Tracking File

You WILL create `20260816-01-calendar-link-improvements-changes.md` in `.copilot-tracking/changes/` if it does not exist.

### Step 2: Execute Implementation

You WILL follow `.github/instructions/task-implementation.instructions.md`
You WILL systematically implement `.copilot-tracking/planning/plans/20260816-01-calendar-link-improvements.plan.md` task-by-task
You WILL follow ALL project standards and conventions:

- `.github/instructions/python.instructions.md` for all Python code (Phases 1-5)
- `.github/instructions/test-driven-development.instructions.md` for the RED→GREEN→REFACTOR cycle on every task
- `.github/instructions/unit-tests.instructions.md` for exact-value/call-argument assertions
- `.github/instructions/fastapi-transaction-patterns.instructions.md` and `.github/instructions/api-authorization.instructions.md` for Phases 4-5
- `.github/instructions/integration-tests.instructions.md` and `.github/instructions/test-execution.instructions.md` for Phase 5's integration tests
- `.github/instructions/reactjs.instructions.md` and `.github/instructions/typescript-5-es2022.instructions.md` for Phases 6-7
- `.github/instructions/self-explanatory-code-commenting.instructions.md` for commenting style

**CRITICAL**: By default, you WILL stop after each Phase and each Task for user review. The user may tell you at the start of the session (or at any point) to run through multiple phases or tasks without stopping — follow whatever cadence they specify instead of this default.
**CRITICAL**: You WILL NOT commit changes unless the user explicitly tells you to commit. Completing a phase does NOT trigger a commit. Announce that the phase is complete and wait for the user to say "commit" or similar before running `git commit`.

When the user does request a commit, use this format for phase commits:

```
feat: Phase N - {{description, including feature context if non-obvious}}

- {{change bullet 1}}
- {{change bullet 2}}

Rationale: {{why this phase does what it does}}
```

**CRITICAL**: Before marking any Phase complete or committing its changes, you MUST verify ALL pre-commit gates pass:

- `uv run pytest tests/unit` — Python unit tests (Phases 1-5)
- `uv run mypy shared/ services/` — type checking; mypy failures block commits exactly like test failures (Phases 1-5)
- `cd frontend && npm run build` — TypeScript build (Phases 6-7, and any phase touching frontend files)
- `cd frontend && npm run test` — frontend tests (Phases 6-7)
- `scripts/run-integration-tests.sh |& tee output-integration.txt` — Phase 5 (writes new integration tests); follow `.github/instructions/test-execution.instructions.md` for output capture rules
- `scripts/run-e2e-tests.sh |& tee output-e2e.txt` — only if Phase 2's optional Task 2.3 (e2e coverage) is done

A phase is not done until all applicable gates are green. Writing tests and committing them without executing them is a pre-commit gate failure.

**Note on `.testmondata`**: Never run `pytest --testmon` manually — always run `uv run pytest tests/unit` without `--testmon`. If a pre-commit hook run leaves `.testmondata` stale, delete it (`rm .testmondata`) before retrying the commit.

### Step 3: Cleanup

When ALL Phases are checked off (`[x]`) and completed you WILL do the following:

1. You WILL provide a markdown style link and a summary of all changes from `.copilot-tracking/changes/20260816-01-calendar-link-improvements-changes.md` to the user:
   - You WILL keep the overall summary brief
   - You WILL add spacing around any lists
   - You MUST wrap any reference to a file in a markdown style link

2. You WILL provide markdown style links to `.copilot-tracking/planning/plans/20260816-01-calendar-link-improvements.plan.md`, `.copilot-tracking/planning/details/20260816-01-calendar-link-improvements-details.md`, and `.copilot-tracking/research/20260816-01-calendar-link-improvements-research.md` documents. You WILL recommend cleaning these files up as well.

## Success Criteria

- [ ] Changes tracking file created
- [ ] All plan items implemented with working code
- [ ] All detailed specifications satisfied
- [ ] Project conventions followed
- [ ] All relevant coding conventions followed
- [ ] All new and modified code passes lint and has unit tests
- [ ] Changes file updated continuously
- [ ] Line numbers updated if any referenced files changed
