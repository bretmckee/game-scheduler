---
mode: agent
agent: agent
description: 'Implement Phase 1 Security Paydown (T1 mutation-debt elimination): six phases W0-W5 from validated research, ending in serial-pipeline restamp v4 under user approval.'
name: implement-phase1-security-paydown
model: Claude Sonnet 4.6
---

<!-- markdownlint-disable-file -->

# Implementation Prompt: Phase 1 Security Paydown (T1 auth/tokens/oauth2/roles/permissions Mutation Debt)

## Task Overview

Execute the plan checklist at `.copilot-tracking/planning/plans/20260905-01-phase1-security-paydown.plan.md` task-by-task to eliminate T1 security-surface mutation debt on branch `develop`: one production dead-line deletion (W0), unit-test strengthening waves (W1–W3), untested-function conversion with pass-immediately tests (W2 tasks), logger-assert + acceptance bookkeeping (W4 work), and a user-approved serial-pipeline ledger restamp v4 that must verify against measured per-file targets. Baseline facts are verified in the source research (`develop` @ `15e318c9`); no external research is needed during execution — re-measure store data using the read-only re-derivation method instead of trusting memory between waves.

**Operating mode (binding)**: This phase runs INTERACTIVE. After completing any Phase or Task, STOP and announce what was done plus its verification evidence; do NOT run `git commit` until the user explicitly says "commit". The implementer NEVER pushes — the user pushes as needed between phases. One active commit at a time.

### Step 1: Create Changes Tracking File

You WILL create `20260905-01-phase1-security-paydown-changes.md` in #file:../changes/ if it does not exist, following the changes-file template in `.github/instructions/task-implementation.instructions.md`. Record continuously: evidence snippets (grep output for dead-line deletion, SQLAlchemy version + where-clause validation criteria outcome, pre-task/post-wave id lists from re-derivations, backed-out assertion sites with reasons, wave-boundary suite/mypy outputs, KILL REGRESSION-free gate confirmation per commit).

### Step 2: Execute Implementation

You WILL follow #file:../../.github/instructions/task-implementation.instructions.md
You WILL systematically implement #file:../plans/20260905-01-phase1-security-paydown.plan.md task-by-task, reading each task's full specification from `.copilot-tracking/planning/details/20260905-01-phase1-security-paydown-details.md` before touching code (line ranges are given on every plan checkbox line). You WILL check off each plan item only after its Success block is met AND the user has said "commit" and the commit passed.

Binding operational rules — violations stop the run and escalate to the user:

- **Store ownership**: `./mutants/**`, `scripts/run-mutmut.py`, `make restamp-mutmut-baseline`, and `scripts/mutmut_ledger.py gate|snapshot` belong to the serial pipeline. NEVER invoke them mid-task; between-wave inventory re-measurement happens ONLY through read-only importlib-driven re-derivation under `uv run python` of `scripts/mutmut_ledger.py` + `scripts/mutmut-logic-survivors.py` (method at research Complete Examples L92-138) or visual ledger/gate-report review.
- **Tests**: plain `uv run pytest <touched paths> -q` only — manual `pytest --testmon` / `--testmon-nocollect` is forbidden. If pre-commit fails with unexpected 0% diff coverage, delete `.testmondata` (`rm .testmondata`) and retry the SAME commit once; a second failure escalates instead of hand-running testmon.
- **Commits**: every commit passes the FULL pre-commit chain including the mutation-ledger gate with rc=0 and ZERO KILL REGRESSION events; no `--no-verify`, no `SKIP=` hook bypasses ever. Commit lines ≤80 chars per #file:../../.github/instructions/commit-messages.instructions.md. Expect slow hooks on test commits touching large source modules: scope resolution attributes test-only changes back to imported source modules wholesale (details Gate/Scope Mechanics block), so permissions-scale files take ~2–4 min. This is normal — never "fix" it by weakening tests or bypassing the hook.
- **TDD mapping**: all W1–W4 work retrofits stronger tests over already-correct code → NO stubs and NO xfail markers anywhere outside the Exception Path below (research TR#3 L173). Tests must pass immediately; negative assertions require triggering sibling paths (#file:../../.github/instructions/unit-tests.instructions.md).

Exception Path (any task): if a surviving mutant coincides with VERIFIED wrong current behavior (not uncertainty, not wording preference), switch that item to strict xfail-TDD bug-fix flow (RED with xfail marker proving detection → confirm failed state → fix incl. affected callers/tests in the same phase → GREEN removing only the marker) per #file:../../.github/instructions/test-driven-development.instructions.md §Bug Fixes — and STOP before ANY production change for explicit user sign-off on the behavioral delta first. Back-out rule likewise stops silently-progressed debt: any assertion requiring pinned internal call ORDERING rather than behavior is backed out and recorded in the changes file as deferred debt.

You WILL follow ALL project standards and conventions:

- #file:../../.github/instructions/python.instructions.md for all Python test additions
- #file:../../.github/instructions/self-explanatory-code-commenting.instructions.md for commenting style
- #file:../../.github/instructions/taming-copilot.instructions.md for interaction patterns
- #file:../../.github/instructions/commit-messages.instructions.md when creating commits
- #file:../../.github/instructions/quality-check-overrides.instructions.md — bypass policy reference; NO suppressions are anticipated anywhere in this plan, so any noqa/SKIP request means stop-and-escalate, not apply
- N/A explicitly this phase: containerization-docker-best-practices, reactjs, typescript, github-actions-ci-cd instruction files (zero Docker/frontend/CI files touched); fastapi-transaction-patterns + api-authorization consulted only if a task ever requires touching `services/api` production code beyond W0's single dead-line deletion (should never occur per TDD mapping)

Phase boundaries add verification gates (all wave boundaries):

- `uv run pytest tests/unit -q` green at ≥ 2585 passed / 0 failures / 0 errors, AND the scoped T1 subset grown from its baseline of 248 passed with zero test removals and no xfail markers added anywhere
- `uv run mypy shared/ services/` clean

**CRITICAL**: If ${input:phaseStop:true} is true, you WILL stop after each Phase for user review.
**CRITICAL**: If ${input:taskStop:true} is true, you WILL stop after each Task for user review.
(In this interactive mode BOTH behaviors are effectively always on: announce every completed Task or Phase and wait for the user's explicit "commit" before committing; default to stopping unless the user pre-authorizes continuing within a Phase.)

Task 6.2 restamp gate: do NOT trigger any pipeline store operation yourself. After Task 6.1's sweep is recorded green, present the success-criteria table verification plan line-by-line against research L205-214, state readiness, and WAIT for explicit user approval of both plan completion and the restamp trigger. The restamp then runs ONLY via `make restamp-mutmut-baseline` under that sign-off; afterward verify the archive `.copilot-tracking/testing/mutation-census/YYYYMMDD-restamp-v4-on-develop.json`, ledger stamps, and every per-file residual against the L209 caps (summing ≤ ~50 logic rows), seven-function notests = 0 unresolved, zero KILL REGRESSION events, acceptance list limited to sanctioned groups ≤ ~165 raw string-class ids with logic acceptances = 0 — recording misses as STOP-and-report rather than re-running without a new decision. Commit ledger + census artifacts through the full chain only when the user says commit.

### Step 3: Cleanup

When ALL Phases are checked off (`[x]`) and completed you WILL do the following:

1. You WILL provide a markdown style link and a summary of all changes from #file:../changes/20260905-01-phase1-security-paydown-changes.md to the user:
   - You WILL keep the overall summary brief
   - You WILL add spacing around any lists
   - You MUST wrap any reference to a file in a markdown style link

2. You WILL provide markdown style links to .copilot-tracking/planning/plans/20260905-01-phase1-security-paydown.plan.md, .copilot-tracking/planning/details/20260905-01-phase1-security-paydown-details.md, and .copilot-tracking/research/20260905-01-phase1-security-paydown-research.md documents. You WILL recommend cleaning these files up as well (archive or delete after restamp v4 verification, per user preference).
3. **MANDATORY**: You WILL attempt to delete .copilot-tracking/planning/prompts/implement-phase1-security-paydown.prompt.md

## Failure Triggers (halt + report instead of retrying blind)

- Pre-commit failure twice on the same commit even after the one-shot `.testmondata` deletion → escalate with full hook output.
- Where-clause equality unstable across repeated runs AND compiled-rendering fallback also fails (Task 2.1) → STOP before inventing new techniques; escalate via Exception Path guidance (no raw uncompiled-object string comparisons permitted).
- Strict-zip testing surfaces semantics surprising enough to warrant a production change (Task 4.6) → Exception Path sign-off flow; do NOT harden silently.
- Any KILL REGRESSION event in gate output → treat as regression investigation FIRST; no further commits until root cause recorded in changes file and resolved with user visibility.
- Restamp target miss at Task 6.2 → report delta line-by-line vs L205-214; do not re-run the pipeline without a fresh user decision (store hygiene: one cold pass per store state).

## Success Criteria

- [ ] Changes tracking file created and updated continuously from Step 1 onward
- [ ] All plan items implemented with working code; every checkbox reflects a committed, chain-passed change (W0 dead line deleted; W1–W3 pinning landed; W2 notests conversion complete for all seven functions; W4 log asserts + acceptance draft complete)
- [ ] All detailed specifications satisfied per task Success blocks
- [ ] Zero KILL REGRESSION events across the entire phase; mutation-ledger gate rc=0 on every commit; no `--no-verify`/`SKIP=`; no manual mutmut/testmon execution
- [ ] Suite floors held at every wave boundary (`uv run pytest tests/unit -q` ≥ 2585 passed / 0 fail / err; scoped T1 subset grown-from-248 only); mypy clean; zero xfail markers added anywhere
- [ ] Restamp v4 (user-approved, serial-pipeline-only): archive census exists under `.copilot-tracking/testing/mutation-census/YYYYMMDD-restamp-v4-on-develop.json`; logic rows ≤ ~50 total with per-file L209 caps met; seven-function notests = 0 unresolved; acceptance list sanctioned-groups-only ≤ ~165 raw string-class ids with logic acceptances = 0
- [ ] Project conventions followed; new and modified test code passes lint with required assertions
- [ ] Line numbers updated if any referenced files changed during execution
