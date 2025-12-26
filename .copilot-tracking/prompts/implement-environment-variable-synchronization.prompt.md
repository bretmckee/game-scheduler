---
mode: agent
model: Claude Sonnet 4.5
---

<!-- markdownlint-disable-file -->

# Implementation Prompt: Environment Variable Configuration Synchronization

## Implementation Instructions

### Step 1: Create Changes Tracking File

You WILL create `20251226-environment-variable-synchronization-changes.md` in #file:../changes/ if it does not exist.

### Step 2: Execute Implementation

You WILL follow #file:../../.github/instructions/task-implementation.instructions.md
You WILL systematically implement #file:../plans/20251226-environment-variable-synchronization-plan.instructions.md task-by-task
You WILL follow ALL project standards and conventions:

- #file:../../.github/instructions/self-explanatory-code-commenting.instructions.md for commenting style
- #file:../../.github/instructions/taming-copilot.instructions.md for interaction patterns

**CRITICAL**: If ${input:phaseStop:true} is true, you WILL stop after each Phase for user review.
**CRITICAL**: If ${input:taskStop:true} is true, you WILL stop after each Task for user review.

### Step 3: Implementation Approach

**CRITICAL SECURITY WARNING**:
- **Only env.example should contain placeholder values**
- **All other env files (dev, prod, staging, e2e, int) contain live credentials**
- **Preserve ALL existing credential values in live environment files**
- Only reorganize, add missing variables, and remove unused variables
- Never replace actual tokens, passwords, or API keys

**Phase 1: env.example Updates**
- Add missing Docker configuration variables with comprehensive comments
- Add JWT_SECRET and RETRY_DAEMON_LOG_LEVEL
- Remove deprecated API_SECRET_KEY, API_HOST, API_PORT
- Reorganize entire file to match 12-section standardized ordering
- Ensure every variable has clear documentation

**Phase 2: env.dev Updates**
- Add missing variables (COMPOSE_FILE, COMPOSE_PROFILES, JWT_SECRET, RETRY_DAEMON_LOG_LEVEL)
- Remove duplicate API_HOST_PORT definition
- Remove commented Discord invite URL
- **PRESERVE all existing credential values** (live working credentials)
- Move Cloudflare section from end to proper location
- Reorganize to match env.example structure

**Phase 3: env.prod Updates**
- Add JWT_SECRET, RETRY_DAEMON_LOG_LEVEL, COMPOSE_FILE
- Remove unused API_HOST, API_PORT
- Reorganize to match standard ordering
- Exclude development-only variables (port mappings, HOST_WORKSPACE_FOLDER)
- Add minimal comments referencing env.example

**Phase 4: env.staging Updates**
- Add JWT_SECRET, RETRY_DAEMON_LOG_LEVEL
- Remove unused API_HOST, API_PORT
- Reorganize to match standard ordering
- Keep CONTAINER_PREFIX for staging isolation
- Preserve external network configuration

**Phase 5: Test Configuration Updates**
- Update env.e2e with consistent ordering while maintaining test focus
- Update env.int with consistent ordering for integration tests
- Preserve test-specific variable sets
- Add clarifying comments for test usage

**Phase 6: Verification**
- Verify all ${VARIABLE} references in compose files have env entries
- Test vimdiff comparison of files
- Document verification results

### Step 4: Cleanup

When ALL Phases are checked off (`[x]`) and completed you WILL do the following:

1. You WILL provide a markdown style link and a summary of all changes from #file:../changes/20251226-environment-variable-synchronization-changes.md to the user:

   - You WILL keep the overall summary brief
   - You WILL add spacing around any lists
   - You MUST wrap any reference to a file in a markdown style link

2. You WILL provide markdown style links to .copilot-tracking/plans/20251226-environment-variable-synchronization-plan.instructions.md, .copilot-tracking/details/20251226-environment-variable-synchronization-details.md, and .copilot-tracking/research/20251226-environment-variable-audit-research.md documents. You WILL recommend cleaning these files up as well.

3. **MANDATORY**: You WILL attempt to delete .copilot-tracking/prompts/implement-environment-variable-synchronization.prompt.md

## Success Criteria

- [ ] Changes tracking file created
- [ ] All plan items implemented with correct variable ordering
- [ ] All detailed specifications satisfied
- [ ] Project conventions followed
- [ ] All env files have consistent structure
- [ ] No duplicate or unused variables remain
- [ ] JWT_SECRET and RETRY_DAEMON_LOG_LEVEL added to all deployment files
- [ ] env.example has comprehensive documentation
- [ ] Files verified with vimdiff for easy comparison
- [ ] Changes file updated continuously
