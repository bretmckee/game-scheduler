---
description: 'Implement the test-assertion-quality plan: checker fix, hollow provider assertion cleanup, allowlist trim, docs'
---

<!-- markdownlint-disable-file -->

# Implementation Prompt: Test Assertion Quality

## Implementation Instructions

### Step 1: Create Changes Tracking File

You WILL create `20261109-01-test-assertion-quality-changes.md` in `.copilot-tracking/planning/changes/` if it does not exist.

### Step 2: Execute Implementation

You WILL follow `.github/instructions/task-implementation.instructions.md`
You WILL systematically implement `.copilot-tracking/planning/plans/20261109-01-test-assertion-quality.plan.md` task-by-task, using `.copilot-tracking/planning/details/20261109-01-test-assertion-quality-details.md` for specifications.
You WILL follow ALL project standards and conventions:

- `.github/instructions/python.instructions.md` for all Python code
- `.github/instructions/unit-tests.instructions.md` for all test edits
- `.github/instructions/test-driven-development.instructions.md` (Phases 1-2 are TDD; Phases 3-5 are retrofits, no xfail)
- `.github/instructions/quality-check-overrides.instructions.md` for `# assert-not-weak:` markers and `APPROVED_WEAK_ASSERTIONS`
- `.github/instructions/self-explanatory-code-commenting.instructions.md` for commenting style

Rules specific to this task:

- Never weaken a real assertion while removing a hollow one.
- Do not trim `no-arg-methods` before Task 5.2; earlier phases must pass the hook under the old allowlist.
- Never run `pytest --testmon`.

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

- `uv run pytest tests/unit` — Python unit tests
- `uv run mypy shared/ services/` — type checking
- `uv run python scripts/check_test_assertions.py <touched test files>` — assertion checker (use `--all` in Phase 5)
- Frontend gates and integration/e2e scripts are not expected (no frontend or integration tests change)

A phase is not done until all applicable gates are green.

### Step 3: Cleanup

When ALL Phases are checked off (`[x]`) you WILL:

1. Provide a markdown link and brief summary of `.copilot-tracking/planning/changes/20261109-01-test-assertion-quality-changes.md`, with spacing around lists and every file reference as a markdown link.
2. Provide markdown links to the plan, details, and research files (`.copilot-tracking/planning/plans/20261109-01-test-assertion-quality.plan.md`, `.copilot-tracking/planning/details/20261109-01-test-assertion-quality-details.md`, `.copilot-tracking/research/20261109-01-test-assertion-quality-research.md`) and recommend cleaning them up.

## Success Criteria

- [ ] Changes tracking file created and kept current
- [ ] All plan items implemented; each phase independently committable
- [ ] `uv run python scripts/check_test_assertions.py --all` reports no violations
- [ ] Marker count in tests/ is 19; unit tests and mypy pass
- [ ] Docs updated to match checker behavior
