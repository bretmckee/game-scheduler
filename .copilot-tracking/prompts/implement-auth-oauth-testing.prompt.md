---
mode: agent
model: Claude Sonnet 4.6
---

<!-- markdownlint-disable-file -->

# Implementation Prompt: Auth Route Testing via Fake Discord Server

## Implementation Instructions

### Step 1: Create Changes Tracking File

You WILL create `20260308-04-auth-oauth-testing-changes.md` in #file:../changes/ if it does not exist.

### Step 2: Execute Implementation

You WILL follow #file:../../.github/instructions/task-implementation.instructions.md
You WILL systematically implement #file:../plans/20260308-04-auth-oauth-testing.plan.md task-by-task
You WILL follow ALL project standards and conventions:

- #file:../../.github/instructions/python.instructions.md for all Python code
- #file:../../.github/instructions/integration-tests.instructions.md for integration test patterns
- #file:../../.github/instructions/test-driven-development.instructions.md for TDD workflow
- #file:../../.github/instructions/containerization-docker-best-practices.instructions.md for Docker/compose changes
- #file:../../.github/instructions/self-explanatory-code-commenting.instructions.md for commenting style
- #file:../../.github/instructions/taming-copilot.instructions.md for interaction patterns
- #file:../../.github/instructions/quality-check-overrides.instructions.md — do NOT suppress linters or bypass pre-commit hooks without explicit user approval

**CRITICAL PREREQUISITE**: Confirm that Doc 03 (coverage collection fix) has been landed before beginning implementation. If it has not, stop and inform the user.

**CRITICAL**: If ${input:phaseStop:true} is true, you WILL stop after each Phase for user review.
**CRITICAL**: If ${input:taskStop:true} is true, you WILL stop after each Task for user review.

### Step 3: Cleanup

When ALL Phases are checked off (`[x]`) and completed you WILL do the following:

1. You WILL provide a markdown style link and a summary of all changes from #file:../changes/20260308-04-auth-oauth-testing-changes.md to the user:
   - You WILL keep the overall summary brief
   - You WILL add spacing around any lists
   - You MUST wrap any reference to a file in a markdown style link

2. You WILL provide markdown style links to .copilot-tracking/plans/20260308-04-auth-oauth-testing.plan.md, .copilot-tracking/details/20260308-04-auth-oauth-testing-details.md, and .copilot-tracking/research/20260308-04-auth-oauth-testing-research.md documents. You WILL recommend cleaning these files up as well.
3. **MANDATORY**: You WILL attempt to delete .copilot-tracking/prompts/implement-auth-oauth-testing.prompt.md

## Success Criteria

- [ ] Changes tracking file created
- [ ] All plan items implemented with working code
- [ ] All detailed specifications satisfied
- [ ] Project conventions followed
- [ ] All new and modified code passes lint and has unit tests
- [ ] Changes file updated continuously
- [ ] Line numbers updated if any referenced files changed
