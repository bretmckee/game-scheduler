---
mode: agent
model: Claude Sonnet 4.5
---

<!-- markdownlint-disable-file -->

# Implementation Prompt: Redis to Valkey Migration

## Implementation Instructions

### Step 1: Create Changes Tracking File

You WILL create `20251217-redis-to-valkey-migration-changes.md` in #file:../changes/ if it does not exist.

### Step 2: Execute Implementation

You WILL follow #file:../../.github/instructions/task-implementation.instructions.md
You WILL systematically implement #file:../plans/20251217-redis-to-valkey-migration-plan.instructions.md task-by-task
You WILL follow ALL project standards and conventions:

- #file:../../.github/instructions/containerization-docker-best-practices.instructions.md for all Docker configurations
- #file:../../.github/instructions/coding-best-practices.instructions.md for testing and validation
- #file:../../.github/instructions/self-explanatory-code-commenting.instructions.md for any code comments (though none expected)
- #file:../../.github/instructions/taming-copilot.instructions.md for interaction patterns

**CRITICAL**: If ${input:phaseStop:true} is true, you WILL stop after each Phase for user review.
**CRITICAL**: If ${input:taskStop:true} is true, you WILL stop after each Task for user review.

### Step 3: Cleanup

When ALL Phases are checked off (`[x]`) and completed you WILL do the following:

1. You WILL provide a markdown style link and a summary of all changes from #file:../changes/20251217-redis-to-valkey-migration-changes.md to the user:

   - You WILL keep the overall summary brief
   - You WILL add spacing around any lists
   - You MUST wrap any reference to a file in a markdown style link

2. You WILL provide markdown style links to [.copilot-tracking/plans/20251217-redis-to-valkey-migration-plan.instructions.md](../plans/20251217-redis-to-valkey-migration-plan.instructions.md), [.copilot-tracking/details/20251217-redis-to-valkey-migration-details.md](../details/20251217-redis-to-valkey-migration-details.md), and [.copilot-tracking/research/20251217-redis-to-valkey-migration-research.md](../research/20251217-redis-to-valkey-migration-research.md) documents. You WILL recommend cleaning these files up as well.
3. **MANDATORY**: You WILL attempt to delete .copilot-tracking/prompts/implement-redis-to-valkey-migration.prompt.md

## Success Criteria

- [ ] Changes tracking file created
- [ ] All Docker Compose files use Valkey 9.0.1-alpine image
- [ ] CI/CD workflow updated with Valkey service container
- [ ] All documentation references updated from Redis to Valkey
- [ ] Services start successfully with healthy status
- [ ] Integration tests pass without modifications
- [ ] OAuth flows validated in development environment
- [ ] Cache operations function identically
- [ ] Changes file updated continuously
- [ ] Line numbers updated if any referenced files changed
