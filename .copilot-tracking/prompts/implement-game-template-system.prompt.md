---
mode: agent
model: Claude Sonnet 4.5
---

<!-- markdownlint-disable-file -->

# Implementation Prompt: Game Template System

## Implementation Instructions

### Step 1: Create Changes Tracking File

You WILL create `20251201-game-template-system-changes.md` in #file:../changes/ if it does not exist.

### Step 2: Execute Implementation

You WILL follow #file:../../.github/instructions/task-implementation.instructions.md
You WILL systematically implement #file:../plans/20251201-game-template-system-plan.instructions.md task-by-task
You WILL follow ALL project standards and conventions:

- #file:../../.github/instructions/python.instructions.md for all Python code
- #file:../../.github/instructions/reactjs.instructions.md for all React/TypeScript code
- #file:../../.github/instructions/containerization-docker-best-practices.instructions.md for Docker files
- #file:../../.github/instructions/self-explanatory-code-commenting.instructions.md for commenting style
- #file:../../.github/instructions/taming-copilot.instructions.md for interaction patterns
- #file:../../.github/instructions/coding-best-practices.instructions.md for modularity and correctness

**CRITICAL**: If ${input:phaseStop:true} is true, you WILL stop after each Phase for user review.
**CRITICAL**: If ${input:taskStop:true} is true, you WILL stop after each Task for user review.

**CRITICAL**: After each task or phase, you WILL verify the system remains deployable by:
1. Running unit tests for affected code: `uv run pytest tests/services/ tests/shared/ -v`
2. Checking Docker builds succeed: `docker compose build api bot frontend`
3. Running linting: `uv run ruff check .` for Python, `cd frontend && npm run lint` for TypeScript

### Step 3: Cleanup

When ALL Phases are checked off (`[x]`) and completed you WILL do the following:

1. You WILL provide a markdown style link and a summary of all changes from #file:../changes/20251201-game-template-system-changes.md to the user:

   - You WILL keep the overall summary brief
   - You WILL add spacing around any lists
   - You MUST wrap any reference to a file in a markdown style link

2. You WILL provide markdown style links to .copilot-tracking/plans/20251201-game-template-system-plan.instructions.md, .copilot-tracking/details/20251201-game-template-system-details.md, and .copilot-tracking/research/20251201-game-template-system-research.md documents. You WILL recommend cleaning these files up as well.
3. **MANDATORY**: You WILL attempt to delete .copilot-tracking/prompts/implement-game-template-system.prompt.md

## Success Criteria

- [ ] Changes tracking file created
- [ ] All plan items implemented with working code
- [ ] All detailed specifications satisfied
- [ ] Project conventions followed
- [ ] All relevant coding conventions followed
- [ ] All new and modified code passes lint and has unit tests
- [ ] System remains deployable after each phase
- [ ] Changes file updated continuously
- [ ] Line numbers updated if any referenced files changed
- [ ] No SettingsResolver or inheritance code remains
- [ ] All games require template selection
- [ ] Templates properly enforce locked vs editable fields
- [ ] Default template exists and cannot be deleted
- [ ] Frontend template management UI functional
- [ ] All tests pass (480+ unit tests, integration tests)
