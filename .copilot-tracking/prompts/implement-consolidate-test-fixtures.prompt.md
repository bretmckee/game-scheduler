---
mode: agent
model: Claude Sonnet 4.5
---

<!-- markdownlint-disable-file -->

# Implementation Prompt: Consolidate Test Fixtures

## Implementation Instructions

### Step 1: Create Changes Tracking File

You WILL create `20260104-consolidate-test-fixtures-changes.md` in [.copilot-tracking/changes/](.copilot-tracking/changes/) if it does not exist.

### Step 2: Execute Implementation

You WILL follow [.github/instructions/task-implementation.instructions.md](../../.github/instructions/task-implementation.instructions.md)

You WILL systematically implement [.copilot-tracking/plans/20260104-consolidate-test-fixtures-plan.instructions.md](.copilot-tracking/plans/20260104-consolidate-test-fixtures-plan.instructions.md) task-by-task

You WILL follow ALL project standards and conventions:
- [.github/instructions/python.instructions.md](../../.github/instructions/python.instructions.md) for all Python code
- [.github/instructions/coding-best-practices.instructions.md](../../.github/instructions/coding-best-practices.instructions.md) for testing patterns
- [.github/instructions/self-explanatory-code-commenting.instructions.md](../../.github/instructions/self-explanatory-code-commenting.instructions.md) for commenting style
- [.github/instructions/taming-copilot.instructions.md](../../.github/instructions/taming-copilot.instructions.md) for interaction patterns

**CRITICAL**: If ${input:phaseStop:true} is true, you WILL stop after each Phase for user review.
**CRITICAL**: If ${input:taskStop:true} is true, you WILL stop after each Task for user review.

### Implementation Guidance

**Phase 0 is Critical**: You MUST create comprehensive shared fixtures and validate them with tests before any migration work. Do not skip fixture validation tests.

**Factory Pattern**: All data creation fixtures MUST return functions, not data. Tests call these functions to create what they need.

**Hermetic Tests**: Tests MUST create everything they need. Tests MUST rely on automatic cleanup. Tests MUST NOT maintain shared data between tests.

**Deadlock Prevention**: admin_db_sync MUST use explicit rollback before close, separate cleanup session, and DELETE (not TRUNCATE).

**Sync First**: Primary implementations are synchronous. Async versions wrap sync with asyncio.run() or use proper async/await patterns.

**Aggressive Migration**: As soon as a test is migrated, DELETE its custom fixtures. As soon as all tests using a deprecated fixture are migrated, DELETE that fixture from conftest.py.

### Step 3: Cleanup

When ALL Phases are checked off (`[x]`) and completed you WILL do the following:

1. You WILL provide a markdown style link and a summary of all changes from [.copilot-tracking/changes/20260104-consolidate-test-fixtures-changes.md](.copilot-tracking/changes/20260104-consolidate-test-fixtures-changes.md) to the user:
   - You WILL keep the overall summary brief
   - You WILL add spacing around any lists
   - You MUST wrap any reference to a file in a markdown style link

2. You WILL provide markdown style links to [.copilot-tracking/plans/20260104-consolidate-test-fixtures-plan.instructions.md](.copilot-tracking/plans/20260104-consolidate-test-fixtures-plan.instructions.md), [.copilot-tracking/details/20260104-consolidate-test-fixtures-details.md](.copilot-tracking/details/20260104-consolidate-test-fixtures-details.md), and [.copilot-tracking/research/20260104-consolidate-test-fixtures-research.md](.copilot-tracking/research/20260104-consolidate-test-fixtures-research.md) documents. You WILL recommend cleaning these files up as well.

3. **MANDATORY**: You WILL attempt to delete [.copilot-tracking/prompts/implement-consolidate-test-fixtures.prompt.md](.copilot-tracking/prompts/implement-consolidate-test-fixtures.prompt.md)

## Success Criteria

- [ ] Changes tracking file created
- [ ] All plan items implemented with working code
- [ ] All detailed specifications satisfied
- [ ] Project conventions followed
- [ ] All relevant coding conventions followed
- [ ] All new and modified code passes lint and has unit tests
- [ ] Changes file updated continuously
- [ ] Line numbers updated if any referenced files changed
- [ ] 100+ fixtures consolidated to ~15 shared factory fixtures
- [ ] All integration and e2e tests passing
- [ ] No deadlocks or cleanup conflicts
- [ ] Redundant fixtures deleted
