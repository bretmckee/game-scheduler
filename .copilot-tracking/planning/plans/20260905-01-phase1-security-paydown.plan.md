---
applyTo: '.copilot-tracking/planning/changes/20260905-01-phase1-security-paydown-changes.md'
---

<!-- markdownlint-disable-file -->

# Task Checklist: Phase 1 Security Paydown (T1 auth/tokens/oauth2/roles/permissions Mutation Debt)

## Overview

Eliminate T1 security-surface mutation-testing debt on branch `develop` by killing surviving logic-class mutants through unit-test strengthening (zero expected production behavior changes), converting all notests rows in seven untested security functions to tested status, and closing the phase with a serial-pipeline-ledger restamp v4 verified against measured per-file targets.

## Objectives

- Reduce T1 logic-class surviving debt from baseline **352 ledger rows / 440 raw ids** (verified @ `develop` HEAD `15e318c9`) to **≤ ~50 rows** at restamp v4, respecting per-file caps (details Success Criteria table; research success table L205-214).
- Convert all **47 notests rows / 51 raw ids** in the seven untested security functions (tokens ×4 crypto/lifecycle helpers + roles `_get_cache`/`check_bot_manager_permission`) to tested verdicts with zero untested rows remaining there.
- Achieve **zero KILL REGRESSION events** across every phase commit and unresolved-none at restamp; mutation-ledger gate rc=0 on every commit with no suppressed hooks (`--no-verify`/`SKIP=` forbidden).
- Keep the unit suite above floors at each wave boundary: full ≥ **2585 passed**, scoped T1 subset ≥ **248 passed** (both measured without `--testmon`; subsets may only grow — no test removals, no xfail markers ever added outside the documented Exception Path), mypy clean.
- Record string-class acceptance ONLY for sanctioned groups (header-case ×8, codec-equivalence ×1, message-wording residual) totaling ≤ ~165 raw string-class ids fixed at restamp time; **logic-class acceptances = 0**; S-other behavioral literals remain tracked killable debt.

## Research Summary

### Project Files

- `services/api/dependencies/permissions.py` - largest T1 debtor: 85 logic / 53 string rows; dead-code deletion target @ L409; security-semantics flips incl. fail-open m19 ≈L84, snowflake-bound m2/m3 in `_resolve_guild_id`, four redis-guard negations
- `services/api/auth/tokens.py` - 69 logic / 58 string / 27 notests rows; payload value-drop families + crypto helpers untested (`ljust` key-length boundary paths)
- `services/api/middleware/authorization.py` - single dispatch family: 39 logic / 21 string rows; branch-flip pins m34/m51 @ ≈L80 then bulk arg/value pinning
- `services/api/auth/oauth2.py` - 33 logic / 26 string rows across six families; `validate_state` thinnest test mapping (2 tests / 11 rows); verified fail-CLOSED default-nullings (disproof example L118 of research)
- `services/bot/auth/role_checker.py` - 28 logic / 14 string rows; fail-closed guard flips m6/m7 + DB query arg nullings; file-wide logger cluster defers to Phase 5
- `services/api/config.py` - 27 logic / 19 string rows; rate-limit `range(1,n+1)` off-by-one ×5, cookie-domain hidden edits, strict-zip behavioral-risk pins m20/m21
- `services/bot/auth/cache.py` - 27 logic / 18 string rows; `RoleCache.get_user_roles` ~16-row head + RedisClient None-guard nullings
- `services/api/auth/roles.py` - 23 logic / 3 string / 20 notests rows; host-permission pair m9+m10 @L234/L235, implicit-bit mutants m37/m44 @L170/L172, grant-all flip m58; two untested functions
- `services/api/dependencies/auth.py` - 11 logic / 4 string rows; four 401 raise sites verified at L65/69/72/82 with details "Not authenticated"/"Session not found"/"Token expired"/"User not found"; where-clause flip m36 @ ≈L77 (fails closed, untested)
- `services/api/middleware/error_handler.py` - 7 logic / 32 string rows; status/detail kwarg pins only (string literals to acceptance)
- `shared/utils/discord_tokens.py` - 3 logic / 1 string row; base64 pad-math `%4→%5` exact-value kills; utf-8 alias equivalence → acceptance list
- `services/api/middleware/cors.py` - 2 string rows only; optional origin-list assert in the tail-fold commit
- `scripts/mutmut_ledger.py` - gate/ratchet implementation: scope resolution `compute_scope` L333-370 (test-only commits attribute via `"*"` whole-module sentinel), blocking semantics `cmd_gate` L850-894 (FAIL = new logic survivors OR kill regressions only); read-only reference throughout
- `mutmut-baseline.json` - committed v2 ratchet ledger (repo root): `entries` + tracked `killed` maps; rewritten ONLY by the Task 6.2 pipeline run
- `tests/unit/services/**/test_*.py` (per-file test modules named in details tasks) - extension bases for all strengthening work; fixture scaffolding per research Dependencies L204

### External References

- #file:../../research/20260905-01-phase1-security-paydown-research.md - validated Phase 1 research (214 lines @ HEAD `15e318c9`): verified debt inventory, cluster taxonomy with expected kill counts, wave plan W0–W5, success-criteria table (L205-214); independently cross-checked this session (zero-mismatch reproduction of 60/60 T1 families from live store data)
- #githubRepo:"boxed/mutmut 3.x timeout watchdog issue 518" - inherited provenance via research External Research section (L50-52): store verdict code vocabulary (`STATUS_TO_CLASS`: `-24`/`36` timed-out etc.) and `timeout_constant=4.0` context established in Phase 0 doc `20260901-01-mutmut-upgrade-validation-research.md`; no new upstream behavior needed for T1 paydown
- #fetch:[mutmut on PyPI](https://pypi.org/project/mutmut/) - pinned version **3.7.0** as validated by the Phase 0 upgrade work; unchanged input to this phase (research L54-55)

### Standards References

- #file:../../../.github/instructions/test-driven-development.instructions.md - retrofitting rule (tests over correct code pass immediately — NO stubs/xfail) + strict xfail bug-fix flow reserved for the Exception Path only
- #file:../../../.github/instructions/unit-tests.instructions.md - falsifiability, required assertions, sanctioned `ANY` usage, negative-assertion triggering-sibling requirement
- #file:../../../.github/instructions/python.instructions.md - style/type-hint/lint rules for any test additions touching Python files
- #file:../../../.github/instructions/commit-messages.instructions.md - ≤80-char commit lines, conventional format per phase/task commits
- #file:../../../.github/instructions/quality-check-overrides.instructions.md - bypass policy reference; NO suppressions anticipated in this plan (any request stops the task and escalates)

## Implementation Checklist

### [ ] Phase 1: W0 Hygiene — Dead-Code Deletion (first commit of the phase)

- [ ] Task 1.1: Delete unreachable `return current_user` at `services/api/dependencies/permissions.py` L409 with grep evidence recorded (all remaining occurrences reachable); mypy clean + full pre-commit chain gate rc=0
  - Details: .copilot-tracking/planning/details/20260905-01-phase1-security-paydown-details.md (Lines 48-63)

### [ ] Phase 2: W1 Security-Semantics Kills (~25 raw ids / ~20 logic rows)

- [ ] Task 2.1: deps/auth single commit — validate where-clause equality technique (primary spec + documented compiled-rendering fallback + negative control), pin all four 401 raises @L65/69/72/82 by type+status+detail, land m36 where-flip pin
  - Details: .copilot-tracking/planning/details/20260905-01-phase1-security-paydown-details.md (Lines 68-116)

- [ ] Task 2.2: permissions security-semantics pins — snowflake exact-bound fixtures for `_resolve_guild_id`, missing-user-data/stale-projection deny+suppression cases (m19 fail-open), redis-guard negation kills ×4, HTTPException status/detail pins at 503/404 sites
  - Details: .copilot-tracking/planning/details/20260905-01-phase1-security-paydown-details.md (Lines 117-138)

- [ ] Task 2.3: roles security-semantics pins — empty-restriction hosting case killing m9+m10 pair with manager-hit sibling, unknown-role bit-defaults remain exactly 0 killing m37/m44, grant-all flip m58 deny-pins
  - Details: .copilot-tracking/planning/details/20260905-01-phase1-security-paydown-details.md (Lines 139-159)

- [ ] Task 2.4: middleware/authorization dispatch branch-flip pins — response-object contract + capture-based adjacent-log discrimination killing m34/m51 while in-file (wording-as-discriminator exception noted inline)
  - Details: .copilot-tracking/planning/details/20260905-01-phase1-security-paydown-details.md (Lines 160-180)

### [ ] Phase 3: W2 Untested-Function Conversion (notests rows → tested; zero untested remaining in the seven functions)

- [ ] Task 3.1: tokens crypto/lifecycle helpers — pass-immediately tests for `get_encryption_key` (exact length + ljust boundary pair), real-Fernet round-trip encrypt/decrypt with tamper-raise, `is_token_expired` boundary triplet
  - Details: .copilot-tracking/planning/details/20260905-01-phase1-security-paydown-details.md (Lines 185-205)

- [ ] Task 3.2: roles untested functions — `_get_cache` configured/unconfigured siblings with no-DB negative assert; `check_bot_manager_permission` manager-hit / fallback-to-MANAGE_GUILD both branches / unconfigured deny
  - Details: .copilot-tracking/planning/details/20260905-01-phase1-security-paydown-details.md (Lines 206-225)

### [ ] Phase 4: W3 Bulk Arg/Value Pinning (~294 raw ids / ~235 rows ≈70% of remaining logic debt)

- [ ] Task 4.1: permissions A1 bulk pinning — exact-arg mock asserts + payload-provenance pins across remaining families (back-out rule enforced); residual ≤15 rows
  - Details: .copilot-tracking/planning/details/20260905-01-phase1-security-paydown-details.md (Lines 230-242)

- [ ] Task 4.2: tokens A1 bulk pinning — Redis call-arg/key provenance, returned-dict field assertions for value-drop families, `os.getenv` propagation pins; residual ≤12 rows
  - Details: .copilot-tracking/planning/details/20260905-01-phase1-security-paydown-details.md (Lines 243-255)

- [ ] Task 4.3: middleware/authorization dispatch residual (CONFIRMED INSERTION #1 by row count) — header-stamping arg pins on concrete request fixtures, duration sign-flips pinned behaviorally under monkeypatched clock with `ANY` wording, anonymous-restructure None/set siblings; residual ≤6 rows
  - Details: .copilot-tracking/planning/details/20260905-01-phase1-security-paydown-details.md (Lines 256-268)

- [ ] Task 4.4: bot/auth/cache pinning — exact cache-key strings + ttl values, return-shape provenance across get_user_roles + guard nullings; residual ≤5 rows
  - Details: .copilot-tracking/planning/details/20260905-01-phase1-security-paydown-details.md (Lines 269-281)

- [ ] Task 4.5: auth/oauth2 pinning — `validate_state` raise-site pins from fresh re-derived family list, exact params-dict for authorization URL, Discord-API call args @~L123, fail-closed default-nulling reachability fixtures m6/m8 + team-member drops m22/m24/m31/m33; residual ≤6 rows
  - Details: .copilot-tracking/planning/details/20260905-01-phase1-security-paydown-details.md (Lines 282-294)

- [ ] Task 4.6: api/config pinning — full-env `os.getenv` propagation incl. hidden cookie-domain sites, n=1 boundary killing five range off-by-one variants, strict-zip behavioral-risk pins m20/m21 with TR#5 sign-off caveat; residual ≤5 rows
  - Details: .copilot-tracking/planning/details/20260905-01-phase1-security-paydown-details.md (Lines 295-307)

- [ ] Task 4.7: bot/auth/role_checker pinning (CONFIRMED INSERTION #2 by row count) — DB query arg nulling with exact execute-args asserts, fail-closed deny outcomes for m6/m7 no-row/error siblings; logger debt defers to Phase 5; residual ≤5 rows
  - Details: .copilot-tracking/planning/details/20260905-01-phase1-security-paydown-details.md (Lines 308-320)

- [ ] Task 4.8: middleware/error_handler logic tail — response-status + detail kwarg pins per handler family; its string literals defer to Phase 5 acceptance; residual ≤2 rows
  - Details: .copilot-tracking/planning/details/20260905-01-phase1-security-paydown-details.md (Lines 321-333)

- [ ] Task 4.9: TAIL FOLD COMMIT (single commit per research L190 fold rule) — deps/auth residual A1 + `shared/utils/discord_tokens.py` pad-math exact-value kills remainders 0..3 [+ optional cors origin-list assert]; back-out sites recorded in changes file
  - Details: .copilot-tracking/planning/details/20260905-01-phase1-security-paydown-details.md (Lines 334-354)

### [ ] Phase 5: W4 Logger/Message Resolution + Acceptance Bookkeeping (~84 logic rows)

- [ ] Task 5.1: Structural log asserts for remaining LOGIC-class logger-arg mutants using sanctioned `ANY` wording, driven from a pre-task re-derived inventory (Complete Examples method); commits per touched test file in Phase-4 order with before/after id lists recorded
  - Details: .copilot-tracking/planning/details/20260905-01-phase1-security-paydown-details.md (Lines 359-372)

- [ ] Task 5.2: Acceptance bookkeeping (doc-only) — draft the string-class acceptance table into the changes tracking file (header-case ×8 / codec-equivalence ×1 / message-wording residual / error-detail residual groups), explicit exclusions verbatim (S-other behavioral literals NOT acceptable; logic acceptances = 0), final counts fixed at restamp v4
  - Details: .copilot-tracking/planning/details/20260905-01-phase1-security-paydown-details.md (Lines 373-395)

### [ ] Phase 6: W5 Phase-End Hygiene & Restamp

- [ ] Task 6.1: Pre-restamp verification sweep — full suite ≥2585 passed / scoped subset grown-from-248 with zero removals or xfails, mypy clean, STALE-row review clean-or-regression-investigation, optional read-only dry-run re-derivation previewing the v4 census delta; record all outputs in changes file
  - Details: .copilot-tracking/planning/details/20260905-01-phase1-security-paydown-details.md (Lines 398-410)

- [ ] Task 6.2: Serial-pipeline restamp → census v4 under EXPLICIT USER APPROVAL only (implementer never triggers): verify archive `.copilot-tracking/testing/mutation-census/YYYYMMDD-restamp-v4-on-develop.json` + ledger stamps against every success-table row line-by-line; commit artifacts when user says commit
  - Details: .copilot-tracking/planning/details/20260905-01-phase1-security-paydown-details.md (Lines 411-426)

## Dependencies

- Mutation store `./mutants/**` (serial-pipeline-owned; read-only during this phase via importlib-loaded project scripts for between-wave target re-derivation — method at research Complete Examples L92-138)
- Project scripts loaded unmodified: `scripts/mutmut_ledger.py`, `scripts/mutmut-logic-survivors.py` (target re-derivation only)
- Existing fixture scaffolding as extension bases: `tests/unit/services/bot/auth/test_role_checker.py` db-mock style, `tests/unit/services/api/dependencies/test_api_permissions.py`, existing tokens/oauth2/config test modules
- Binding instruction files: TDD / unit-tests / python / commit-messages / quality-check-overrides (see Standards References) plus house no-manual-testmon rule (research TR#4 @ L174)
- End-of-phase restamp executed ONLY by the serial pipeline after user approval of plan completion (Task 6.2 gate)

## Success Criteria

- Restamp v4 verdict census shows T1 logic rows ≤ ~50 total with every file at or under its cap (permissions ≤15 · tokens ≤12 · authorization ≤6 · oauth2 ≤6 · role_checker ≤5 · config ≤5 · cache ≤5 · roles ≤5 · auth-dep ≤2 · error_handler ≤2 · discord_tokens ≤1 · cors 0); measured via the validated zero-mismatch re-derivation method against store metas + regenerated ledger rows; interim preview available at Task 6.1 dry run.
- Seven-function notests rows = 0 unresolved in the store-verdict census at restamp v4; any survivors counted as gated logic debt against their file targets and reported explicitly.
- Zero KILL REGRESSION events across all phase commits (pre-commit ledger-gate output captured per commit) and unresolved-none at restamp (restamp report regression preview clean).
- Unit suite floors held at every wave boundary: `uv run pytest tests/unit -q` ≥ 2585 passed / 0 failures / 0 errors, scoped T1 subset grown from baseline 248 passed with no test removals and NO xfail markers ever added; `uv run mypy shared/ services/` clean.
- Gate hygiene: mutation-ledger gate rc=0 on every single commit, no `--no-verify`/`SKIP=` anywhere, no manual mutmut or `pytest --testmon` execution during the phase, `.testmondata` absent or deleted-stale rule honored when triggered.
- Acceptance bookkeeping: restamp-v4 acceptance list contains only the sanctioned Task 5.2 groups totaling ≤ ~165 raw string-class ids each citing its justification class, with **logic-class acceptances = 0**; S-other behavioral literals remain tracked killable debt after restamp.
