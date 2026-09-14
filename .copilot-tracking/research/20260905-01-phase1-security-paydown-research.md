<!-- markdownlint-disable-file -->

# Task Research Notes: Phase 1 Security Paydown (T1 auth/tokens/oauth2/roles/permissions mutation debt)

**Task:** Reduce mutation-testing debt on the security-critical T1 file set by killing surviving mutants — unit-test strengthening first, defensive hardening second, documented acceptance last.
**Date:** 2026-09-05 · **Branch / HEAD:** `develop` @ `15e318c9` (`== origin/develop`), "chore(mutmut): restamp ledger stamps and archive v3 cold-pass census"
**Tooling context (Phase 0, referenced not duplicated):** `.copilot-tracking/research/20260901-01-mutmut-upgrade-validation-research.md` covers mutmut 3.5→3.7 upgrade, the `timeout_constant=4.0` watchdog fix, and the two ledger-gate fixes at `4ac48abd` / `5278de4c`. This document builds on that state: the store is clean (cold-pass census `20260905-restamp-v3-on-develop.json`: killed 9,382 / survived 5,840 / no-tests 981 of 16,203 mutants) and `mutants/**/*.meta` verdicts are treated as read-only inputs throughout.

## Research Executed

### File Analysis

T1 scope = 12 files, 60 function-families carrying surviving or untested debt. Every number below was re-derived in this session from live store data joined to the committed ledger; per-mutant edits were reconstructed with full diffs (method under Complete Examples) so ledger rows hidden past their 48-char clip could be resolved.

- `./mutmut-baseline.json` (**repo root, not** under `mutants/`) — ledger v2 ratchet: top keys `_readme, entries, generated_utc, killed, source_commit, version`; class vocabulary `{logic, string, notests}`. T1 totals verified: **650 rows = logic 352 + string 251 + notests 47** across 60 families (per-file table under Configuration Examples).
- `scripts/mutmut_ledger.py` — constants re-verified by direct read/grep: `CLIP_CHARS=48`, `EDIT_SUMMARY_LIMIT=240` (`[:236] + " …+"`), `BLOCKING_CLASS="logic"`, entry dedup per family on `(class, canonical_summary)` where `canonical_summary()` strips `^L\d+: ` prefixes from `"; "-joined segments`; kill-regression tracked via `ledger['killed'][relpath][family] → [mutant_numbers]`; gate scope = upstream==HEAD so only actually-changed functions are scanned at hook time; STALE is informational-only.
- `scripts/mutmut-logic-survivors.py` — `compute_diff(module, name, path)` (unified diff of mutmut's stored original vs mutant function) and `is_string_only_mutation(diff)` (string-class iff XX-wrap or pure case-change edits only); both loaded and executed in this session for the full cross-check (Complete Examples).
- `services/api/dependencies/permissions.py` (778 L, 15 fams, **85 logic / 53 string rows**) — largest T1 debtor. Verified survivors: `_check_guild_membership` m19 fail-open direction flip @ ≈L84 (`return False→True` on the missing-user-data guard) plus a hidden edit past char-48 inside the stale-bot guard line (`if not await member_projection.is_bot_fresh(redis=redis):`, resolved as an arg-nulling by full diff); `_resolve_guild_id` m2/m3 break the snowflake length bounds at both exact ends; four `if redis is None:` guard negations (`→ is not None:`) across verify/get-guild-name paths overwrite a caller-provided client with the singleton; `_require_permission`: token-fetch/guild-resolve arg nullings survive while the maintainer-bypass check itself (L347 `token_data.get("is_maintainer") → return current_user`) has no surviving mutants (covered ✓); HTTPException status/detail edits at the 503/404/403 sites (m34–m37 area, L123–160). Also found: **unreachable dead `return current_user` @ L409** in `require_manage_guild` after `return await _require_permission(...)` — sole occurrence in file (all three helper call-sites scanned).
- `services/api/auth/tokens.py` (267 L, 10 fams, **69 logic / 58 string / 27 notests rows**) — `get_user_tokens` (28 logic) = return-payload value drops + Redis call-arg nulls; `refresh_user_tokens` (20), `store_user_tokens` (14) same shapes. Five crypto/lifecycle helpers have zero tests (notests): `get_encryption_key` (12 rows incl. key-length boundary `len(key) < ENCRYPTION_KEY_LENGTH → <=` m3 @ L54 and `ljust(…, b"0")` arg nullings), `is_token_expired` (7), `decrypt_token` (4, Fernet construction args L~70), `encrypt_token` (4); `delete_user_tokens` log-text only.
- `services/api/middleware/authorization.py` (1 fam, **39 logic / 21 string rows**) — `xǁAuthorizationMiddlewareǁdispatch` is a single family that is **logging-only** (stamps `X-User-Id`/`X-Request-Id`, logs 401/403 responses; actual authz happens in FastAPI dependencies per its docstring). Survivors: header-value nulling & arg edits, status-code branch flips (m34 @ L80 `==→!=` on HTTP_403, m51 @ L88 on HTTP_401), duration arithmetic sign flips ×2 (`time.time() - start_time → + start_time`), `user_id or "anonymous" → and` (log context only), logger-arg mangling, case variants of the two header-name strings.
- `services/api/auth/oauth2.py` (6 fams, **33 logic / 26 string rows**) — `validate_state`: 11 logic rows vs only 2 mapped unit tests (thinnest coverage/densest debt in T1) incl. `msg = "Invalid or expired state token"` site args and raise-site nullings; `generate_authorization_url`: `secrets.token_urlsafe(32) → None` (state strength drop-out) plus params-dict literal case/XX variants (`"response_type":"code"`, scope join); `exchange_code_for_tokens`: Discord-API call arg nullings L123; `is_app_maintainer`: survivors are default-nullings `.get("owner", {})→(…, None|∅)` (m6/m8 @ L186) and team-member iteration arg drops (m22/m24/m31/m33 @ L191) — **not** operator flips (Key Discoveries).
- `services/bot/auth/role_checker.py` (224 L, 6 fams, **28 logic / 14 string rows**) — `RoleChecker.get_guild_roles` 8 logic (DB query arg nulling + fail-closed guard return-flips m6/m7 where the flip direction is the _denying_ one, still killable), logger-arg mangling cluster (20 raw ids file-wide).
- `services/api/config.py` (4 fams, **27 logic / 19 string rows**) — `APIConfig.__init__` (~15 logic): getenv-default drops/swaps incl. hidden-edit rows past the 48-char clip (resolved by full diff: e.g., cookie-domain args, DB URL parts); `_validate` missing-variable list literals are string-class only; `get_rate_limits` (10 logic): five `range(1, n+1)` off-by-one variants + int(getenv f-string defaults); `_get_cookie_domain`: reversed-zip suffix loop survivors m20 (`strict=False → None`) and m21 (`strict=True`, would raise ValueError on unequal host-part counts — behavioral risk pin needed) plus a break/continue control edit.
- `services/bot/auth/cache.py` (3 fams, **27 logic / 18 string rows**) — RedisClient `| None` guard arg nullings ×3 methods around `RoleCache.get_user_roles` (16 logic) + cache key/ttl arg edits.
- `services/api/auth/roles.py` (298 L, 8 fams, **23 logic / 3 string / 20 notests rows**) — core permission evaluation: `user_permissions = 0 → 1` init const (m37 @ L170) and `.get(role_id, 0) → .get(role_id, 1)` (m44 @ L172) silently grant +1 bits for unknown roles (implicit-bit test gaps); owner-check `"owner_id"` key literal survives as string class; fail-open flips in `check_game_host_permission` (m9 @ L234 guard negation + paired m10 @ L235 `return False→True`) and `has_permissions` (m58, L163/L181 area). Notests debt concentrated in exactly two functions: `check_bot_manager_permission` (18 rows incl. boolean restructures on the `if not guild_config or …` line and a where-clause flip candidate) and `_get_cache` (2).
- `services/api/dependencies/auth.py` (1 fam, **11 logic / 4 string rows**) — four `HTTPException(401)` detail-nulls at L65/69/72/82, token-fetch arg nulling, and confirmed where-clause equality flip m36 (`User.discord_id == discord_id → !=`, L~77 select statement), plus `scalar_one_or_none` return-path edits.
- `services/api/middleware/error_handler.py` (148 L, 4 fams, **7 logic / 32 string rows**) — overwhelmingly string-heavy: exception-detail message literals, log text, `"details"` response-body key case variants (×2); logic survivors limited to status/detail kwarg edits.
- `shared/utils/discord_tokens.py` (1 fam, **3 logic / 1 string row**) — `% 4 → % 5` base64 pad math with `(4-pad)→(4±pad)/(5-pad)` sign variants; one true equivalence mutant `decode("utf-8")→"UTF-8"` (string class, codecs normalize).
- `services/api/middleware/cors.py` (1 fam, **2 string rows only**) — both survivors are origin-string case edits around `"http://127.0.0.1:8000",` (m11 XX-wrap @ store line 18 region of the expanded module; verified via project pipeline).

### Code Search Results

- Glob over `tests/unit/**/test_*.py` for T1 modules
  - All 12 T1 sources have a test file: `services/api/auth/{test_oauth2,test_roles,test_tokens}.py`, `dependencies/{test_api_permissions,test_auth_dependency,test_permissions_migration}.py`, `middleware/{test_authorization,test_cors,test_error_handler}.py`, `test_api_config.py`, `test_negative_authorization.py`; `services/bot/auth/{test_role_checker,test_cache,test_bot_permissions}.py`; `shared/utils/test_discord_tokens.py`. No T1 source lacks coverage scaffolding — debt is assertion depth plus two untested function families inside tested files.
- `grep` for unreachable trailing returns after `_require_permission(...)` in `permissions.py`
  - One match: L409 dead `return current_user` in `require_manage_guild` (the other two call sites at L444/L537 have no trailing return).
- `grep` on the reconstructed per-mutant inventory for direction-flip edit text (`'return False'->'return True'`)
  - Three surviving flips, all fail-open direction, none reversed: permissions `_check_guild_membership` m19; roles `check_game_host_permission` m9+m10 (guard pair); roles `has_permissions` m58. Exact edits + hunk offsets verified by full-diff run (Complete Examples).
- Test-mapping sample from `mutants/mutmut-stats.json → tests_by_mangled_function_name` (**approximate**: stats `git_commit=5278de4c` predates HEAD and one sampled mapping cross-includes unrelated suites)
  - `x__require_permission` → 16 mapped tests · `oauth2.x_validate_state` → **only 2** · `AuthorizationMiddleware.dispatch` → **only 6** vs its 39 logic rows · `role_checker.check_game_host_permission` → 4. Directionally corroborated by survival density: thinnest-mapped families carry densest survivors.
- Scoped pytest of exactly the T1 test paths (`uv run pytest <paths> -q --no-header -p no:cacheprovider`, **no `--testmon`**)
  - **248 passed, 0 failed, 0.54s** — Phase-1 scoped baseline.
- Full unit suite `uv run pytest tests/unit -q --no-header -p no:cacheprovider`
  - **2585 passed in 14.59s** at HEAD (task-brief baseline said 2584; use verified 2585 as the Phase-1 floor).
- Census archive listing `.copilot-tracking/testing/mutation-census/`
  - Existing convention: `20260904-restamp-on-develop.json`, `20260905-restamp-v3-on-develop.json` → Phase-1 restamp belongs at `YYYYMMDD-restamp-v4-on-develop.json`.

### External Research

No new external fetches were required for this phase's analysis; tooling-behavior sources already captured in the Phase 0 doc are re-relied-upon and cited here so provenance stays inside one research trail:

- #githubRepo:"[mutmut](https://github.com/boxed/mutmut/issues/518) mutmut 3.x timeout watchdog"
  - Store verdict codes per `STATUS_TO_CLASS`: `-24`/`36` = timed out, `37` = typecheck-failed; `timeout_constant=4.0` context established in Phase 0 (`20260901-01-mutmut-upgrade-validation-research.md`). No new upstream behavior was needed for T1 paydown planning — all T1 analysis uses local store + project scripts only.
- #fetch:[mutmut on PyPI](https://pypi.org/project/mutmut/)
  - Pinned version **3.7.0** as validated by the Phase 0 upgrade work; unchanged input to this phase.
- (All other "external" facts used below are verified directly from this repo's `mutants/**` data and its own scripts rather than upstream docs.)

### Project Conventions

- Standards referenced: unit-test quality bar (`.github/instructions/unit-tests.instructions.md`) — assertions-first, falsifiability test ("if I swap two arguments, delete a return value, or invert a condition, will this test catch it?"), `assert_called_once_with(...)` over bare call-count asserts, `pytest.raises` on error paths, **`ANY` sanctioned specifically for log-message strings** (structure asserted, wording ignored), negative assertions require a triggering sibling path. Test execution rule (CLAUDE.md index §Testmon / `.github/copilot-instructions.md`): never run `pytest --testmon` manually; stale `.testmondata` is deleted, not advanced. Quality-check override policy (`.github/instructions/quality-check-overrides.instructions.md`): any pre-commit bypass (`--no-verify`, `SKIP=`) needs explicit user approval — the mutation-ledger gate failure during Phase 1 must never be suppressed.
- Instructions followed: TDD applicability determined per file type per `.github/instructions/test-driven-development.instructions.md` — see Technical Requirements for the binding statement. Researcher protocol per `.copilot-tracking/research/AGENTS.md` + `.github/instructions/researcher-enhancements.instructions.md`: one recommended approach only (alternatives evaluated then removed from this doc's body), prior research referenced not duplicated, verified numbers with sources, `#githubRepo:`/`#fetch:` callouts preserved exactly.

## Key Discoveries

### Project Structure

- **Ledger rows ≠ mutant count.** The committed ledger holds 650 T1 rows (352 logic / 251 string / 47 notests). Raw store verdicts over the same 12 files show **997 killed ids + 760 non-killed ids**, where the 760 split into **440 logic-class survivor ids / 269 string-class / 51 no-test**. Rows dedup per family on `(class, canonical_summary)` after clipping both edit sides to 48 chars (`…`), so identical-looking edits at different sites collapse to one row. Kill targets ≈ raw-id count; ratchet sensitivity tracks row count. Both units are used in success criteria below.
- **Family key format measured, corrected:** `<dotted.module.path>.<mangled>` with mangle = `x<func>` for module functions and `x\u01C1<Class>\u01C1<method>` for methods — separator is codepoint **U+01C1** (hex-verified from store keys; the task brief's U+01C0 was wrong). Store keys append `__mutmut_N`.
- **Committed ledger reproduces exactly from live store data: zero mismatches.** Re-running the project's own pipeline (`compute_diff` + `is_string_only_mutation` + `summarize_edit`/`canonical_summary`, executed under `uv run python`) over all 60 T1 families yielded per-family `(class, summary)` sets that were set-equal to `mutmut-baseline.json` entries in **60/60 families** with zero residual deltas. The baseline is trustworthy as-of `15e318c9`; later drift ⇒ source or store changed, not classifier divergence. This also validated the reconstruction method behind every edit cited here.
- **Gate semantics at HEAD:** scope = upstream==HEAD so only actually-changed functions are scanned (fast hooks); BLOCKING_CLASS="logic" means logic-class _new_ survivors in merge-base scope block commits, while string/notests new rows warn-only; STALE rows are informational; kill-regression fires when a tracked killed id fails re-kill in changed scope (with a bounded lost-id preview).

### Implementation Patterns

Measured edit-shape taxonomy of the debt (full-diff reconstructed counts, raw ids; row estimates = ids × 352/440 dedup factor — planning estimates, exact per-cluster row derivable from ledger at implementation time):

| cluster                                                        | logic rows≈ |                                                          raw ids | verified shape examples                                                                                                                                                                                                                                                                                       | verdict                                                                                                   |
| -------------------------------------------------------------- | ----------: | ---------------------------------------------------------------: | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------- |
| A1 arg/RHS nulling & removed args into external calls          |        ≈235 |                                                              294 | `get_user_tokens(session_token→None)` deps/auth L77-area · `cache.get_json(key→None)` roles L153 · `exchange_code(code,None)` oauth2 L123 · `"user_id": str(…get(None))` tokens payload                                                                                                                       | TEST GAP                                                                                                  |
| A2 HTTPException status/detail edits                           |         ≈13 |                                                               16 | `status_code=…503 → None`, `detail="Service unavailable" → ∅` permissions L123–160 · four 401-detail nulls deps/auth L65/69/72/82 · dispatch m34/m51 branch flips                                                                                                                                             | TEST GAP                                                                                                  |
| A3 logger argument mangling                                    |         ≈84 |                                                              105 | `logger.info(msg→None)`, dropped/reordered `%s` args across all T1 files                                                                                                                                                                                                                                      | TEST GAP (killable via house-style `ANY`-wording structural asserts; wording itself is string-class debt) |
| A4 comparison/boundary/negation flips                          |          ≈6 |                                                               7+ | snowflake bound breaks ×2 (`_resolve_guild_id` m2/m3) · redis-guard negations ×4 (`if redis is None:→is not None:`) · where-clause flip (deps/auth m36) · and/or restructure in `check_bot_manager_permission`                                                                                                | TEST GAP, security-critical                                                                               |
| A5 arithmetic/off-by-one/constants                             |         ≈12 |                                                               15 | `range(1,n+1)` family ×5 config rate-limits · base64 pad math %4/%5 + sign variants discord_tokens · `token_urlsafe(None)` oauth2 L60 · `timedelta(minutes=5)→6/None` · `user_permissions = 0→1` & `.get(role_id,0)→1` roles L170/L172 · duration `-→+` authorization ×2 · zip `strict=False→True` config m21 | TEST GAP                                                                                                  |
| A6 return-direction flips                                      |          ≈2 |                                                                3 | all three surviving ones fail open — see Technical Requirements item 1 for the exact verified ids/lines                                                                                                                                                                                                       | **highest severity**                                                                                      |
| S-msg literals (log text + raise/msg=/detail= wording context) |           — | ~155 raw string ids (73 one-line logger + 82 multi-line-context) | `logger.warning("No calendar export token…") → XX/lower/UPPER` tokens L265 etc.                                                                                                                                                                                                                               | ACCEPT candidates                                                                                         |
| S-other behavioral literals                                    |           — |                                                               95 | OAuth URL param names/values (`"response_type":"code"`), payload keys (`"access_token"`), env identifiers via `os.getenv`, response key `"details"`, cors origins                                                                                                                                             | optional / low priority (killable by exact-value asserts)                                                 |
| S-header case variants                                         |           — |                                                                8 | `X-User-Id` / `X-Request-Id` lower/upper/XX — identical under Starlette `CaseInsensitiveDict`                                                                                                                                                                                                                 | **true equivalence mutants — accept**                                                                     |
| S-encoding equivalence                                         |           — |                                                                1 | `decode("utf-8")→"UTF-8"`                                                                                                                                                                                                                                                                                     | **true equivalence mutant — accept**                                                                      |
| N no-test debt                                                 |           — |                                                 51 ids / 47 rows | entire functions absent from unit suite: tokens `{get_encryption_key,is_token_expired,decrypt_token,encrypt_token}` + roles `{_get_cache,check_bot_manager_permission}`                                                                                                                                       | TEST GAP; adding tests converts class to ratchet-gated logic                                              |

No logic-class survivor was found to be an unkillable true-equivalence mutant (all equivalence cases landed in string class). The suspected "hidden fail-open maintainer-check flip" in oauth2 `is_app_maintainer` L~191 (masked by the 48-char clip in the committed ledger rows) resolved to harmless default-nullings that raise under mutation — i.e., they fail _closed_ — and likewise the deps/auth where-clause flip fails closed (wrong users selected → empty lookup → 401 path). **Full-diff re-examination of every security-suspicious row found zero confirmed production-code weaknesses requiring behavior changes: T1 debt is overwhelmingly test gaps over correct code.** This de-risks Phase 1 materially (see Technical Requirements item 5 for the one caveat).

### Complete Examples

Reconstruction method used for all per-mutant evidence above (verified working; re-derivable in minutes at implementation time):

```python
# run via: uv run python   (loads project scripts unmodified; reads store data only)
import importlib.util, json, libcst as cst
def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m
cls_mod = load("ls", "scripts/mutmut-logic-survivors.py")   # compute_diff / is_string_only_mutation
led_mod = load("ml", "scripts/mutmut_ledger.py")            # summarize_edit / canonical_summary

f = "services/api/dependencies/permissions.py"
meta = json.load(open(f"mutants/{f}.meta"))["exit_code_by_key"]      # 0 survived | 1|3 killed | 5|33 no-tests
module = cst.parse_module(open(f"mutants/{f}").read())               # expanded trampoline module
for key, code in meta.items():
    if code in (1, 3):
        continue                                                       # skip killed ids
    diff = cls_mod.compute_diff(module, key, f)                       # full unified diff, UNCLIPPED
    string_only = cls_mod.is_string_only_mutation(diff)               # XX-wrap or case-only edits
```

Representative verified mutant diffs (exact stored edits; `−` original → `+` mutated):

```diff
# oauth2.py x_is_app_maintainer m6 @ L186  — suspected hidden ==→!= flip DISPROVEN: default-nulling instead
-    owner_id = app_info.get("owner", {}).get("id")
+    owner_id = app_info.get("owner", None).get("id")       # AttributeError under mutation ⇒ fails closed

# permissions.py x__resolve_guild_id m2/m3 — both snowflake bound ends breakable at exact lengths
-        and DISCORD_SNOWFLAKE_MIN_LENGTH <= len(guild_id) <= DISCORD_SNOWFLAKE_MAX_LENGTH
+        and DISCORD_SNOWFLAKE_MIN_LENGTH < len(guild_id) <= DISCORD_SNOWFLAKE_MAX_LENGTH   # m2
+        and DISCORD_SNOWFLAKE_MIN_LENGTH <= len(guild_id) < DISCORD_SNOWFLAKE_MAX_LENGTH   # m3

# dependencies/auth.py x_get_current_user m36 @ ~L77 — confirmed where-clause flip (fails closed but untested)
-            select(user_model.User).where(user_model.User.discord_id == discord_id)
+            select(user_model.User).where(user_model.User.discord_id != discord_id)

# roles.py xǁRoleVerificationServiceǁcheck_game_host_permission m9 L234 / paired m10 L235
-     if not allowed_host_role_ids:          -         return False
+     if allowed_host_role_ids:              +         return True    # empty restriction list ⇒ hosting granted

# config.py xǁAPIConfigǁ__init__ m21 — zip strict flag edit (ValueError on unequal host-part counts under mutation)
-                reversed(frontend_parts), reversed(backend_parts), strict=False
+                reversed(frontend_parts), reversed(backend_parts), strict=True
```

### API and Schema Documentation

- Ledger v2 (`./mutmut-baseline.json`): `entries[relpath][family] = [(class, canonical_summary), …]`, class ∈ {logic, string, notests}; `killed[relpath][family] = [mutant_numbers]`; entry identity `(file, family, coordinate-free canonical summary)`; summaries clipped at 48 chars/side then deduped per family.
- Store layout: verdicts in `mutants/<relpath>.meta → exit_code_by_key` keyed by full store key `<dotted.module.path>.<mangled>__mutmut_N` (U+01C1 separators); expanded trampoline modules at `mutants/<relpath>` hold `x_<mangled>__mutmut_orig` plus one variant def per mutant (bare mangled names only — no dotted module prefix inside stored function names). Verdict codes: 0 survived · 1|3 killed · 5|33 no-tests · −24/36 timeout · 37 typecheck-failed.
- Test mapping: `mutants/mutmut-stats.json → tests_by_mangled_function_name {dotted family key → test ids}` — treat as approximate (stats commit predates HEAD) and cross-validate against actual pytest collection before citing counts.

### Configuration Examples

Per-file/family verified row counts from the committed ledger @ `15e318c9`:

```json
{
  "services/api/dependencies/permissions.py": {
    "families": 15,
    "logic_rows": 85,
    "string_rows": 53,
    "notests_rows": 0
  },
  "services/api/auth/tokens.py": {
    "families": 10,
    "logic_rows": 69,
    "string_rows": 58,
    "notests_rows": 27
  },
  "services/api/middleware/authorization.py": {
    "families": 1,
    "logic_rows": 39,
    "string_rows": 21,
    "notests_rows": 0
  },
  "services/api/auth/oauth2.py": {
    "families": 6,
    "logic_rows": 33,
    "string_rows": 26,
    "notests_rows": 0
  },
  "services/bot/auth/role_checker.py": {
    "families": 6,
    "logic_rows": 28,
    "string_rows": 14,
    "notests_rows": 0
  },
  "services/api/config.py": {
    "families": 4,
    "logic_rows": 27,
    "string_rows": 19,
    "notests_rows": 0
  },
  "services/bot/auth/cache.py": {
    "families": 3,
    "logic_rows": 27,
    "string_rows": 18,
    "notests_rows": 0
  },
  "services/api/auth/roles.py": {
    "families": 8,
    "logic_rows": 23,
    "string_rows": 3,
    "notests_rows": 20
  },
  "services/api/dependencies/auth.py": {
    "families": 1,
    "logic_rows": 11,
    "string_rows": 4,
    "notests_rows": 0
  },
  "services/api/middleware/error_handler.py": {
    "families": 4,
    "logic_rows": 7,
    "string_rows": 32,
    "notests_rows": 0
  },
  "shared/utils/discord_tokens.py": {
    "families": 1,
    "logic_rows": 3,
    "string_rows": 1,
    "notests_rows": 0
  },
  "services/api/middleware/cors.py": {
    "families": 1,
    "logic_rows": 0,
    "string_rows": 2,
    "notests_rows": 0
  }
}
```

Top-15 families by logic rows (kill-target ordering input): authorization `dispatch` 39 · tokens `get_user_tokens` 28 · tokens `refresh_user_tokens` 20 · cache `RoleCache.get_user_roles` 16 · permissions `verify_guild_membership` 16 · config `APIConfig.__init__` 15 · permissions `get_guild_name` 14 · tokens `store_user_tokens` 14 · deps/auth `get_current_user` 11 · roles `has_permissions` 11 · oauth2 `validate_state` 11 · config `get_rate_limits` 10 · permissions `verify_game_access` 9 · permissions `_check_guild_membership` 9 · role_checker `get_guild_roles` 8.

### Technical Requirements

1. **Confirmed fail-open direction flips & boundary breaks to kill first** (all unit-test-klllable; no code change needed): (a) permissions `_check_guild_membership` m19 @ ≈L84 — membership granted when projection lacks the user (exact site disambiguated by hunk offset at implementation time); (b) roles `check_game_host_permission` m9 L234 + paired m10 L235 — hosting granted with an empty host-role restriction list; (c) roles `has_permissions` m58 @ L163/L181 area — grant-all on missing-guild-roles or error path; (d) `_resolve_guild_id` m2/m3 — exactly-min/max-length snowflakes bypass the fast path; (e) deps/auth m36 where-clause `==→!=`.
2. Hard boundaries from task brief (binding for implementer too): writes only under `.copilot-tracking/research/` during research; never run `make restamp-mutmut-baseline`, `scripts/run-mutmut.py`, or `scripts/mutmut_ledger.py gate|snapshot|run`; mutmut verdicts consumed solely via the serial pipeline's end-of-phase restamp; all local verification is plain pytest without `--testmon`.
3. **TDD applicability statement** (per `.github/instructions/test-driven-development.instructions.md` + `unit-tests.instructions.md`): TDD (RED→GREEN, `xfail(strict=True)` stubs) applies to new/enhanced production code only. The dominant Phase-1 work — strengthening tests for already-correct code — is explicitly outside TDD scope: no stubs, **never xfail markers even when uncertain of outcome**, assertions written directly against live implementation and must pass immediately; a failing test then has exactly two valid responses (implementation bug → fix it; assertion wrong → fix it). Only a wave-2-surprise real bug or a semantic surprise promoted into a production edit switches that item to bug-fix/enhancement TDD and requires explicit user sign-off on the behavior delta first.
4. House rules: manual `pytest --testmon` prohibited (advances `.testmondata`, breaks pre-commit diff coverage); stale `.testmondata` is deleted before retrying, never hand-run forward. Any pre-commit bypass needs explicit user approval — ledger-gate failures are signals of incomplete/regressed work, not blockers to suppress.
5. **Sign-off caveat:** full-diff re-examination found zero confirmed logic weaknesses needing hardening in T1, so user sign-off on authz behavior changes is _not_ expected in waves 1–4. It becomes required if (a) W2 testing exposes a genuine bug in one of the seven untested functions (switches to xfail-TDD bug-fix flow), or (b) W3 boundary testing of `_get_cookie_domain` unequal-part-count hosts reveals surprising strict-zip semantics worth changing (currently tested around, not changed).

## Recommended Approach

**Authorization-core-first within T1: security-semantics kills first, then mechanical bulk test-hardening by file, zero behavior changes, single restamp at phase end.** Sequencing alternatives were evaluated against measured data before selection: largest-count-first (permissions→tokens→…) maximizes raw row burn per hour but defers the highest-severity flips to later and leaves `tokens.py`/`oauth2.py` ratchet-exposed while neighbors churn; highest-test-gap-density-first (`validate_state` 2 tests / 11 rows; `dispatch` 6 / 39) optimizes yield-per-test but interleaves cosmetic debt ahead of confirmed fail-open paths. The selected hybrid ranks each commit target by severity × kill-density using the taxonomy above — which happens to place authorization core (flip/boundary/guard kills across permissions, roles, oauth2, deps/auth) in wave 1 and the mechanical A1 arg-pinning volume later — preserving gate sensitivity on security files early with predictable effort. Alternatives are removed from further consideration here; their only retained contribution is absorbed below (map existing tests per family from the stats mapping before writing assertions; one observable contract per test).

**Wave plan (each item = one or more commits; every commit must pass pre-commit incl. mutation-ledger gate rc=0):**

1. **W0 Hygiene (first commit):** remove dead unreachable `return current_user` at `permissions.py::require_manage_guild` L409 — pure deletion, zero observable change; done first so mutant ids for later functions don't shift mid-phase.
2. **W1 Security semantics (~25 raw ids / ~20 logic rows):** boundary/negative fixtures + `pytest.raises` status_code/detail pins: snowflake exact-min/max ids (`_resolve_guild_id`); missing-user-data & stale-projection cases for `_check_guild_membership`/`verify_guild_membership` (assert False return AND `get_user_guilds` suppression); empty-restriction hosting case (`check_game_host_permission`); unknown-role permission-bit defaults stay 0 (`has_permissions`, both implicit-bit mutants); all four deps/auth 401 raises pinned (type+status+detail) plus permissions 503/404 sites; where-clause equality pin for `get_current_user` by comparing the mocked session's captured `Select.whereclause` to an independently built statement (validate this SQLAlchemy equality technique once before templating it). Kill dispatch m34/m51 branch flips with response-object assertions while in-file.
3. **W2 Untested-function conversion (N class, 51 ids / 47 rows):** new pass-immediately unit tests per the no-xfail rule — tokens `{get_encryption_key, is_token_expired, decrypt_token, encrypt_token}` (prefer real-Fernet roundtrip so `ljust`/key-length-boundary paths execute) and roles `{_get_cache, check_bot_manager_permission}` (manager-role hit, fallback-to-MANAGE_GUILD incl. boolean restructure rows, unconfigured-guild path). After landing, notests rows convert: mostly killed outright (simple arg/null assignments in small functions); any survivors reclassify as gated logic debt against file targets.
4. **W3 Bulk A1 arg/value pinning (~294 raw ids / ~235 rows — volume wave; ≈70% of remaining logic debt):** mechanical pattern per function from the reconstructed inventory — exact-arg mock asserts (`assert_called_once_with`; `ANY` only where a value is genuinely non-essential), return-payload field provenance pins, monkeypatched `os.getenv` propagation (kills S-env-name literals opportunistically). File order by row count: permissions → tokens → cache → oauth2 → config → error_handler/deps tail. Where an assertion would need to pin internal call _ordering_ rather than behavior, back out (house standard + keeps restamp clean).
5. **W4 Logger/message resolution:** kill A3 (~84 rows) via structural log asserts with sanctioned `ANY` wording (one behavior per test); then classify residual string-class debt into the acceptance set below. Optionally knock out cheap killable S-other rows (oauth param case pins in `generate_authorization_url`, `"details"` key in error_handler responses) if effort remains — explicitly not required.
6. **W5 Phase-end hygiene & restamp:** full-suite run green, single ledger restamp producing v4 (naming per census convention `YYYYMMDD-restamp-v4-on-develop.json`, archived to `.copilot-tracking/testing/mutation-census/`) with a one-line note recording pre/post logic-row counts against the success criteria; review STALE rows visually at this point (informational unless masking a KILL REGRESSION in changed scope).

**Commit granularity:** one commit per (file × wave step), e.g. "test(permissions): pin fail-open guards and snowflake boundaries"; no multi-file mixed-strategy commits so bisect attributes any gate failure or KILL REGRESSION to one file's test delta. Small files (cors, discord_tokens, deps/auth tail) may fold into their W3 parent commit.

**Verification loop (every commit):** `uv run pytest <touched test paths> -q` (no `--testmon`) green → pre-commit chain incl. mutation-ledger gate rc=0 on push-parity → after each _wave_, rerun the scoped T1 set (baseline 248 passed must only grow) and keep full suite ≥ 2585 passing. No manual mutmut runs at any point (store is serial-pipeline-owned); if `.testmondata` goes stale mid-phase (pre-commit 0%-diff-coverage symptom), delete it before retrying — never hand-run testmon.

## Implementation Guidance

- **Objectives**: bring T1 logic-class surviving debt from baseline 352 ledger rows / 440 raw ids to ≤ ~~50 rows via unit-test strengthening first; convert all 47 notests rows in the seven untested security functions to tested status with zero survivors remaining there; leave string-class debt as an explicit documented acceptance list (~~≤165 raw string-class ids: 8 header-case + 1 encoding equivalence + ~155 msg-literal wording minus W1/W3-pinned slice, final count fixed at restamp time); achieve zero KILL REGRESSION events and zero suppressed gates across every phase commit without any production behavior change.
- **Key Tasks** (fix-strategy classification per cluster):
  - Strategy A — unit-test hardening on existing correct code (W0–W1): mechanism = boundary/negative fixtures, `pytest.raises` pins of type+status_code+detail, captured-Select where-clause comparison; expected kills ≈ 25 raw ids / ~20 rows (A6+A4+A2 incl. where-flip); effort S (~2–3 d incl. fixture scaffolding reuse); risk none observable (tests pass against current code by construction).
  - Strategy B′ — untested-function coverage (W2), distinct from defensive hardening because it involves no production change: new pass-immediately tests; expected conversion 51 ids / 47 rows mostly → killed; effort M (~2 d); risk low — a genuine bug found here switches that item to xfail-TDD bug-fix flow with sign-off (Technical Requirements #3/#5).
  - Strategy C — bulk arg/value pinning (W3, + opportunistic env-name literals): exact-arg mock asserts + payload provenance pins; expected kills ~294 raw ids / ~235 rows; effort L–XL (~6–10 d, highly mechanical; inventory re-derivable in minutes via the Complete Examples method); risk low-medium from brittle over-assertion on internal call sequences — mitigated by behavior-relevant-args-only discipline already mandated by the unit-test standard.
  - Strategy D — logger/message structural asserts (W4): `caplog`/mock-logger with `ANY` wording per house style; expected kills ~105 raw ids / ~84 rows; effort M (~3 d); risk low (wording deliberately unasserted).
  - Strategy E — defensive hardening (code changes): **none confirmed required for logic-class debt** (zero verified weaknesses after full-diff re-examination). Only candidates: dead-code deletion at permissions.py L409 (no behavior delta, W0) and an optional docstring note on `_get_cookie_domain` strict-zip semantics if W3 testing reveals surprising unequal-part-count behavior (would then become a sign-off-gated xfail-TDD enhancement item). Expected code-change kills: 0 required.
  - Documented acceptance (final bucket, count + justification per group): header-name case variants (8 raw string ids — Starlette `CaseInsensitiveDict` makes lookups byte-case-insensitive; asserting exact-case storage would test starlette internals) · `decode("utf-8")→"UTF-8"` (1 — codec normalization) · log-message wording literals (~155 minus pinned slice — house standard sanctions `ANY` for wording; structural log asserts still kill every logic-class arg mangling at those sites so nothing gating goes untested) · residual error/detail wording where type+status already pinned by W1/W3 raises-pins (small double-digit estimate, fixed at restamp). Explicitly NOT acceptable: S-other behavioral literals (95 raw ids — observable contracts, remain killable debt ranked below all logic work) and any logic-class survivor (logic acceptances = 0).
- **Dependencies**: read-only store inputs (`mutants/**/*.meta`, expanded modules, `mutants/mutmut-stats.json`) owned by the serial pipeline — never written during phase; project scripts `scripts/mutmut_ledger.py` / `scripts/mutmut-logic-survivors.py` loaded unmodified via importlib under `uv run python` for target re-derivation between waves; existing fixture/mock patterns in `tests/unit/services/bot/auth/test_role_checker.py` (db-mock style) and `tests/unit/services/api/dependencies/test_api_permissions.py` as scaffolding base; instruction files unit-tests/TDD/quality-check-overrides/testmon rules as binding constraints; end-of-phase single v4 restamp executed only by the serial pipeline after user approval of this plan.
- **Success Criteria** (baseline verified @ `15e318c9` → Phase-1 targets, measured by stated means):

| metric                                                                       | baseline                                                                                            | target                                                                                                                                                                                                                    | measurement                                                                                                           |
| ---------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------- |
| Logic rows surviving (T1)                                                    | 352 rows / 440 raw ids                                                                              | ≤ 50 rows (≥ ~85% row reduction); per-file: permissions ≤15 · tokens ≤12 · authorization ≤6 · oauth2 ≤6 · role_checker ≤5 · config ≤5 · cache ≤5 · roles ≤5 · auth-dep ≤2 · error_handler ≤2 · discord_tokens ≤1 · cors 0 | restamp-v4 verdict census over `mutants/<file>.meta` + regenerated ledger rows via the validated zero-mismatch method |
| Notests rows in the seven untested security functions                        | 47 rows / 51 ids                                                                                    | 0 untested rows remain there; any survivors reclassify to gated logic debt counted against file targets                                                                                                                   | store verdict census over those 7 function families                                                                   |
| KILL REGRESSION events (tracked killed ids failing re-kill in changed scope) | gate rc=0 at HEAD                                                                                   | zero on every phase commit and unresolved-none at restamp                                                                                                                                                                 | pre-commit ledger gate output per commit; restamp report regression preview                                           |
| Unit suite health                                                            | full **2585 passed** (`uv run pytest tests/unit -q`, no --testmon); T1 scoped subset **248 passed** | full ≥ 2585 with 0 failures/0 errors at each wave boundary; scoped set only grows (no removals, no xfail markers ever added)                                                                                              | same commands at boundaries                                                                                           |
| Gate hygiene                                                                 | —                                                                                                   | mutation-ledger gate rc=0 on every commit; no `--no-verify`/`SKIP=`; no manual mutmut/testmon execution; `.testmondata` absent or deleted-stale rule honored                                                              | git log vs hook logs; absence of checksum advances                                                                    |
| Acceptance bookkeeping                                                       | —                                                                                                   | restamp-v4 acceptance list contains only this doc's justified groups, ≤ ~165 raw string-class ids total, each row citing its justification class; logic-class acceptances = 0                                             | restamp v4 census note                                                                                                |
