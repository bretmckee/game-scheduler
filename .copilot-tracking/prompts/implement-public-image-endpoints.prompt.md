---
mode: agent
model: Claude Sonnet 4.5
---

<!-- markdownlint-disable-file -->

# Implementation Prompt: Secure Public Image Architecture with Deduplication

## Implementation Instructions

### Step 1: Create Changes Tracking File

You WILL create `20260207-02-public-image-endpoints-changes.md` in #file:../changes/ if it does not exist.

### Step 2: Execute Implementation

You WILL follow #file:../../.github/instructions/task-implementation.instructions.md
You WILL systematically implement #file:../plans/20260207-02-public-image-endpoints-plan.instructions.md task-by-task
You WILL follow ALL project standards and conventions:

- #file:../../.github/instructions/python.instructions.md for all Python code
- #file:../../.github/instructions/test-driven-development.instructions.md for TDD methodology (RED-GREEN-REFACTOR)
- #file:../../.github/instructions/fastapi-transaction-patterns.instructions.md for service layer patterns
- #file:../../.github/instructions/containerization-docker-best-practices.instructions.md for any Docker changes
- #file:../../.github/instructions/self-explanatory-code-commenting.instructions.md for commenting style
- #file:../../.github/instructions/taming-copilot.instructions.md for interaction patterns

**CRITICAL SECURITY REQUIREMENT**: This implementation MUST NOT use BYPASSRLS credentials for public endpoints. Public image endpoint MUST use regular database credentials accessing the new game_images table (no RLS policies).

**CRITICAL TDD REQUIREMENT**: Follow Red-Green-Refactor cycle strictly:

- Phase 1: Write tests first (RED), then implement (GREEN), then refactor
- Phase 2: Write integration tests first (RED), then implement (GREEN)
- Phase 3: Create stub (RED), write tests (RED), implement (GREEN), add rate limiting (REFACTOR)

**CRITICAL**: If ${input:phaseStop:true} is true, you WILL stop after each Phase for user review.
**CRITICAL**: If ${input:taskStop:true} is true, you WILL stop after each Task for user review.

### Step 3: Cleanup

When ALL Phases are checked off (`[x]`) and completed you WILL do the following:

1. You WILL provide a markdown style link and a summary of all changes from #file:../changes/20260207-02-public-image-endpoints-changes.md to the user:
   - You WILL keep the overall summary brief
   - You WILL add spacing around any lists
   - You MUST wrap any reference to a file in a markdown style link

2. You WILL provide markdown style links to:
   - [.copilot-tracking/plans/20260207-02-public-image-endpoints-plan.instructions.md](/.copilot-tracking/plans/20260207-02-public-image-endpoints-plan.instructions.md)
   - [.copilot-tracking/details/20260207-02-public-image-endpoints-details.md](/.copilot-tracking/details/20260207-02-public-image-endpoints-details.md)
   - [.copilot-tracking/research/20260207-02-public-image-endpoints-research.md](/.copilot-tracking/research/20260207-02-public-image-endpoints-research.md)

   You WILL recommend cleaning these files up as well.

3. **MANDATORY**: You WILL attempt to delete .copilot-tracking/prompts/implement-public-image-endpoints.prompt.md

## Success Criteria

- [ ] Changes tracking file created and maintained
- [ ] Phase 0: Migration and models complete (game_images table created, GameImage model, GameSession updated)
- [ ] Phase 1: Image storage service with deduplication complete (30+ integration tests passing)
- [ ] Phase 2: Game service integration complete (create/update/delete with images)
- [ ] Phase 3: Public endpoint complete with rate limiting (no BYPASSRLS, 60/min + 100/5min limits)
- [ ] Phase 4: Bot and frontend updated to use new URLs
- [ ] Phase 5: Old endpoints removed, documentation updated
- [ ] All integration tests pass (30+ tests for storage, deduplication, reference counting, public endpoint, rate limiting)
- [ ] All E2E tests pass with new architecture
- [ ] Zero BYPASSRLS credentials used for public endpoint
- [ ] Principle of least privilege maintained (public endpoint can only access image binary data)
- [ ] Changes file updated continuously with accurate line numbers
