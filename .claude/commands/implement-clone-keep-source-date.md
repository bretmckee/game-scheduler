---
description: 'Implement Clone Game keeping the source date, with server and form guards against past dates'
---

<!-- markdownlint-disable-file -->

# Implementation Prompt: Clone Game — Keep Source Date

## Implementation Instructions

### Step 1: Create Changes Tracking File

You WILL create `20261123-01-clone-keep-source-date-changes.md` in `.copilot-tracking/planning/changes/` if it does not exist.

### Step 2: Execute Implementation

You WILL follow `.github/instructions/task-implementation.instructions.md`
You WILL systematically implement `.copilot-tracking/planning/plans/20261123-01-clone-keep-source-date.plan.md` task-by-task
You WILL follow ALL project standards and conventions:

- `.github/instructions/python.instructions.md` for all Python code
- `.github/instructions/test-driven-development.instructions.md` for the RED (xfail / `it.fails`) → GREEN flow in Phases 2–4
- `.github/instructions/unit-tests.instructions.md` for all unit tests
- `.github/instructions/reactjs.instructions.md` and `.github/instructions/typescript-5-es2022.instructions.md` for frontend code
- `.github/instructions/self-explanatory-code-commenting.instructions.md` for commenting style

**CRITICAL**: By default, you WILL stop after each Phase and each Task for user review. The user may tell you at the start of the session (or at any point) to run through multiple phases or tasks without stopping. Follow whatever cadence they specify instead of this default.
**CRITICAL**: You WILL NOT commit changes unless the user explicitly tells you to commit. Completing a phase does NOT trigger a commit. Announce that the phase is complete and wait for the user to say "commit" or similar before running `git commit`.
**CRITICAL**: Never run `pytest --testmon` manually. Use `uv run pytest tests/unit`.

When the user does request a commit, use this format for phase commits:

```
feat: Phase N - {description, including feature context if non-obvious}

- {change bullet 1}
- {change bullet 2}

Rationale: {why this phase does what it does}
```

**CRITICAL**: Before marking any Phase complete or committing its changes, you MUST verify ALL pre-commit gates pass:

- `uv run pytest tests/unit` — Python unit tests
- `uv run mypy shared/ services/` — type checking (mypy failures block commits exactly like test failures)
- `cd frontend && npm run build` — TypeScript build (Phases 3–4)
- `cd frontend && npm run test` — frontend tests (Phases 3–4)
- `scripts/run-integration-tests.sh |& tee output-integration.txt` — Phases 1–2 (integration tests are written or modified); use the scoping args and follow `.github/instructions/test-execution.instructions.md`
- `scripts/run-e2e-tests.sh |& tee output-e2e.txt` — only if tests/e2e/test_clone_game_e2e.py is modified

A phase is not done until all applicable gates are green. Writing tests and committing them without executing them is a pre-commit gate failure.

### Step 3: Cleanup

When ALL Phases are checked off (`[x]`) and completed you WILL do the following:

1. You WILL provide a markdown style link and a summary of all changes from `.copilot-tracking/planning/changes/20261123-01-clone-keep-source-date-changes.md` to the user:
   - You WILL keep the overall summary brief
   - You WILL add spacing around any lists
   - You MUST wrap any reference to a file in a markdown style link

2. You WILL provide markdown style links to `.copilot-tracking/planning/plans/20261123-01-clone-keep-source-date.plan.md`, `.copilot-tracking/planning/details/20261123-01-clone-keep-source-date-details.md`, and `.copilot-tracking/research/20261122-01-clone-keep-source-date-research.md` documents. You WILL recommend cleaning these files up as well.

## Success Criteria

- [ ] Changes tracking file created
- [ ] All plan items implemented with working code
- [ ] All detailed specifications satisfied
- [ ] Project conventions followed
- [ ] All relevant coding conventions followed
- [ ] All new and modified code passes lint and has unit tests
- [ ] Changes file updated continuously
- [ ] Line numbers updated if any referenced files changed
