---
mode: agent
model: Claude Sonnet 4.5
---

<!-- markdownlint-disable-file -->

# Implementation Prompt: Reduce Complexity Thresholds to Default Values

## Implementation Instructions

### Step 1: Create Changes Tracking File

You WILL create `20260116-default-complexity-thresholds-reduction-changes.md` in #file:../changes/ if it does not exist.

### Step 2: Execute Implementation

You WILL follow #file:../../.github/instructions/task-implementation.instructions.md

You WILL systematically implement #file:../plans/20260116-default-complexity-thresholds-reduction-plan.instructions.md task-by-task

You WILL follow ALL project standards and conventions:
- #file:../../.github/instructions/python.instructions.md for all Python code
- #file:../../.github/instructions/coding-best-practices.instructions.md for refactoring patterns
- #file:../../.github/instructions/self-explanatory-code-commenting.instructions.md for commenting style
- #file:../../.github/instructions/taming-copilot.instructions.md for interaction patterns

**CRITICAL REQUIREMENTS**:
- You WILL write unit tests for ALL extracted helper methods before considering a task complete
- You WILL verify test coverage reaches 100% for all new extracted methods
- You WILL run complexity checks after each function refactoring to verify metrics reduced
- You WILL run full test suite after each task to ensure no regressions

**REFACTORING PATTERN** (from create_game() success):
1. Extract Method: Create focused helper methods with single responsibility
2. Parameter Objects: Group related data into dataclasses
3. Guard Clauses: Use early returns to reduce nesting
4. Progressive Extraction: Refactor in small, testable increments
5. Unit Test Each Helper: Test extracted methods independently

**VERIFICATION COMMANDS**:
- Cyclomatic complexity: `uv run ruff check --select C901`
- Cognitive complexity: `uv run pre-commit run complexipy --all-files`
- Unit tests: `uv run pytest tests/ -v`
- Integration tests: `scripts/run-integration-tests.sh`

**PHASE STOPPING POINTS**:
- ${input:phaseStop:true} - If true, stop after each Phase for user review
- ${input:taskStop:true} - If true, stop after each Task for user review

**DEFAULT BEHAVIOR**: Continue through all tasks in sequence unless stopping points enabled.

### Step 3: Cleanup

When ALL Phases are checked off (`[x]`) and Phase 4 Task 4.6 is complete (PRIMARY GOAL achieved), you WILL:

1. Provide a markdown link and summary of changes from #file:../changes/20260116-default-complexity-thresholds-reduction-changes.md:
   - Keep overall summary brief
   - Add spacing around lists
   - Wrap all file references in markdown links

2. Provide markdown links to planning documents:
   - [.copilot-tracking/plans/20260116-default-complexity-thresholds-reduction-plan.instructions.md](.copilot-tracking/plans/20260116-default-complexity-thresholds-reduction-plan.instructions.md)
   - [.copilot-tracking/details/20260116-default-complexity-thresholds-reduction-details.md](.copilot-tracking/details/20260116-default-complexity-thresholds-reduction-details.md)
   - [.copilot-tracking/research/20260116-default-complexity-thresholds-reduction-research.md](.copilot-tracking/research/20260116-default-complexity-thresholds-reduction-research.md)

   Recommend reviewing and cleaning up these documents.

3. **MANDATORY**: Attempt to delete `.copilot-tracking/prompts/implement-default-complexity-thresholds-reduction.prompt.md`

## Success Criteria

- [ ] Changes tracking file created and maintained
- [ ] Phase 1: 8 dual-violation functions refactored with unit tests
- [ ] Phase 1: Thresholds updated to C901=12, complexipy=17
- [ ] Phase 2: 2 cyclomatic violations resolved with unit tests
- [ ] Phase 2: Cyclomatic threshold at default C901=10
- [ ] Phase 3: 8 high cognitive complexity functions refactored with unit tests
- [ ] Phase 3: All functions at cognitive ≤17
- [ ] Phase 4: Remaining cognitive violations resolved with unit tests
- [ ] Phase 4: **PRIMARY GOAL** - Both thresholds at defaults (C901=10, complexipy=15)
- [ ] Phase 5 (Optional): Utility code refactored if desired
- [ ] All project coding standards followed
- [ ] 100% test coverage maintained on all new code
- [ ] Zero complexity violations at default thresholds
- [ ] All integration and E2E tests passing
- [ ] Changes file updated continuously with accurate line references

## Phased Approach Notes

**Phase 1** targets the 8 highest-impact functions violating both metrics, enabling immediate threshold reduction.

**Phase 2** addresses final cyclomatic violations to reach C901=10 default.

**Phase 3** tackles high cognitive complexity (20-27) functions to reach threshold of 17.

**Phase 4** completes the work by reducing remaining cognitive complexity violations to reach complexipy=15 default - **THIS IS THE PRIMARY GOAL**.

**Phase 5** is optional cleanup of test utilities and scripts with extreme complexity.

Apply proven refactoring techniques from create_game() success: 65% fewer lines, 75% less cyclomatic complexity, 88% less cognitive complexity.
