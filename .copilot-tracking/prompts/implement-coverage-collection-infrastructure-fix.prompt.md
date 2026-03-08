---
mode: agent
model: Claude Sonnet 4.6
---

<!-- markdownlint-disable-file -->

# Implementation Prompt: Coverage Collection Infrastructure Fix

## Implementation Instructions

### Step 1: Create Changes Tracking File

You WILL create `20260308-03-coverage-collection-infrastructure-fix-changes.md` in #file:../changes/ if it does not exist.

### Step 2: Execute Implementation

You WILL follow #file:../../.github/instructions/task-implementation.instructions.md
You WILL systematically implement #file:../plans/20260308-03-coverage-collection-infrastructure-fix.plan.md task-by-task
You WILL follow ALL project standards and conventions:

- #file:../../.github/instructions/python.instructions.md for all Python code
- #file:../../.github/instructions/containerization-docker-best-practices.instructions.md for Docker files
- #file:../../.github/instructions/self-explanatory-code-commenting.instructions.md for commenting style
- #file:../../.github/instructions/taming-copilot.instructions.md for interaction patterns

Work through the phases in order. Phases 1 and 2 must be complete before Phases 3 and 4 (coverage must be installed and the hook installed before the compose environment variables have any effect).

**CRITICAL**: If ${input:phaseStop:true} is true, you WILL stop after each Phase for user review.
**CRITICAL**: If ${input:taskStop:true} is true, you WILL stop after each Task for user review.

### Step 3: Cleanup

When ALL Phases are checked off (`[x]`) and completed you WILL do the following:

1. You WILL provide a markdown style link and a summary of all changes from #file:../changes/20260308-03-coverage-collection-infrastructure-fix-changes.md to the user:
   - You WILL keep the overall summary brief
   - You WILL add spacing around any lists
   - You MUST wrap any reference to a file in a markdown style link

2. You WILL provide markdown style links to .copilot-tracking/plans/20260308-03-coverage-collection-infrastructure-fix.plan.md, .copilot-tracking/details/20260308-03-coverage-collection-infrastructure-fix-details.md, and .copilot-tracking/research/20260308-03-test-coverage-gaps-research.md documents. You WILL recommend cleaning these files up as well.
3. **MANDATORY**: You WILL attempt to delete .copilot-tracking/prompts/implement-coverage-collection-infrastructure-fix.prompt.md

## Success Criteria

- [ ] Changes tracking file created
- [ ] `coverage[toml]` added to `[project.dependencies]` in `pyproject.toml`
- [ ] `sitecustomize.py` RUN line added to `api.Dockerfile`, `bot.Dockerfile`, `scheduler.Dockerfile`, `retry.Dockerfile`
- [ ] Coverage env vars and volume mounts added to 4 services in `compose.int.yaml`
- [ ] Coverage env vars and volume mounts added to 3 services in `compose.e2e.yaml`
- [ ] `scripts/coverage-report.sh` updated to combine all per-service coverage files
- [ ] No modifications to `compose.prod.yaml`, `compose.staging.yaml`, or `compose.yaml`
- [ ] All plan items checked off
- [ ] Changes file updated continuously
