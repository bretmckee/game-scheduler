---
mode: agent
model: Claude Sonnet 4.6
---

<!-- markdownlint-disable-file -->

# Implementation Prompt: Integration Tests Using admin_db Bypass RLS

## Implementation Instructions

### Step 1: Create Changes Tracking File

You WILL create `20260427-01-integration-tests-admin-db-rls-bypass-changes.md` in
#file:../changes/ if it does not exist.

### Step 2: Execute Implementation

You WILL follow #file:../../.github/instructions/task-implementation.instructions.md
You WILL systematically implement #file:../plans/20260427-01-integration-tests-admin-db-rls-bypass.plan.md task-by-task
You WILL follow ALL project standards and conventions:

- #file:../../.github/instructions/python.instructions.md for all Python code
- #file:../../.github/instructions/test-driven-development.instructions.md for TDD conventions (retrofitting scenario applies — no stubs or xfail)
- #file:../../.github/instructions/unit-tests.instructions.md for behavioral assertion requirements
- #file:../../.github/instructions/integration-tests.instructions.md for integration test conventions
- #file:../../.github/instructions/test-execution.instructions.md for test execution and output capture rules
- #file:../../.github/instructions/self-explanatory-code-commenting.instructions.md for commenting style
- #file:../../.github/instructions/taming-copilot.instructions.md for interaction patterns

**CRITICAL**: If ${input:phaseStop:true} is true, you WILL stop after each Phase for user review.
**CRITICAL**: If ${input:taskStop:true} is true, you WILL stop after each Task for user review.
**CRITICAL**: You WILL NOT commit changes unless the user explicitly tells you to commit. Completing a phase does NOT trigger a commit. Announce that the phase is complete and wait for the user to say "commit" or similar before running `git commit`.

When the user does request a commit, use this format:

```
fix: convert GameService integration tests to use app_db under RLS

- replace GameService(db=admin_db) with GameService(db=app_db) for the 12
  affected tests in test_game_image_integration.py
- add set_config('app.current_guild_ids', ...) before each app_db service call
  to match the RLS context that production HTTP routes establish
- keep admin_db for fixture setup and post-operation verification reads

Rationale: tests using admin_db (BYPASSRLS superuser) silently skipped all
RLS policies; future regressions that violate guild isolation would pass
the integration suite and only surface in e2e tests or production
```

**CRITICAL**: Before marking Phase 1 complete, verify ALL applicable gates pass:

- `scripts/run-integration-tests.sh tests/integration/services/api/services/test_game_image_integration.py |& tee output-integration-rls-fix.txt` — all 13 tests must pass; follow #file:../../.github/instructions/test-execution.instructions.md for output capture

### Step 3: Cleanup

When ALL Phases are checked off (`[x]`) and completed you WILL do the following:

1. You WILL provide a markdown style link and a summary of all changes from
   #file:../changes/20260427-01-integration-tests-admin-db-rls-bypass-changes.md to the user.

2. You WILL provide markdown style links to
   .copilot-tracking/planning/plans/20260427-01-integration-tests-admin-db-rls-bypass.plan.md,
   .copilot-tracking/planning/details/20260427-01-integration-tests-admin-db-rls-bypass-details.md,
   and .copilot-tracking/research/20260427-01-integration-tests-admin-db-rls-bypass-research.md.
   Recommend cleaning these files up as well.

## Success Criteria

- [ ] Changes tracking file created
- [ ] All plan items implemented with working code
- [ ] All 13 tests in test_game_image_integration.py pass under integration test suite
- [ ] No GameService call that exercises the operation under test uses admin_db
- [ ] admin_db retained for fixture setup and post-operation verification
- [ ] Changes file updated continuously
