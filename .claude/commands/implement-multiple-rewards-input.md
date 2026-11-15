---
description: 'Implement the multiple reward entries plan (JSON list storage, embed fit-or-link, list form UI)'
---

<!-- markdownlint-disable-file -->

# Implementation Prompt: Multiple Reward Entries Input

## Implementation Instructions

### Step 1: Create Changes Tracking File

Create `20261115-01-multiple-rewards-input-changes.md` in `.copilot-tracking/planning/changes/` if it does not exist.

### Step 2: Execute Implementation

Follow `.github/instructions/task-implementation.instructions.md`.
Systematically implement `.copilot-tracking/planning/plans/20261115-01-multiple-rewards-input.plan.md` task-by-task (details in `.copilot-tracking/planning/details/20261115-01-multiple-rewards-input-details.md`).
Follow ALL project standards:

- `.github/instructions/python.instructions.md`
- `.github/instructions/test-driven-development.instructions.md`
- `.github/instructions/reactjs.instructions.md` for frontend
- `.github/instructions/self-explanatory-code-commenting.instructions.md`

**CRITICAL**: By default, stop after each Phase and each Task for user review unless the user specifies another cadence.
**CRITICAL**: Do NOT commit unless the user explicitly asks. Phase completion does not trigger a commit. Never run `pytest --testmon`.

Phase commit format when requested:

```
feat: Phase N - {description}

- {change bullet}

Rationale: {why}
```

**CRITICAL**: Before marking a Phase complete, ALL applicable gates must pass:

- `uv run pytest tests/unit`
- `uv run mypy shared/ services/`
- `cd frontend && npm run build` and `npm run test` (if frontend changed)
- `scripts/run-integration-tests.sh |& tee output-integration.txt` (Phase 1 and any integration test change)
- `scripts/run-e2e-tests.sh |& tee output-e2e.txt` (Task 2.3 and any e2e change)

Follow `.github/instructions/test-execution.instructions.md` for output capture.

### Step 3: Cleanup

When all Phases are checked off:

1. Give a brief summary of `.copilot-tracking/planning/changes/20261115-01-multiple-rewards-input-changes.md` with markdown links to files.
2. Link the plan, details, and `.copilot-tracking/research/20261115-01-multiple-rewards-input-research.md` and recommend cleaning them up.

## Success Criteria

- [ ] Changes tracking file created and kept current
- [ ] All plan items implemented with tests (TDD)
- [ ] All pre-commit gates green per phase
- [ ] Project conventions followed
