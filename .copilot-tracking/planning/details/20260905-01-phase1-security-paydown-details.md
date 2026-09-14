<!-- markdownlint-disable-file -->

# Task Details: Phase 1 Security Paydown (T1 auth/tokens/oauth2/roles/permissions Mutation Debt)

## Research Reference

**Source Research**: #file:../../research/20260905-01-phase1-security-paydown-research.md (214 lines @ `develop` HEAD `15e318c9`)

Verified section map of the source research (all ranges re-checked against the current file on 2026-09-05):

| Section                      | Lines    | Contents relied upon here                                                                                                                                                                                                                                                                                                                     |
| ---------------------------- | -------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| File Analysis                | L11-30   | Per-file debt rows: permissions **L17**, tokens **L18**, authorization-mw **L19**, oauth2 **L20**, role_checker **L21**, config **L22**, cache **L23**, roles **L24**, deps/auth **L25**, error_handler **L26**, discord_tokens **L27**, cors **L28**                                                                                         |
| External Research            | L48-56   | Inherited provenance only (mutmut#518 watchdog context, PyPI pin 3.7.0); no new external facts needed                                                                                                                                                                                                                                         |
| Project Conventions          | L58-61   | Standards/instructions applied throughout this plan                                                                                                                                                                                                                                                                                           |
| Project Structure findings   | L65-70   | Ledger-row vs raw-id units (L67), family-key format U+01C1 (L68), zero-mismatch baseline reproduction (L69), gate semantics at HEAD (L70)                                                                                                                                                                                                     |
| Implementation Patterns      | L72-91   | Cluster taxonomy A1–A6 / S-header / S-encoding / S-msg / S-other with expected kill counts                                                                                                                                                                                                                                                    |
| Complete Examples            | L92-138  | Reproducible ledger/store re-derivation method (uv run python + importlib of the two project scripts; read-only) and full-diff verified examples: oauth2 m6 disproof **L118**, snowflake bounds **L122**, where-flip m36 **L127**, roles host-permission pair **L131**, config strict-zip **L135**                                            |
| API and Schema Documentation | L140-144 | Store meta schema / exit-code vocabulary (`mutmut-stats.json` mapping caveats L143-144)                                                                                                                                                                                                                                                       |
| Configuration Examples       | L146-168 | Per-file row-count tables used for targets                                                                                                                                                                                                                                                                                                    |
| Technical Requirements       | L169-175 | TR#1 first-to-kill flips/boundaries **L171**; TR#2 hard boundaries **L172**; TR#3 TDD applicability statement **L173**; TR#4 house rules incl. no manual `--testmon` **L174**; TR#5 sign-off caveat (zero confirmed weaknesses) **L175**                                                                                                      |
| Recommended Approach         | L177-193 | Selected sequencing rationale **L179**; wave plan W0–W5 **L181-188**; commit granularity rule **L190**; verification loop **L192**                                                                                                                                                                                                            |
| Implementation Guidance      | L194-214 | Objectives **L196**; strategy table A/B′/C/D/E + acceptance groups **L197-203**; dependencies **L204**; success-criteria table **L205-214** (logic-row targets per file **L209**, notests conversion **L210**, kill-regression zero-tolerance **L211**, suite-health floors **L212**, gate hygiene **L213**, acceptance bookkeeping **L214**) |

## Overview

Phase 1 eliminates the T1 security-surface mutation debt measured on branch `develop` @ `15e318c9`: baseline **352 ledger rows / 440 raw logic-class survivor ids** across 12 files, plus 47 notests rows in seven untested security functions. Strategy: unit-test strengthening first (retrofit coverage over already-correct code), defensive hardening only if a genuine weakness surfaces (none confirmed by verified full-diff re-examination — research TR#5 L175), documented string-class acceptance last with zero logic-class acceptances. Expected outcome at restamp v4: T1 logic rows ≤ ~50 (per-file caps below), seven-function notests rows = 0 unresolved, zero KILL REGRESSION events across every phase commit, and no production behavior change anywhere in the phase.

## Binding Operational Rules (all phases, all tasks, all commits)

- Mutation store ownership: `./mutants/**` belongs to the serial pipeline. NEVER manually run `make restamp-mutmut-baseline`, `scripts/run-mutmut.py`, or `scripts/mutmut_ledger.py gate|snapshot` during task work. The sole exception is Task 6.2, which runs ONLY through the serial-pipeline make target under explicit user sign-off after all phases complete.
- Unit tests: plain `uv run pytest <paths> -q` only. Manual `pytest --testmon` / `--testmon-nocollect` is prohibited (advances `.testmondata` so pre-commit then sees 0 changed files and diff coverage fails). If `.testmondata` goes stale mid-phase (symptom: unexpected 0% diff coverage in pre-commit), delete it (`rm .testmondata`) and retry — never hand-run testmon.
- Commits: every commit passes the FULL pre-commit chain including the mutation-ledger gate with rc=0 and **zero** KILL REGRESSION events; no `--no-verify`, no `SKIP=` env bypasses of any hook. Commit message lines ≤80 chars per #file:../../../.github/instructions/commit-messages.instructions.md.
- Push policy: the implementer NEVER pushes. Work is interactive — announce each completed phase/task, wait for the user's explicit "commit" before running `git commit`, and the user pushes as needed between phases.
- Target re-derivation between waves is allowed using the project scripts loaded unmodified via importlib under `uv run python` against read-only store data (method at research L92-138); this mutates nothing.
- TDD mapping (per #file:../../../.github/instructions/test-driven-development.instructions.md): all W1–W4 strengthening work retrofits tests onto already-correct code → NO stubs, NO xfail markers ever outside the Exception Path below. Tests must pass immediately with stronger, falsifiable assertions (one observable contract per test; negative assertions require a triggering sibling path per #file:../../../.github/instructions/unit-tests.instructions.md).

## Gate / Scope Mechanics on Test-Only Commits (why hooks look slow)

Verified against `compute_scope` in `scripts/mutmut_ledger.py` **L333-370**: scope = union of (a) function families of changed source lines and (b) every mutant of modules that changed test files import (the `"*"` whole-module sentinel at L353-356 — a deliberate conservative killer-weakening check for tests-only PRs). Unmapped test paths produce WARN only (L357-364). The committed ledger contains ZERO entries under `tests/`, and unchanged source functions re-judge to verdicts identical to baseline (neither new nor stale), so newly added test logic can never self-trip the ratchet gate. Consequence to expect and not "fix": each commit touching tests will make the hook re-judge the whole imported source module(s) — roughly 2–4 min wall for permissions-scale files while unpushed delta accumulates; the user's interactive pushes keep this bounded. Per-commit verification order: `uv run pytest <touched test paths> -q` green → commit through full pre-commit chain.

## Exception Path: Genuine Latent Bug Discovered (applies to any task)

Trigger: a surviving mutant AND verified-wrong behavior on the current code path (not mere uncertainty, not a string-wording preference). Procedure: switch THAT item to the strict xfail-TDD bug-fix flow per #file:../../../.github/instructions/test-driven-development.instructions.md (§TDD for Bug Fixes): RED with an xfail marker proving detection, confirm the xfailed state, implement the fix in the same phase including every affected caller/test, GREEN with the marker removed. STOP before ANY production change and obtain explicit user sign-off on the behavioral delta first (research TR#3/TR#5 at L173/L175); security-critical authz modules raise the bar — no implicit acceptances. No other task may add stubs or xfail markers under any circumstances.

## Phase 1: W0 Hygiene — Dead-Code Deletion (first commit of the phase)

### Task 1.1: Remove unreachable `return current_user` at permissions.py L409

Delete the single dead line inside `require_manage_guild`: the bare `    return current_user` immediately following the multi-line `return await _require_permission(...)` call. Verified in-file today: that block sits after the unconditional `return await ...`, so the trailing statement is unreachable; it is the sole occurrence of this pattern (all three helper call-sites scanned in research). Implementation-time verification (before deletion): `grep -n 'return current_user' services/api/dependencies/permissions.py` must show the remaining occurrences each in a reachable position (maintainer-bypass early returns / function tails) — record the grep output in the changes file as evidence. Pure deletion, zero observable change, no caller migration required (the three wrapper dependencies are untouched). Landing this FIRST keeps mutant ids for later functions stable across the rest of the phase (ids shift only when earlier code text changes). Production-code edit inside an authz-critical file → mypy clean and full pre-commit chain (incl. ledger gate rc=0) are explicit completion requirements. No new test is meaningful here (nothing newly observable to assert); existing suite coverage of `require_manage_guild` is unchanged.

- **Files**:
  - `services/api/dependencies/permissions.py` - delete line L409 (`return current_user`)
- **Success**:
  - grep evidence recorded showing all surviving `return current_user` sites reachable
  - `uv run pytest tests/unit -q` green at ≥ baseline suite floor (see Phase gates)
  - `uv run mypy shared/ services/` clean
  - commit passes full pre-commit chain incl. mutation-ledger gate rc=0 with zero KILL REGRESSION events; hook scope = single family (`require_manage_guild`)
- **Research References**:
  - #file:../../research/20260905-01-phase1-security-paydown-research.md (Lines 17-18, File Analysis permissions row — dead code + verified survivors list), (Lines 31-47 Code Search Results sole-match scan), (Lines 183 W0 wave directive), (Lines 197-203 strategy E "no confirmed hardening required")
- **Dependencies**:
  - None — first task of the phase; must land before any other phase work so later mutant ids stay stable.

## Phase 2: W1 Security-Semantics Kills (~25 raw ids / ~20 logic rows; research L184, strategy A at L198)

Phase note: every test in this phase passes immediately against current behavior (retrofit rule). Expected kills come from clusters A6/A4/A2 plus the where-flip per research taxonomy (Implementation Patterns L72-91).

### Task 2.1: deps/auth — validate where-clause technique AND pin all 401s + m36 (single commit)

One commit for file×step `services/api/dependencies/auth.py` × W1 in `tests/unit/services/api/dependencies/test_auth_dependency.py`. Step order inside the task:

1. **Validate the where-clause equality technique FIRST** (research flags one-time validation before templating anywhere else). Primary spec: capture via a mocked session `side_effect` the `Select` object passed to `db.execute`, build an independent reference statement, and assert both positive and negative controls:

   ```python
   stmt = captured_stmt  # Select passed into db.execute by get_current_user
   reference = select(user_model.User).where(
       user_model.User.discord_id == discord_id
   )
   assert stmt.whereclause == reference.whereclause  # criterion (a): selects by equality
   flipped = select(user_model.User).where(
       user_model.User.discord_id != discord_id
   )
   assert stmt.whereclause != flipped.whereclause    # negative control (b): discriminative
   ```

   PASS criteria: (a) holds on the installed SQLAlchemy version; (b) the `!=` variant is NOT equal (proves the assertion has teeth against the exact surviving mutation m36 `==→!=` at ~L77 — verified diff example research L127). Record the SQLAlchemy version in the changes file.

2. **Documented fallback** (apply only if the primary errors or gives unstable results across repeated runs/pins): render both whereclauses through SQLAlchemy's SQLite dialect compiler and compare rendered strings with the same two-criterion structure:

   ```python
   from sqlalchemy.dialects import sqlite

   def _render(wc):
       return str(wc.compile(dialect=sqlite.dialect()))

   assert _render(stmt.whereclause) == _render(reference.whereclause)
   assert _render(stmt.whereclause) != _render(flipped.whereclause)
   ```

   Rationale: deterministic SQL renderer inside the pinned venv (statement-level rendering, not source-text comparison); behavior contract remains "the WHERE clause selects by equality on `discord_id`". Check existing unit-test fixtures for an in-memory-SQLite pattern first; if one exists and row-level behavioral pinning is feasible there, prefer it as Fallback A over compiled-rendering. If even that is unstable: STOP and escalate via the Exception Path before inventing new techniques (no over-fragile raw-string comparisons of uncompiled objects).

3. **Land all four 401 raise pins** in the same commit: `pytest.raises(HTTPException)` capturing status_code==401 AND exact detail string at each site — verified current lines/details in `services/api/dependencies/auth.py`: **L65** `"Not authenticated"`, **L69** `"Session not found"`, **L72** `"Token expired"`, **L82** `"User not found"` (`get_current_user` def @ L45). One sibling test per raise path with distinct fixture conditions so each pin's kill is attributable.
4. Where-clause equality assertion lands as the m36 pin once validation passes (or fallback spec active), in this same file/commit.

Expected kills: m36 (where-flip) + the four detail-null/drop survivors ≈ 5 logic-class ids from clusters A4/A2.

- **Files**:
  - `tests/unit/services/api/dependencies/test_auth_dependency.py` - modify/add (pins above; extend existing fixtures rather than duplicating scaffolding)
  - `services/api/dependencies/auth.py` - read-only reference for sites and details strings
- **Success**:
  - Validation criteria (a)+(b) recorded as PASS or Fallback-A active, with SQLAlchemy version noted
  - scoped run green: `uv run pytest tests/unit/services/api/dependencies/test_auth_dependency.py -q`
  - commit through full pre-commit chain rc=0, zero KILL REGRESSION events; hook re-judges deps/auth module only (fast)
- **Research References**:
  - #file:../../research/20260905-01-phase1-security-paydown-research.md (Lines 25 per-file row — deps/auth 11 logic / 4 string), (Lines 79-83 Implementation Patterns A2/A4 cluster rows), (Lines 127-129 verified diff of m36 flip fails-closed-untested), (Lines 171 TR#1 first-to-kill list), (Lines 184 W1 where-clause directive)
- **Dependencies**:
  - Phase 1 (W0) complete so permissions-module ids stay stable (no hard dependency on this file's own ids, but keeps phase-wide id reasoning consistent).

### Task 2.2: permissions security-semantics pins (`test_api_permissions.py`)

Single commit for `services/api/dependencies/permissions.py` × W1. Test additions in the existing fixture base at `tests/unit/services/api/dependencies/test_api_permissions.py`:

1. `_resolve_guild_id` snowflake exact-boundary fixtures (kills m2/m3; verified example research L122): construct valid-format ids with length exactly at the min and max allowed bounds → must resolve via the fast path; assert the resolved value AND that no DB round-trip occurs at those lengths (negative assertion needs triggering sibling: an out-of-bounds-length case exercising the fallback path).
2. Missing-user-data & stale-projection cases for `_check_guild_membership` / `verify_guild_membership` (incl. fail-open direction flip m19 ≈L84 — guarded deny must return False/deny AND suppress the downstream lookup the flipped guard would let run; assert suppression with `assert_not_called` on the sibling-path mock per unit-tests negative-assertion standard). The hidden arg-nulling edit inside the stale-bot guard line (`if not await member_projection.is_bot_fresh(redis=redis):`, located past the ledger's 48-char clip) — derive its exact site from the full-diff re-derivation method at implementation time and pin the deny-path outcome for a stale projection.
3. Redis-guard negation kills ×4 (`if redis is None:` → `is not None:` across verify/get-guild-name paths, research L17 row): pass an explicit caller-provided client into each affected path and assert THAT client was used (call-spy asserts), not overwritten by the singleton. One test per guard site with the caller-client fixture; keep wording/args behavior-relevant only.
4. HTTPException type+status_code+detail pins at every 503/404 raise site in this file (same pattern as Task 2.1 step 3; enumerate sites via grep of `HTTPException(` during implementation).

Expected kills: m19, m2/m3, the hidden stale-bot nulling, 4× redis-guard negations, 503/404 detail/status survivors ≈ 10–12 logic-class ids / ~8–10 rows.

- **Files**:
  - `tests/unit/services/api/dependencies/test_api_permissions.py` - modify/add (extend existing db-mock/redis fixtures)
  - `services/api/dependencies/permissions.py` - read-only reference (sites enumerated above)
- **Success**:
  - scoped run green on the touched test file
  - commit through full pre-commit chain rc=0, zero KILL REGRESSION events
- **Research References**:
  - #file:../../research/20260905-01-phase1-security-paydown-research.md (Lines 17 File Analysis permissions row incl. verified survivors list), (Lines 122-125 snowflake + fail-open diff examples), (Lines 171 TR#1(a)/(d)), (Lines 184 W1 directive), (Lines 204 dependencies — fixture scaffolding base)
- **Dependencies**:
  - Phase 1 (W0) complete; Task 2.1 independent (separate module).

### Task 2.3: roles security-semantics pins (`test_roles.py`)

Single commit for `services/api/auth/roles.py` × W1 in `tests/unit/services/api/auth/test_roles.py`. Verified mapping (correcting any brief-level conflation): m9/m10 are the host-permission guard PAIR at L234/L235; the implicit-bit mutants are m37/m44 at L170/L172; m58 is the grant-all flip (site ≈L163/L181 region — disambiguate exact site via full-diff re-derivation at implementation time):

1. `check_game_host_permission` empty-restriction hosting case (kills paired m9 @ L234 guard-negation AND m10 @ L235 `return False→True`; verified example research L131): fixture with allowed-host-role-ids empty and a non-manager user → must return deny-False. Include the manager-hit sibling (is-bot-manager True → allow-True) so BOTH flip directions of the pair are falsifiable by separate tests.
2. `has_permissions` unknown-role permission-bit defaults remain exactly 0 (kills implicit-bit mutants m37 init constant L170 + m44 `.get(...)` default L172, "implicit granted +1 bits on unknown roles"): fixture where one of the user's role ids is absent from guild_roles → that id's contribution must be exactly 0 bits; assert the precise resulting permission outcome for a request whose satisfaction depends on any bit such an unknown role could silently contribute.
3. `has_permissions` fail-open pin m58: error-path / no-guild-roles cases must return deny-False (grant-all under mutation would flip this); drive both entry conditions and assert denial without exception leakage.

Expected kills: m9+m10 pair, m37+m44, m58 ≈ 5 logic-class ids / ~4 rows.

- **Files**:
  - `tests/unit/services/api/auth/test_roles.py` - modify/add
  - `services/api/auth/roles.py` - read-only reference (L163/L170/L172/L181/L234/L235 regions)
- **Success**:
  - scoped run green on touched test file
  - commit through full pre-commit chain rc=0, zero KILL REGRESSION events
- **Research References**:
  - #file:../../research/20260905-01-phase1-security-paydown-research.md (Lines 24 File Analysis roles row — incl. notests concentration), (Lines 131-133 verified host-permission diff), (Lines 171 TR#1(a)-(c)), (Lines 184 W1 directive)
- **Dependencies**:
  - Phase 1 (W0) complete; independent of Tasks 2.1–2.2.

### Task 2.4: middleware/authorization dispatch branch-flip pins (`test_authorization.py`)

Single commit for `services/api/middleware/authorization.py` × W1 in `tests/unit/services/api/middleware/test_authorization.py`. The module is logging-only observability over request flow (research L19 row); its two surviving branch flips are m34 @ ≈L80 (`==→!=` on the HTTP_403 branch) and the paired flip at the adjacent raise-condition site (m51). Kill mechanics while in-file:

1. Response-object contract assertions: drive a mocked `call_next` to return each status class (403, 401, 2xx) and assert the response passes through unmodified (status preserved, X-User-Id / X-Request-Id headers stamped from concrete request fixtures) — this anchors behavior regardless of how log internals evolve.
2. Capture-based log discrimination where needed between ADJACENT similar log lines: assert exactly ONE of the two distinct messages fires for a 403 response and neither for 401/2xx as applicable. Here exact wording IS the discriminator (branch identity is the observable contract), which intentionally departs from the Phase 5 ANY-wording rule; note this exception inline in the test docstring.
3. No assertion may depend on internal call ordering or on non-deterministic fields (timestamps beyond pinned-clock techniques reserved for Task 4.3).

Expected kills: m34 + m51 branch flips = 2 logic-class ids (response-object pins back them up if the log path is later refactored away).

- **Files**:
  - `tests/unit/services/api/middleware/test_authorization.py` - modify/add
  - `services/api/middleware/authorization.py` - read-only reference (dispatch family L79-81 cluster region per research patterns section)
- **Success**:
  - scoped run green on touched test file
  - commit through full pre-commit chain rc=0, zero KILL REGRESSION events
- **Research References**:
  - #file:../../research/20260905-01-phase1-security-paydown-research.md (Lines 19 File Analysis authorization row — dispatch 39 logic / thinnest-mapping evidence), (Lines 79-81 Implementation Patterns A2/A4 rows listing dispatch m34/m51), (Lines 184 W1 "kill dispatch m34/m51 ... while in-file")
- **Dependencies**:
  - Phase 1 (W0) complete; independent of Tasks 2.1–2.3. Remaining dispatch debt (arg/value nullings, duration sign-flips, anonymous restructure) lands in Task 4.3 and Phase 5 log asserts — do NOT attempt them here to keep the W1 commit focused on branch flips.

## Phase 3: W2 Untested-Function Conversion (notests 51 ids / 47 rows → zero untested rows remaining in the seven functions)

Phase note (TDD retrofitting rule applies strictly): new tests PASS IMMEDIATELY with falsifiable assertions; NO stubs, NO xfail markers. The seven functions: tokens `{get_encryption_key, is_token_expired, decrypt_token, encrypt_token}` + roles `{_get_cache, check_bot_manager_permission}` per research L185/L199. After landing, notests rows convert to tested verdicts — simple arg/null assignments in small functions kill outright; any RESIDUAL logic-class survivors in these families reclassify from notests into gated logic debt counted against the per-file targets at restamp v4 (research L210). A genuine bug found here triggers the Exception Path (stop for sign-off before production change).

### Task 3.1: tokens crypto/lifecycle helpers (`test_tokens.py`)

Single commit for `services/api/auth/tokens.py` × W2 in `tests/unit/services/api/auth/test_tokens.py`:

1. `get_encryption_key`: urlsafe-base64 output must decode to exactly ENCRYPTION_KEY_LENGTH bytes; boundary pair around the short-secret branch — monkeypatched `api_config.jwt_secret` SHORT enough that `ljust(...)` pads with `b"0"` AND a LONG sibling where no padding occurs (both sides of the comparison executed; exact pad content asserted in the short case so the literal is pinned behavior-relevantly).
2. `encrypt_token` / `decrypt_token`: prefer REAL Fernet round-trip over mocked construction (so Fernet-construction arguments execute and survive as killed): encrypt then decrypt equals original payload structure; tampered/garbled input raises via `pytest.raises(Fernet.InvalidToken)`.
3. `is_token_expired`: expired-timestamp → True, future-timestamp → False, and the exact-boundary case pinning which side wins at equality.

Expected conversion: all four families' notests rows reclassify; expect most ids killed outright on first judgment (small functions, direct assertions), residual survivors counted per Phase note.

- **Files**:
  - `tests/unit/services/api/auth/test_tokens.py` - modify/add (new test class or extension for crypto helpers)
  - `services/api/auth/tokens.py` - read-only reference (key-length constant + ljust site per research L18 row)
- **Success**:
  - scoped run green on touched test file
  - commit through full pre-commit chain rc=0, zero KILL REGRESSION events
- **Research References**:
  - #file:../../research/20260905-01-phase1-security-paydown-research.md (Lines 18 File Analysis tokens row incl. ljust/key-boundary paths), (Lines 88 Implementation Patterns N-class untested-function row), (Lines 173 TR#3 TDD applicability — retrofitting), (Lines 185 W2 directive), (Lines 199 strategy B′)
- **Dependencies**:
  - Phases 1–2 complete (sequential phase discipline); independent of Task 3.2 module-wise but same wave keeps restamp bookkeeping clean.

### Task 3.2: roles untested functions (`test_roles.py`)

Single commit for `services/api/auth/roles.py` × W2 in the same test module as Phase 2 (new additions only — no edits to Task 2.3 tests):

1. `_get_cache`: configured-guild path returns the cache instance; unconfigured-guild path returns None/fallback per current code (assert identity/type + that no DB access occurs on the unconfigured sibling via mock `assert_not_called`).
2. `check_bot_manager_permission`: manager-role-hit → allow-True when the user holds a bot-manager role in the guild; fallback-to-MANAGE_GUILD path where config is missing/empty vs present — fixtures covering BOTH branches of the `if not guild_config or …` line so its boolean-restructure rows are killed with distinct observable outcomes; unconfigured-guild deny path asserts denial without exception leakage.

Expected conversion: both families' notests rows reclassified (research L24 row: 20 notests concentrated here plus tokens). Residual logic survivors count against the roles file target at restamp v4.

- **Files**:
  - `tests/unit/services/api/auth/test_roles.py` - modify/add
  - `services/api/auth/roles.py` - read-only reference
- **Success**:
  - scoped run green on touched test file
  - commit through full pre-commit chain rc=0, zero KILL REGRESSION events
- **Research References**:
  - #file:../../research/20260905-01-phase1-security-paydown-research.md (Lines 24 File Analysis roles row), (Lines 88 N-class row), (Lines 173 TR#3), (Lines 185 W2 directive), (Lines 199 strategy B′ risk note — bug discovery switches to xfail-TDD flow with sign-off)
- **Dependencies**:
  - Task 2.3 complete (same test module; keeps one-file-per-step commits cleanly separable in git history).

## Phase 4: W3 Bulk Arg/Value Pinning (~294 raw ids / ~235 rows ≈70% of remaining logic debt; research L186, strategy C at L200)

Phase rules (hard): exact-arg mock asserts (`assert_called_once_with`; `ANY` only where a value is genuinely non-essential and say so inline), return-payload field provenance pins, monkeypatched `os.getenv` propagation pins where config values feed payloads or calls. BACK OUT anywhere an assertion would need to pin internal call ORDERING rather than behavior (house standard + keeps restamp clean — record any backed-out site in the changes file as deferred debt). One commit per file×wave step. File order = research's stated sequence for its six listed files plus two CONFIRMED INSERTIONS flagged here because research L186's list omitted them from the spine (judgment calls #1/#2, by row-count principle): `middleware/authorization.py` after tokens (largest single family, 39 logic rows) and `bot/auth/role_checker.py` before the error_handler tail (28 rows > tail counts). Inventory between waves may be re-derived via the Complete Examples method (research L92-138) if drift makes per-family targets unclear.

### Task 4.1: permissions A1 bulk pinning (`test_api_permissions.py`)

Per-family exact-arg pins across the remaining permissions families (verify_guild_membership ~16-row family head, get_guild_name, verify_game_access, _require_permission token-fetch/guild-resolve arg nullings per research L17 row; redis operation arg/kwarg provenance incl. key-string literals where behavior-relevant, e.g., cache-key shapes). Payload-provenance assertions on returned dicts/tuples so value-drop mutations at return sites fail. Back-out rule enforced. Residual target after phase: ≤15 logic rows (success table research L209).

- **Files**:
  - `tests/unit/services/api/dependencies/test_api_permissions.py` - modify/add
- **Success**:
  - scoped run green; commit through full pre-commit chain rc=0, zero KILL REGRESSION events; hook re-judges whole permissions module (~2–4 min expected — see Gate/Scope Mechanics)
- **Research References**:
  - #file:../../research/20260905-01-phase1-security-paydown-research.md (Lines 17 File Analysis permissions inventory), (Lines 78 Implementation Patterns A1 cluster mechanics), (Lines 186 W3 order + back-out rule), (Lines 200 strategy C effort/risk note), (Lines 209 per-file residual cap)
- **Dependencies**:
  - Phases 1–3 complete.

### Task 4.2: tokens A1 bulk pinning (`test_tokens.py`)

Payload value-drop kills for the get_user_tokens (~28-row family head), refresh_user_tokens, store_user_tokens families: exact Redis call args (key strings, field/value provenance), returned-dict field assertions so dropped keys/values fail, monkeypatched `os.getenv` propagation where env-derived values enter payloads (kills S-env-name literals opportunistically — note in changes file which ones). Residual target ≤12 logic rows (research L209).

- **Files**:
  - `tests/unit/services/api/auth/test_tokens.py` - modify/add
- **Success**:
  - scoped run green; commit through full pre-commit chain rc=0, zero KILL REGRESSION events
- **Research References**:
  - #file:../../research/20260905-01-phase1-security-paydown-research.md (Lines 18 File Analysis tokens inventory), (Lines 78 A1 cluster), (Lines 186 W3), (Lines 200 strategy C), (Lines 209 cap)
- **Dependencies**:
  - Tasks 4.1 complete (sequential wave discipline; same phase may interleave only if a commit is mid-flight — one active commit at a time per repo policy).

### Task 4.3: middleware/authorization dispatch residual pinning (`test_authorization.py`)

CONFIRMED INSERTION #1 (not named in research L186's sequence; placed after tokens by row count — largest single family, 39 logic rows): remaining dispatch debt beyond Phase 2's branch flips — header-value nulling / call-next arg edits pinned via concrete request fixtures asserting stamped headers end-to-end; duration arithmetic sign-flips ×2 pinned BEHAVIORALLY with a monkeypatched clock (e.g., t_start=1.0, t_end=2.0 → captured logged duration argument == 1.0 while the `+` mutant would yield 3.0; message wording still `ANY`, only the computed value pinned); `user_id or "anonymous" → and` restructure killed by the None-fixture asserting the fallback string AND a set-id sibling asserting the real id propagates. Residual target ≤6 logic rows (research L209).

- **Files**:
  - `tests/unit/services/api/middleware/test_authorization.py` - modify/add
- **Success**:
  - scoped run green; commit through full pre-commit chain rc=0, zero KILL REGRESSION events
- **Research References**:
  - #file:../../research/20260905-01-phase1-security-paydown-research.md (Lines 19 File Analysis authorization inventory), (Lines 78 A1 cluster + A5 arithmetic row in Implementation Patterns range L72-91), (Lines 186 W3 insertion rationale as flagged here), (Lines 200 strategy C), (Lines 209 cap)
- **Dependencies**:
  - Task 2.4 complete (branch flips already anchored; this task adds arg/value pins without disturbing them).

### Task 4.4: bot/auth/cache pinning (`test_cache.py`)

RoleCache.get_user_roles family (~16 rows per research L23 row) plus RedisClient None-guard nullings across the cache methods: exact cache-key strings and ttl values asserted on mock calls (behavior-relevant — wrong key IS observable data-corruption potential), return-shape provenance for populated/empty-cache siblings. Residual target ≤5 logic rows (research L209).

- **Files**:
  - `tests/unit/services/bot/auth/test_cache.py` - modify/add (extend existing db-mock style fixtures per research L204)
- **Success**:
  - scoped run green; commit through full pre-commit chain rc=0, zero KILL REGRESSION events
- **Research References**:
  - #file:../../research/20260905-01-phase1-security-paydown-research.md (Lines 23 File Analysis cache row), (Lines 78 A1 cluster), (Lines 186 W3), (Lines 200 strategy C), (Lines 204 fixture scaffolding note), (Lines 209 cap)
- **Dependencies**:
  - Tasks 4.1–4.3 complete in sequence.

### Task 4.5: auth/oauth2 pinning (`test_oauth2.py`)

All six oauth2 families (research L20 row): `validate_state` raise-site pins — thinnest mapping evidence in T1 (2 mapped tests vs 11 logic rows) so start from the re-derived family list at implementation time; assert exception type + message/site args for missing/expired/malformed-state siblings. `generate_authorization_url`: `secrets.token_urlsafe(32)` not-none AND exact params-dict values (response_type, client_id, redirect_uri, scope ordering) pinned by call-arg capture; parameter-case S-other kills are OPTIONAL (note if skipped). `exchange_code_for_tokens`: Discord-API call arg nulling pin @ ~L123 with full expected-args assertion. `is_app_maintainer` default-nullings m6/m8 @ ~L186 (verified to FAIL CLOSED under mutation per research L118 example — kills are pure test additions reaching those lines via non-owner app_info fixtures asserting denial, no behavior change) plus team-member iteration arg drops m22/m24/m31/m33 @ ~L191 via populated owner/team fixtures. Residual target ≤6 logic rows (research L209).

- **Files**:
  - `tests/unit/services/api/auth/test_oauth2.py` - modify/add
- **Success**:
  - scoped run green; commit through full pre-commit chain rc=0, zero KILL REGRESSION events
- **Research References**:
  - #file:../../research/20260905-01-phase1-security-paydown-research.md (Lines 20 File Analysis oauth2 row), (Lines 118-120 verified is_app_maintainer disproof diff), (Lines 78 A1 cluster), (Lines 186 W3), (Lines 200 strategy C), (Lines 209 cap)
- **Dependencies**:
  - Tasks 4.1–4.4 complete in sequence.

### Task 4.6: api/config pinning (`test_api_config.py`)

APIConfig families (research L22 row): `__init__` monkeypatched `os.getenv` propagation for EVERY env var read (pin the exact value reaching each dependent attribute — kills env-name S-literals opportunistically, record which); hidden cookie-domain arg edits past the ledger clip derived via full-diff re-derivation at implementation time and pinned as call args. `_validate` missing-var-list behavior siblings. `get_rate_limits`: five `range(1, n+1)` off-by-one variants killed by an n=1 boundary fixture asserting exact iteration count + int-getenv f-string default pins with exact getenv values. `_get_cookie_domain`: strict-zip behavioral-risk pins m20 (strict=False→None) / m21 (strict=True; verified example research L135 — under mutation unequal host-part counts would raise ValueError, i.e., current semantics tolerate them) constructed with unequal-part-count hosts asserting the CURRENT no-raise tolerance explicitly. TR#5 caveat applies: if testing reveals strict-zip semantics surprising enough to warrant a production change, STOP into the Exception Path (sign-off-gated xfail-TDD enhancement), do not harden silently. Residual target ≤5 logic rows (research L209).

- **Files**:
  - `tests/unit/services/api/test_api_config.py` (or existing config test module path — verify at implementation time; extend rather than fork) - modify/add
- **Success**:
  - scoped run green; commit through full pre-commit chain rc=0, zero KILL REGRESSION events
- **Research References**:
  - #file:../../research/20260905-01-phase1-security-paydown-research.md (Lines 22 File Analysis config row incl. rate-limit off-by-one ×5 + cookie-domain hidden edits), (Lines 135-137 verified strict-zip diff), (Lines 82 Implementation Patterns A5 arithmetic row within L72-91 range), (Lines 175 TR#5 sign-off caveat), (Lines 186 W3), (Lines 200 strategy C), (Lines 209 cap)
- **Dependencies**:
  - Tasks 4.1–4.5 complete in sequence.

### Task 4.7: bot/auth/role_checker pinning (`test_role_checker.py`)

CONFIRMED INSERTION #2 (omitted from research L186's six-file spine; inserted before the tail by row count, 28 logic rows): `get_guild_roles` family (~8 rows per research L21 row) — DB query arg nulling pinned with exact execute-args assertions; fail-closed guard return-flips m6/m7 where the flip direction is deny-side (survivors still killable: fixtures for error/no-row cases must assert empty/deny outcomes, NOT exception leakage or truthy fallbacks). Logger cluster debt here defers to Phase 5. Residual target ≤5 logic rows (research L209).

- **Files**:
  - `tests/unit/services/bot/auth/test_role_checker.py` - modify/add (extend existing db-mock style per research L204)
- **Success**:
  - scoped run green; commit through full pre-commit chain rc=0, zero KILL REGRESSION events
- **Research References**:
  - #file:../../research/20260905-01-phase1-security-paydown-research.md (Lines 21 File Analysis role_checker row incl. logger-cluster note), (Lines 81 Implementation Patterns A4 guard/negation row within L72-91 range), (Lines 186 W3 insertion as flagged here), (Lines 200 strategy C), (Lines 204 fixture scaffolding note), (Lines 209 cap)
- **Dependencies**:
  - Tasks 4.1–4.6 complete in sequence.

### Task 4.8: middleware/error_handler logic tail (`test_error_handler.py`)

Seven logic rows = status/detail kwarg edits across the exception-handler families (research L26 row): response-status + detail pins per handler family via raised-exception siblings with distinct payloads. This file's string-class message literals (32 rows) defer to Phase 5 acceptance bookkeeping — do not chase them here. Residual target ≤2 logic rows (research L209).

- **Files**:
  - `tests/unit/services/api/middleware/test_error_handler.py` - modify/add
- **Success**:
  - scoped run green; commit through full pre-commit chain rc=0, zero KILL REGRESSION events
- **Research References**:
  - #file:../../research/20260905-01-phase1-security-paydown-research.md (Lines 26 File Analysis error_handler row), (Lines 79 Implementation Patterns A2 raise-site row within L72-91 range), (Lines 186 W3 "error_handler/deps tail"), (Lines 200 strategy C), (Lines 209 cap)
- **Dependencies**:
  - Tasks 4.1–4.7 complete in sequence.

### Task 4.9: TAIL FOLD COMMIT (deps/auth residual + discord_tokens exact-value kills [+ optional cors])

Single commit permitted by the research L190 fold rule naming exactly these files — bundle into ONE commit only the small-file work below (no other files):

1. `services/api/dependencies/auth.py` residual A1 beyond Task 2.1's pins: token-fetch arg nullings inside get_current_user and the scalar_one_or_none return-path edit family (mock-result fixtures asserting returned-user provenance).
2. `shared/utils/discord_tokens.py`: exact-value kills on the base64 pad-math (`%4→%5` survivors per research L27 row) via input lengths exercising remainders 0..3, each asserting the EXACT padded output string; its `decode("utf-8")→"UTF-8"` equivalence is string-class → goes to the Phase 5 acceptance list, NOT killed here. Residual target ≤1 logic row (research L209).
3. OPTIONAL: `services/api/middleware/cors.py` origin-list exact assert killing its two S-other case-edit ids (research L28 row). Skip if effort-bound and record the skip in the changes file (string-class; never blocks commits).

Back-out rule applies throughout; any site pinned only by call-ordering dependence is deferred to the changes file.

- **Files**:
  - `tests/unit/services/api/dependencies/test_auth_dependency.py` - modify/add (residual pins)
  - `tests/unit/shared/utils/test_discord_tokens.py` (verify existing path at implementation time; extend rather than fork) - modify/add
  - optionally `tests/unit/services/api/middleware/test_cors.py` - modify/add
- **Success**:
  - scoped run green across touched test files; single commit through full pre-commit chain rc=0, zero KILL REGRESSION events; fold noted in changes file per research L190
- **Research References**:
  - #file:../../research/20260905-01-phase1-security-paydown-research.md (Lines 25, 27, 28 File Analysis rows for the three folded files), (Lines 85-87 Implementation Patterns S-class rows within L72-91 range), (Lines 162-163 Configuration Examples tail-file tables within L146-168 range), (Lines 190 fold permission), (Lines 203 acceptance classification of utf-8 equivalence + optional S-other note)
- **Dependencies**:
  - Tasks 4.1–4.8 complete — this is the wave's final commit.

## Phase 5: W4 Logger/Message Resolution + Acceptance Bookkeeping (~84 logic rows / ~105 raw ids; research L187, strategy D at L201)

Phase note: structural log asserts with SANCTIONED `ANY` wording (one behavior per test; pinned structured args only — caplog or mock-logger call-capture). Scope discipline: this phase kills LOGIC-class logger-arg mutants; message-WORding literals are string-class and belong to Task 5.2's acceptance list. Negative assertions still require triggering sibling paths (unit-tests standard).

### Task 5.1: Structural log asserts across T1 files (per-touched-test-file commits in Phase-4 order)

Derive the residual per-file LOGIC-class logger-arg-mutant id list from a fresh re-derived inventory using the Complete Examples method (research L92-138) taken just before starting — do not work from stale memory of which sites remain after Phases 2–4. Pattern: `assert_called_once_with(ANY, <pinned non-wording structured args>)` for argument-bearing logger calls, record-count + pinned-fields assertions where multiple emits are possible, one test per observable behavior. Expected distribution anchors from research patterns section (L72-91): authorization dispatch logger cluster, role_checker file-wide ~20-id logger cluster, remaining tokens/permissions/oauth2 logic-class arg manglings at raise/log sites. Commit per touched test file following Phase 4 order so git history stays bisectable by file×step. Optional cheap S-other kills (oauth param-case pins, "details" key casing) may ride along ONLY where they fall out naturally while writing a task's tests; explicitly not required (research L187).

- **Files**:
  - whichever subset of the Phase-4 test modules still carries logic-class logger debt (determined by the pre-task re-derivation; expected: test_authorization.py, test_role_checker.py first by row count)
- **Success**:
  - scoped runs green per touched module; each commit through full pre-commit chain rc=0 with zero KILL REGRESSION events
  - pre-task id list and post-wave residual recorded in changes file (measurement evidence for restamp v4 note)
- **Research References**:
  - #file:../../research/20260905-01-phase1-security-paydown-research.md (Lines 80 Implementation Patterns A3 logger-cluster row within L72-91 range), (Lines 92-138 re-derivation method), (Lines 187 W4 directive + optional-S-other note), (Lines 201 strategy D effort/risk), (Lines 203 rationale that structural asserts kill every logic-class arg mangling at those sites)
- **Dependencies**:
  - Phases 1–4 complete (residual list is only meaningful after bulk pinning lands).

### Task 5.2: Acceptance bookkeeping (documentation task — no code change)

Classify ALL residual string-class debt into the explicit acceptance list with a justification class per group (final counts fixed ONLY at restamp v4; this task produces the draft table):

| Group                                                                              | Raw-id estimate                              | Justification class (cite research line)                                                                                                                                                      |
| ---------------------------------------------------------------------------------- | -------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Header-name case variants                                                          | 8                                            | Starlette `CaseInsensitiveDict` makes lookups byte-case-insensitive — asserting exact-case storage tests framework internals, not our contract (L86/L203 within patterns/acceptance sections) |
| Codec normalization (`decode("utf-8")→"UTF-8"`)                                    | 1                                            | codec alias equivalence — behavior identical under CPython (L87/L203)                                                                                                                         |
| Log-message wording literals                                                       | ~155 minus any slice pinned by W1/W3/W4 work | house standard sanctions `ANY` for wording; Phase 5.1 structural asserts already kill every LOGIC-class arg mangling at those sites so nothing gating goes untested (L84/L203)                |
| Residual error/detail wording where type+status already pinned by W1/W3 raise-pins | small double-digit                           | observable contract (exception type/status/detail-pin structure) already enforced; pure surface text remains (L203)                                                                           |

EXPLICITLY NOT acceptable into the list: S-other behavioral literals (~95 raw ids per L85/L203) remain KILLABLE debt ranked below all logic work and stay tracked as ordinary string rows after restamp v4; ANY logic-class survivor is ineligible for acceptance — logic acceptances = 0 (L203). Deliverable: draft acceptance table written into the changes tracking file (created at execution Step 1) with one line per group + justification, flagged "counts fixed at restamp v4". Commit only when the user says commit (markdown-only diff passes the chain trivially but still runs it in full).

- **Files**:
  - `.copilot-tracking/planning/changes/20260905-01-phase1-security-paydown-changes.md` - modify (append acceptance-draft section)
- **Success**:
  - acceptance draft complete with per-group justifications and the two explicit exclusions stated verbatim-equivalent
  - no source/test code touched; any commit of this doc through full pre-commit chain rc=0
- **Research References**:
  - #file:../../research/20260905-01-phase1-security-paydown-research.md (Lines 84-87 S-class taxonomy within Implementation Patterns), (Lines 187 W4 classification directive), (Lines 203 documented-acceptance groups + explicit non-acceptable list), (Lines 214 success-table row for bookkeeping)
- **Dependencies**:
  - Task 5.1 complete (the wording-literal count depends on which slice got pinned along the way).

## Phase 6: W5 Phase-End Hygiene & Restamp

### Task 6.1: Pre-restamp verification sweep (no store mutation; likely no commit)

Run in order, record outputs in the changes file: (1) full suite `uv run pytest tests/unit -q` — ≥ baseline floor (baseline verified at planning time: 2585 passed @ HEAD; scoped T1 subset 248 passed — both floors may only GROW during this phase, zero removals and zero xfail markers ever added anywhere); (2) mypy clean via `uv run mypy shared/ services/`; (3) visual STALE-row review of the gate reports accumulated across the phase — informational UNLESS a stale line masks a KILL REGRESSION inside changed scope (if it does, STOP and treat as regression investigation before restamp); (4) OPTIONAL dry-run re-derivation via the Complete Examples method to preview the v4 census delta BEFORE triggering the pipeline (read-only; confirms per-file residuals against L209 targets so surprises land here instead of after the ~15–20 min cold pass). This task itself produces no commit unless evidence files warrant one (decide with user when reached).

- **Files**:
  - none modified (verification + evidence recording into the changes file)
- **Success**:
  - all four recorded results green/informational-clean; any anomaly escalated to the user BEFORE Task 6.2 is requested
- **Research References**:
  - #file:../../research/20260905-01-phase1-security-paydown-research.md (Lines 41-44 test-suite baselines within Code Search Results), (Lines 70 STALE semantics in Project Structure findings), (Lines 92-138 re-derivation method for the optional dry run), (Lines 188 W5 directive)
- **Dependencies**:
  - Phases 1–5 complete.

### Task 6.2: Serial-pipeline restamp → census v4 (user-approved gate — implementer does NOT trigger)

The restamp executes ONLY via the serial-pipeline make target `make restamp-mutmut-baseline` and ONLY under explicit user sign-off AFTER all phases are complete and this plan's success table has been presented. Implementer prepares state, announces readiness, and waits. After pipeline completion verify outputs against the success-criteria table (research L205-214): ledger stamps updated with plain-SHA source commit (clean tree); archive `.copilot-tracking/testing/mutation-census/YYYYMMDD-restamp-v4-on-develop.json` exists per naming convention; one-line pre/post logic-row note recorded against targets (per-file residuals ≤ L209 caps summing ≤ ~50 from baseline 352; seven-function notests rows = 0 unresolved with any survivors counted as gated logic debt vs file targets; zero KILL REGRESSION events unresolved at restamp); acceptance list in the changes file matches ONLY the sanctioned groups at ≤ ~165 raw string-class ids total with logic acceptances = 0. Update the changes file with final numbers; commit ledger + census artifacts through the full pre-commit chain when the user says commit. Any target miss: STOP, report delta to user, do NOT re-run the pipeline without a new decision (store hygiene rule: no interleaved or repeat cold passes on one store).

- **Files**:
  - `mutmut-baseline.json` - rewritten BY THE PIPELINE (never by hand) — commit artifact
  - `.copilot-tracking/testing/mutation-census/YYYYMMDD-restamp-v4-on-develop.json` - pipeline output — commit artifact
  - `.copilot-tracking/planning/changes/20260905-01-phase1-security-paydown-changes.md` - modify (final counts section)
- **Success**:
  - success-table verification recorded line-by-line against research L209-214
  - single restamp commit through full pre-commit chain rc=0 (gate scope at that point: whole changed module set post-push-parity if user has pushed — still narrow by design)
- **Research References**:
  - #file:../../research/20260905-01-phase1-security-paydown-research.md (Lines 45-46 census naming convention within Code Search Results), (Lines 70 STALE/regression semantics), (Lines 188 W5 directive), (Lines 196 objectives incl. acceptance-count bounds), (Lines 204 serial-pipeline-only dependency + user approval gate), (Lines 205-214 success-criteria table carried verbatim-equivalent into the plan file)
- **Dependencies**:
  - Task 6.1 clean sweep; explicit user approval of both plan completion and the restamp trigger.

## Dependencies

- Read-only store inputs owned by the serial pipeline: `mutants/**/*.meta`, expanded mutant modules, `mutants/mutmut-stats.json` (test-mapping approximations pre-date HEAD — cross-validate counts via re-derivation per research API-and-Schema notes L143-144). Never written during this phase except by the Task 6.2 pipeline run under user sign-off.
- Project scripts loaded unmodified under `uv run python` for between-wave target re-derivation: `scripts/mutmut_ledger.py`, `scripts/mutmut-logic-survivors.py` (method at research Complete Examples L92-138).
- Existing fixture scaffolding as extension bases (extend, never fork/duplicate): `tests/unit/services/bot/auth/test_role_checker.py` db-mock style; `tests/unit/services/api/dependencies/test_api_permissions.py`; existing tokens/oauth2/config test modules where present.
- Binding instruction files: #file:../../../.github/instructions/test-driven-development.instructions.md (retrofitting row + bug-fix exception), #file:../../../.github/instructions/unit-tests.instructions.md (falsifiability / ANY sanction / negative-assertion siblings), #file:../../../.github/instructions/commit-messages.instructions.md (≤80-char lines), #file:../../../.github/instructions/quality-check-overrides.instructions.md (bypass policy — none anticipated in this plan; any suppression request stops the task and escalates), plus the house no-manual-testmon rule (research TR#4 L174).
- End-of-phase restamp dependency: serial pipeline execution after user approval of this plan (Task 6.2 gate) — no manual store operations under any circumstance outside that single gated run.

## Success Criteria

Carried verbatim-equivalent from the source research success table (L205-214); measurement means are binding:

| Metric                                                                       | Baseline (verified @ `15e318c9`)                                                                    | Target                                                                                                                                                                                                                                | Measurement                                                                                                                                                      |
| ---------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Logic rows surviving (T1)                                                    | 352 rows / 440 raw ids                                                                              | ≤ ~50 rows total (≥ ~85% row reduction); per-file caps: permissions ≤15 · tokens ≤12 · authorization ≤6 · oauth2 ≤6 · role_checker ≤5 · config ≤5 · cache ≤5 · roles ≤5 · auth-dep ≤2 · error_handler ≤2 · discord_tokens ≤1 · cors 0 | Restamp-v4 verdict census over `mutants/<file>.meta` + regenerated ledger rows via the validated zero-mismatch re-derivation method; interim dry-run at Task 6.1 |
| Notests rows in the seven untested security functions                        | 47 rows / 51 ids                                                                                    | 0 untested rows remain there; any survivors reclassify to gated logic debt counted against file targets                                                                                                                               | Store-verdict census over those 7 function families at restamp v4                                                                                                |
| KILL REGRESSION events (tracked killed ids failing re-kill in changed scope) | gate rc=0 at HEAD                                                                                   | Zero on every phase commit and unresolved-none at restamp                                                                                                                                                                             | Pre-commit ledger-gate output captured per commit; restamp report regression preview                                                                             |
| Unit suite health                                                            | full **2585 passed** (`uv run pytest tests/unit -q`, no --testmon); T1 scoped subset **248 passed** | Full ≥ 2585 with 0 failures / 0 errors at each wave boundary; scoped set only grows (no removals, no xfail markers ever added)                                                                                                        | Same commands at each phase-completion gate                                                                                                                      |
| Gate hygiene                                                                 | —                                                                                                   | Mutation-ledger gate rc=0 on every commit; no `--no-verify`/`SKIP=`; no manual mutmut/testmon execution; `.testmondata` absent or deleted-stale rule honored                                                                          | Git log vs hook outputs per commit; absence of checksum advances                                                                                                 |
| Acceptance bookkeeping                                                       | —                                                                                                   | Restamp-v4 acceptance list contains only the Task 5.2 sanctioned groups, ≤ ~165 raw string-class ids total, each row citing its justification class; logic-class acceptances = 0                                                      | Restamp v4 census note + changes-file draft table reconciliation                                                                                                 |
