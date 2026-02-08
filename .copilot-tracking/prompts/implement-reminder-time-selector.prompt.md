---
mode: agent
model: Claude Sonnet 4.5
---

<!-- markdownlint-disable-file -->

# Implementation Prompt: Reminder Time Selector Component

## Implementation Instructions

### Step 1: Create Changes Tracking File

You WILL create `20260208-01-reminder-time-selector-changes.md` in #file:../changes/ if it does not exist.

### Step 2: Execute Implementation

You WILL follow #file:../../.github/instructions/task-implementation.instructions.md
You WILL systematically implement #file:../plans/20260208-01-reminder-time-selector-plan.instructions.md task-by-task
You WILL follow ALL project standards and conventions:

- #file:../../.github/instructions/reactjs.instructions.md for all React/TypeScript code
- #file:../../.github/instructions/typescript-5-es2022.instructions.md for TypeScript standards
- #file:../../.github/instructions/test-driven-development.instructions.md for TDD methodology
- #file:../../.github/instructions/self-explanatory-code-commenting.instructions.md for commenting style
- #file:../../.github/instructions/taming-copilot.instructions.md for interaction patterns

**CRITICAL TDD Requirements**:

1. Create component/function stub with `throw new Error('not yet implemented')` BEFORE writing tests
2. Write tests expecting proper behavior (RED phase)
3. Verify tests fail correctly (stub throws error)
4. Implement minimal solution to pass tests (GREEN phase)
5. Refactor with passing tests (REFACTOR phase)
6. NO test modifications after initial test writing - tests should be correct from the start

**CRITICAL**: If ${input:phaseStop:true} is true, you WILL stop after each Phase for user review.
**CRITICAL**: If ${input:taskStop:true} is true, you WILL stop after each Task for user review.

### Step 3: Cleanup

When ALL Phases are checked off (`[x]`) and completed you WILL do the following:

1. You WILL provide a markdown style link and a summary of all changes from #file:../changes/20260208-01-reminder-time-selector-changes.md to the user:
   - You WILL keep the overall summary brief
   - You WILL add spacing around any lists
   - You MUST wrap any reference to a file in a markdown style link

2. You WILL provide markdown style links to .copilot-tracking/plans/20260208-01-reminder-time-selector-plan.instructions.md, .copilot-tracking/details/20260208-01-reminder-time-selector-details.md, and .copilot-tracking/research/20260208-01-reminder-time-selector-research.md documents. You WILL recommend cleaning these files up as well.

3. **MANDATORY**: You WILL attempt to delete .copilot-tracking/prompts/implement-reminder-time-selector.prompt.md

## Success Criteria

- [ ] Changes tracking file created
- [ ] All plan items implemented with working code
- [ ] All detailed specifications satisfied
- [ ] Project conventions followed
- [ ] All relevant coding conventions followed
- [ ] All new and modified code passes lint and has unit tests
- [ ] TDD Red-Green-Refactor cycle followed for all new components
- [ ] ReminderSelector component functional with 100% test coverage
- [ ] GameForm and TemplateForm integrated correctly
- [ ] Backward compatibility maintained
- [ ] Changes file updated continuously
- [ ] Line numbers updated if any referenced files changed
