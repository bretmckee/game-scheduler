---
mode: agent
model: Claude Sonnet 4.5
---

<!-- markdownlint-disable-file -->

# Implementation Prompt: Unit Test Fixture Consolidation

## Implementation Instructions

### Step 1: Create Changes Tracking File

You WILL create `20260126-unit-test-fixture-consolidation-changes.md` in #file:../changes/ if it does not exist.

### Step 2: Execute Implementation

You WILL follow #file:../../.github/instructions/task-implementation.instructions.md
You WILL systematically implement #file:../plans/20260126-unit-test-fixture-consolidation-plan.instructions.md task-by-task
You WILL follow ALL project standards and conventions:

- #file:../../.github/instructions/python.instructions.md for all Python code
- #file:../../.github/instructions/self-explanatory-code-commenting.instructions.md for commenting style
- #file:../../.github/instructions/taming-copilot.instructions.md for interaction patterns

**CRITICAL**: You WILL run tests after each phase to verify no regressions.
**CRITICAL**: If ${input:phaseStop:true} is true, you WILL stop after each Phase for user review.
**CRITICAL**: If ${input:taskStop:true} is true, you WILL stop after each Task for user review.

### Implementation Details

**Phase 1: Game Service Cluster** (Tasks 1.1-1.7)
- Create tests/services/api/services/conftest.py with 8 shared fixtures
- Remove duplicate fixtures from 5 game service test files
- Verify with `docker compose run unit-tests tests/services/api/services/`

**Phase 2: Root-Level Mocks** (Tasks 2.1-2.4)
- Add 4 unit test mock fixtures to tests/conftest.py
- Update route and dependency tests to use shared fixtures
- Verify with `docker compose run unit-tests tests/services/`

**Phase 3: Verification** (Tasks 3.1-3.3)
- Verify fixture discovery with pytest --collect-only
- Run coverage report to verify no regressions
- Document fixture locations and usage patterns

### Step 3: Cleanup

When ALL Phases are checked off (`[x]`) and completed you WILL do the following:

1. You WILL provide a markdown style link and a summary of all changes from #file:../changes/20260126-unit-test-fixture-consolidation-changes.md to the user:

   - You WILL keep the overall summary brief
   - You WILL add spacing around any lists
   - You MUST wrap any reference to a file in a markdown style link

2. You WILL provide markdown style links to [.copilot-tracking/plans/20260126-unit-test-fixture-consolidation-plan.instructions.md](.copilot-tracking/plans/20260126-unit-test-fixture-consolidation-plan.instructions.md), [.copilot-tracking/details/20260126-unit-test-fixture-consolidation-details.md](.copilot-tracking/details/20260126-unit-test-fixture-consolidation-details.md), and [.copilot-tracking/research/20260126-unit-test-fixture-consolidation-current-state-research.md](.copilot-tracking/research/20260126-unit-test-fixture-consolidation-current-state-research.md) documents. You WILL recommend cleaning these files up as well.

3. **MANDATORY**: You WILL attempt to delete `.copilot-tracking/prompts/implement-unit-test-fixture-consolidation.prompt.md`

## Success Criteria

- [ ] Changes tracking file created
- [ ] Phase 1: 35 fixtures removed from game service cluster
- [ ] Phase 1: tests/services/api/services/conftest.py created with 8 fixtures
- [ ] Phase 1: All game service tests pass
- [ ] Phase 2: 4 unit test mock fixtures added to tests/conftest.py
- [ ] Phase 2: Route and dependency tests updated
- [ ] Phase 2: All unit tests pass
- [ ] Phase 3: Fixture discovery verified
- [ ] Phase 3: Coverage report shows no regressions
- [ ] Phase 3: Fixture usage documented
- [ ] All code passes lint
- [ ] Changes file updated continuously
- [ ] Line numbers updated if any referenced files changed
