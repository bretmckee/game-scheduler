---
mode: agent
model: Claude Sonnet 4.6
---

<!-- markdownlint-disable-file -->

# Implementation Prompt: HOST_SELECTED_WITH_WAITLIST signup mode

## Implementation Instructions

### Step 1: Create Changes Tracking File

Create `.copilot-tracking/changes/20260530-01-host-selected-waitlist-changes.md`
if it does not exist.

### Step 2: Execute Implementation

Follow #file:../../.github/instructions/task-implementation.instructions.md

Implement #file:../plans/20260530-01-host-selected-waitlist.plan.md task-by-task,
consulting #file:../details/20260530-01-host-selected-waitlist-details.md for
full specifications of each task.

Follow ALL project standards and conventions:

- #file:../../.github/instructions/python.instructions.md for all Python code
- #file:../../.github/instructions/test-driven-development.instructions.md for TDD RED/GREEN/REFACTOR
- #file:../../.github/instructions/unit-tests.instructions.md for test quality
- #file:../../.github/instructions/typescript-5-es2022.instructions.md for TypeScript
- #file:../../.github/instructions/reactjs.instructions.md for React/frontend
- #file:../../.github/instructions/self-explanatory-code-commenting.instructions.md for commenting
- #file:../../.github/instructions/taming-copilot.instructions.md for interaction patterns

**CRITICAL**: If ${input:phaseStop:true} is true, stop after each Phase for user review.
**CRITICAL**: If ${input:taskStop:true} is true, stop after each Task for user review.
**CRITICAL**: Before marking any Phase complete or committing its changes, verify ALL pre-commit gates pass:

- `uv run pytest tests/unit` — Python unit tests
- `uv run mypy shared/ services/` — type checking (mypy failures block commits)
- `cd frontend && npm run build` — TypeScript build (if any frontend files changed)
- `cd frontend && npm run test` — frontend tests (if any frontend files changed)

A phase is not done until all applicable gates are green.

### Step 3: Cleanup

When ALL Phases are checked off (`[x]`) and completed:

1. Provide a markdown style link and summary of all changes from
   #file:../changes/20260530-01-host-selected-waitlist-changes.md

2. Provide markdown style links to:
   - .copilot-tracking/planning/plans/20260530-01-host-selected-waitlist.plan.md
   - .copilot-tracking/planning/details/20260530-01-host-selected-waitlist-details.md
   - .copilot-tracking/research/20260530-01-host-selected-waitlist-research.md

   Recommend cleaning these files up after the implementation is merged.

## Success Criteria

- [ ] Changes tracking file created
- [ ] All plan items implemented with working code
- [ ] All detailed specifications satisfied
- [ ] No Alembic migration needed (confirmed by plan)
- [ ] All 10 `partition_participants` callers pass `signup_method` explicitly
- [ ] SELF_ADDED upsert to HOST_ADDED works via drag in edit form
- [ ] Demotion DM fires for any confirmed→overflow transition (all modes)
- [ ] `uv run pytest tests/unit` — all pass
- [ ] `uv run mypy shared/ services/` — no errors
- [ ] `cd frontend && npm run build && npm run test` — all pass
- [ ] Changes file updated continuously throughout implementation
