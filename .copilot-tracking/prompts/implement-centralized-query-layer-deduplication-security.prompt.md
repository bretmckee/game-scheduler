---
mode: agent
model: Claude Sonnet 4.5
---

<!-- markdownlint-disable-file -->

# Implementation Prompt: Centralized Query Layer for Deduplication and Security

## Implementation Instructions

### Step 1: Create Changes Tracking File

You WILL create `20260101-centralized-query-layer-deduplication-security-changes.md` in #file:../changes/ if it does not exist.

### Step 2: Execute Implementation

You WILL follow #file:../../.github/instructions/task-implementation.instructions.md

You WILL systematically implement #file:../plans/20260101-centralized-query-layer-deduplication-security-plan.instructions.md task-by-task

You WILL follow ALL project standards and conventions:
- #file:../../.github/instructions/python.instructions.md for all Python code
- #file:../../.github/instructions/coding-best-practices.instructions.md for modularity, DRY, security, testing
- #file:../../.github/instructions/self-explanatory-code-commenting.instructions.md for commenting style
- #file:../../.github/instructions/taming-copilot.instructions.md for interaction patterns

**CRITICAL Implementation Approach**:
- Each task MUST be its own git commit
- Every commit MUST leave the system in a working state
- Every commit MUST meet code quality guidelines (lint passes, tests pass)
- Every commit MUST have appropriate test coverage:
  - Unit tests for all new wrapper functions (100% coverage requirement)
  - Integration tests for API route migrations (verify endpoints still work)
  - Integration tests for RLS enforcement (Phase 4)
  - E2E tests if user-facing behavior changes
- New functions may only be called by test code until fully integrated
- Run `uv run pytest` after each commit to verify working state
- Run `uv run ruff check` after each commit to verify code quality

**Test Coverage Requirements**:
- Unit tests: Every wrapper function must have tests covering:
  - Happy path with valid guild_id
  - Error cases (not found, invalid guild_id)
  - Verification that guild_id is required (TypeError if missing)
  - Verification that RLS context is set correctly
  - Verification that queries filter by guild_id
- Integration tests: API migrations must verify:
  - All endpoints continue to work
  - Guild filtering is enforced
  - Cross-guild access is prevented
- E2E tests: If user-facing behavior changes, verify through browser automation

**Incremental Working System Approach**:
- Phase 1: Create wrapper functions with tests (working but not used)
- Phase 2-3: Migrate one route/handler at a time, verify tests pass after each
- Phase 4: Add RLS after all migrations complete (low risk)
- Phase 5: Add enforcement tooling

**CRITICAL**: If ${input:phaseStop:true} is true, you WILL stop after each Phase for user review.
**CRITICAL**: If ${input:taskStop:true} is true, you WILL stop after each Task for user review.

### Step 3: Cleanup

When ALL Phases are checked off (`[x]`) and completed you WILL do the following:

1. You WILL provide a markdown style link and a summary of all changes from #file:../changes/20260101-centralized-query-layer-deduplication-security-changes.md to the user:
   - You WILL keep the overall summary brief
   - You WILL add spacing around any lists
   - You MUST wrap any reference to a file in a markdown style link

2. You WILL provide markdown style links to [.copilot-tracking/plans/20260101-centralized-query-layer-deduplication-security-plan.instructions.md](.copilot-tracking/plans/20260101-centralized-query-layer-deduplication-security-plan.instructions.md), [.copilot-tracking/details/20260101-centralized-query-layer-deduplication-security-details.md](.copilot-tracking/details/20260101-centralized-query-layer-deduplication-security-details.md), and [.copilot-tracking/research/20260101-centralized-query-layer-deduplication-security-research.md](.copilot-tracking/research/20260101-centralized-query-layer-deduplication-security-research.md) documents. You WILL recommend cleaning these files up as well.

3. **MANDATORY**: You WILL attempt to delete .copilot-tracking/prompts/implement-centralized-query-layer-deduplication-security.prompt.md

## Success Criteria

- [ ] Changes tracking file created
- [ ] All plan items implemented with working code
- [ ] All detailed specifications satisfied
- [ ] Project conventions followed (Python, Docker, commenting)
- [ ] All relevant coding conventions followed
- [ ] All new and modified code passes lint (ruff check)
- [ ] All new and modified code has comprehensive tests:
  - [ ] Unit tests for all wrapper functions (100% coverage)
  - [ ] Integration tests for API migrations
  - [ ] Integration tests for RLS enforcement
  - [ ] E2E tests if applicable
- [ ] All tests pass after every commit
- [ ] Every commit leaves system in working state
- [ ] Changes file updated continuously with commit information
- [ ] Line numbers updated if any referenced files changed
