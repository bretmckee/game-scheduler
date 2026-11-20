---
description: 'Implement lossless @mention / #channel round-trip in game description and signup instructions, phase by phase'
---

<!-- markdownlint-disable-file -->

# Implementation Prompt: Lossless @mention / #channel Round-Trip in Game Text Fields

## Task Overview

Fix two compounding bugs:

- **2b**: the API returns rendered display names, so mentions lose their IDs on re-save.
- **2a**: suggestion chips write `@username` into free text, which loops on "Multiple matches found".

The fix has these parts:

- Server: an exact-match preference, a collapse of `<@id|label>` / `<#id|label>` on input, `display_name: null` for departed participants, and finally token-form rendering.
- Frontend: a `MemberRef` / `MemberChip` component, a `mentionTokens` util, `MentionText` for read-only views, and GameForm editor wiring that maps labels back to IDs.

The phases are ordered so that the server switches to emitting tokens last (Phase 7). Every earlier phase is a safe no-op for today's text.

## Implementation Instructions

### Step 1: Create Changes Tracking File

You WILL create `20261120-01-mention-round-trip-changes.md` in `.copilot-tracking/planning/changes/` if it does not exist.

### Step 2: Execute Implementation

You WILL follow `.github/instructions/task-implementation.instructions.md`
You WILL systematically implement `.copilot-tracking/planning/plans/20261120-01-mention-round-trip.plan.md` task-by-task, reading each task's details from `.copilot-tracking/planning/details/20261120-01-mention-round-trip-details.md` at the cited lines.
You WILL follow ALL project standards and conventions:

- `.github/instructions/python.instructions.md` for all Python code
- `.github/instructions/test-driven-development.instructions.md` for RED/GREEN phases (xfail in Python, `it.fails` in Vitest)
- `.github/instructions/unit-tests.instructions.md` for unit test quality
- `.github/instructions/reactjs.instructions.md` and `.github/instructions/typescript-5-es2022.instructions.md` for frontend code
- `.github/instructions/integration-tests.instructions.md` and `.github/instructions/test-execution.instructions.md` for integration/e2e runs
- `.github/instructions/copyright-headers.instructions.md` for new files
- `.github/instructions/self-explanatory-code-commenting.instructions.md` for commenting style

Task-specific guardrails:

- **Never persist names for Discord IDs.** Labels are produced live from the member projection.
- `MentionChip.tsx` is the existing suggestion chip. The new component is `MemberChip.tsx`. Do not conflate them.
- Do not change how the server renders `description` / `signup_instructions` before Phase 7. That would break frontend readers mid-plan.
- Never run `pytest --testmon` manually.

**CRITICAL**: By default, you WILL stop after each Phase and each Task for user review. The user may tell you at the start of the session (or at any point) to run through multiple phases or tasks without stopping. Follow whatever cadence they specify instead of this default.
**CRITICAL**: You WILL NOT commit changes unless the user explicitly tells you to commit. Completing a phase does NOT trigger a commit. Announce that the phase is complete and wait for the user to say "commit" or similar before running `git commit`.

When the user does request a commit, use this format for phase commits:

```
fix: Phase N - {{description, including mention round-trip context}}

- {{change bullet 1}}
- {{change bullet 2}}

Rationale: {{why this phase does what it does}}
```

**CRITICAL**: Before marking any Phase complete or committing its changes, you MUST verify ALL pre-commit gates pass:

- `uv run pytest tests/unit` — Python unit tests
- `uv run mypy shared/ services/` — type checking (mypy failures block commits exactly like test failures)
- `cd frontend && npm run build` — TypeScript build (if any frontend files changed)
- `cd frontend && npm run test` — frontend tests (if any frontend files changed)
- `scripts/run-integration-tests.sh |& tee output-integration.txt` — if the phase writes or modifies integration tests (Phase 7); follow `.github/instructions/test-execution.instructions.md` for output capture rules
- `scripts/run-e2e-tests.sh |& tee output-e2e.txt` — if the phase writes or modifies e2e tests (Phase 8); follow `.github/instructions/test-execution.instructions.md` for output capture rules

A phase is not done until all applicable gates are green. Writing tests and committing them without executing them is a pre-commit gate failure.

### Step 3: Cleanup

When ALL Phases are checked off (`[x]`) and completed you WILL do the following:

1. You WILL provide a markdown style link and a summary of all changes from `.copilot-tracking/planning/changes/20261120-01-mention-round-trip-changes.md` to the user:
   - You WILL keep the overall summary brief
   - You WILL add spacing around any lists
   - You MUST wrap any reference to a file in a markdown style link

2. You WILL provide markdown style links to `.copilot-tracking/planning/plans/20261120-01-mention-round-trip.plan.md`, `.copilot-tracking/planning/details/20261120-01-mention-round-trip-details.md`, and `.copilot-tracking/research/20261120-01-mention-round-trip-research.md` documents. You WILL recommend cleaning these files up as well.

## Success Criteria

- [ ] Changes tracking file created
- [ ] All plan items implemented with working code
- [ ] All detailed specifications satisfied
- [ ] Kallisti and Xanthias scenarios save after at most one disambiguation
- [ ] Unedited re-save yields byte-identical stored text
- [ ] Project conventions followed
- [ ] All new and modified code passes lint and has unit tests
- [ ] Changes file updated continuously
- [ ] Line numbers updated if any referenced files changed
