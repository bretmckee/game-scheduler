<!-- markdownlint-disable-file -->

# Task Research Notes: mutmut 3.5 -> 3.7 upgrade + spurious-timeout fix validation

## Research Executed

### File Analysis

- `.venv/lib/python3.13/site-packages/mutmut/__main__.py` (installed v3.5.0)
  - `timeout_checker` (L1155-1171): outer loop iterates every `(file m, mutant_name)` pair while the inner kill test checks `m.estimated_time_of_tests_by_mutant[mutant_name]` — i.e., the _outer-loop_ mutant's estimate is applied to **every live child PID in that file**. Measured consequence: a near-zero-estimate sibling capped all of its siblings at ~15 s wall; all 75 coldrun5 timeout deaths were SIGXCPU (`exit_code=-24`) with measured walls 15.3-17.3 s. Only 21/75 exceeded their own threshold; 54 died before it could fire (49 in `shared/services/image_storage.py`, own est 3.862 s = 72.9 s legitimate budget vs file-min est 0.018 s => 15.28 s killer line).
- `/tmp/mm-3.7.0.py` (fetched upstream source at tag 3.7.0, kept as durable copy)
  - Cross-mutant `timeout_checker` removed entirely; replaced by per-PID deadline registry.
  - `set_start_method("fork")` now guarded against already-set contexts (GH-466), so the import-time fork crash that motivated our launcher wrapper no longer reproduces via normal entry points.
- `/tmp/mm-data37.py` (upstream `src/mutmut/mutation/data.py` @ 3.7.0)
  - Per-file `.meta` writer keeps the exact core keys our tooling parses — `exit_code_by_key`, `type_check_error_by_key`, `durations_by_key`, `estimated_durations_by_key` — plus additive fields (`version`, `spans`, `hash_by_function_name`). No schema break for `scripts/mutmut_ledger.py` (reads only `exit_code_by_key` from live metas).
- Upstream status map (@ 3.7.0): `-24` appears twice in `status_by_exit_code`; last key wins => `-24: "timeout"`. Effective semantics unchanged vs 3.5.0; our ledger's `STATUS_TO_CLASS` mapping remains valid.

### Code Search Results

- `register_timeout(pid=pid, timeout_s=...)`
  - Called at child fork with **that mutant's own** wall budget `(estimated_time_of_tests + config.timeout_constant) * config.timeout_multiplier`; min-heap `(deadline, pid)` popped by a checker thread that SIGXCPUs expired PIDs (ProcessLookupError tolerated). Present on tags 3.6.0, 3.7.0 and main — fix landed <= 3.6.0.
- `[tool.mutmut]` in `pyproject.toml`
  - Migrated pre/post upgrade: `paths_to_mutate` -> `source_paths`, `tests_dir` -> `pytest_add_cli_args_test_selection = ["tests/unit"]`, `also_copy` unchanged. Parses cleanly post-upgrade with zero deprecation warnings (`Config.get()` verified).

### External Research

- #githubRepo:"boxed/mutmut issue 518 timeout wrong mutant estimated_time_of_tests_by_mutant"
  - Issue is OPEN, filed by another user 2026-05-13, no maintainer response or labels, never linked to the fix commit. Body quotes the exact buggy loop with a "wrong mutant!" annotation and suggests the same per-PID direction we independently derived. Our measured forensics are an independent repro of it.
- #fetch:https://raw.githubusercontent.com/boxed/mutmut/3.7.0/src/mutmut/threading/timeout.py
  - Full per-PID registry implementation read and quoted during validation (see File Analysis above).
- #fetch:https://pypi.org/pypi/mutmut/json
  - Release history: 3.6.0 (2026-06-06), 3.7.0 (2026-07-31); pin moved from `"mutmut>=3.5.0"` to `"mutmut>=3.7.0,<4.0"`; `uv lock --upgrade-package mutmut` + `uv sync` installed exactly 3.7.0.

### Project Conventions

- Standards referenced: `.github/instructions/commit-messages.instructions.md`, `.copilot-tracking/research/AGENTS.md` (verified-findings-only rule)
- Instructions followed: house rules on measured-numbers rigor, durable snapshots in /tmp before clobbering runs, commit-to-current-branch (`mutmut-audit`)

## Key Discoveries

### Root Cause (measured, not inferred)

- The "tests running >70 s" hypothesis was refuted by measurement: max child wall across all 14,568 completed coldrun5 children = **17.3 s** (p95=0.5 s). All deaths clustered at the misapplied ~15 s sibling line — cross-mutant estimate application per #518, plus a secondary self-timeout path for near-zero-estimate families under 12-way parallel load.
- Run-to-run timeout variance (#3: 48 / #4: 131 / #5: 75) is explained by load-dependent counts of children crossing that line — inconsistent with intrinsic slowness.

### Validation Matrix (all numbers measured from store snapshots)

| run                                                         | version               | killed | survived | no-tests | timeouts   | notes                                                                                                                                                                                                                                                                                                                                |
| ----------------------------------------------------------- | --------------------- | ------ | -------- | -------- | ---------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| coldrun5                                                    | 3.5.0 (buggy watcher) | 8792   | 5701     | 950      | 75         | snapshot `/tmp/mutmut-forensics-coldrun5-20260831-233009/`                                                                                                                                                                                                                                                                           |
| smoke37 (scoped `shared.services.image_storage.*`)          | 3.7.0                 | -      | -        | -        | 11 in-file | machine suspended mid-run; all 11 = suspend-frozen children whose **own** ~72 s deadline elapsed during the freeze (`wall` recorded ~28,1xx s). Zero spurious kills among unfrozen children; `x_store_image`: 0 timeouts vs 11 false kills under #5. Snapshot `/tmp/mutmut-smoke37-20260901-075543/`                                 |
| coldrun6 (full)                                             | 3.7.0                 | 8880   | 5651     | 1601     | 37         | image_storage skipped by incremental cache (stale smoke values retained); remaining 26 fresh timeouts ALL exceed their own calibrated deadline (measured 15.2-16.0 s vs budgets 15.1-15.7 s) and were already timing out in #5 => genuine self-budget class, no upgrade regression. Snapshot `/tmp/mutmut-coldrun6-20260901-080305/` |
| imgrepro37 (forced image_storage rerun) + final store audit | 3.7.0                 | 8844   | 5698     | 1601     | **26**     | all stale >1000 s entries flushed from the entire store (final audit: 0). image_storage.py final: 0 timeouts; `downscale_if_oversized` 70K/46S, other families all decided K/S. Snapshot `/tmp/mutmut-final-37-20260901-081821/`                                                                                                     |

- Reclassifications on the 15,518 keys present in both coldrun5 and the live store: of #5's 75 timeouts, the overwhelming majority resolved to real verdicts (image_storage alone: 32 timeout->survived + 17 timeout->killed); **zero killed verdicts were ever lost** (`killed -> X = 0` repo-wide on that join; only small `survived -> killed` flips remain — order-dependent weak killers, conservative direction, flagged for logic-debt triage).
- Keyset delta vs 3.5.0 store: **+651 / -0 mutants**, exactly matching the no-tests delta (+651) => new mutator coverage shipped in 3.6+ concentrated in formatter modules (`services/bot/formatters/game_message.py` +439, `shared/message_formats.py` +110), most not yet unit-tested. The committed baseline ledger must be regenerated against this expanded key set before further ratchet comparisons.

### Behavioral Changes Affecting Our Workflow (verified by observation)

1. Incremental cache with git change detection (default `use_git_change_detection=true`) preserves out-of-scope results across runs — scoped runs no longer clobber the whole store. Consequence: abnormal interruptions (machine suspend mid-run, crashes) leave stale per-key entries behind until a forced rerun of those keys/files; audit every run's durations for >1000 s outliers after any interruption (final-store check: 0 present today).
2. Timeout budget knobs exist but are marked unstable upstream: `[tool.mutmut] timeout_multiplier = 15.0`, `timeout_constant = 1.0` (defaults verified live). Not configured yet; revisit if the 26 legitimate self-budget timeouts prove too noisy under CI load.
3. Launcher wrapper `scripts/run-mutmut.py` remains valid and harmless; its original justification (unguarded import-time `set_start_method("fork")`) is fixed upstream (GH-466), so it is belt-and-braces only now.

## Recommended Approach

Upgrade path adopted and validated (monkeypatch-in-launcher alternative dropped as unnecessary): pin `"mutmut>=3.7.0,<4.0"`, migrate the two config keys, keep launcher + ledger tooling unchanged (schema-compatible). Remaining follow-ups: regenerate baseline ledger v8 on the 16,161-key store, triage the 7-file legitimate-timeout families (handlers 7, scheduler_loop 6, main 5, bot 3, guild_projection 2, client 2, announcement_loop 1) — mostly async-loop hang mutants where raising `timeout_multiplier` or adding tests is the right lever — and optionally post our measured repro data to boxed/mutmut#518.

## Implementation Guidance

- **Objectives**: keep mutation-gate numbers trustworthy (no false timeouts); track new mutator coverage into the baseline
- **Key Tasks**: regenerate baseline from `/tmp/mutmut-final-37-20260901-081821/`; re-run gate E2E (`TESTING=true .venv/bin/python scripts/mutmut_ledger.py gate --base HEAD`) after regeneration; decide #518 comment
- **Dependencies**: none outstanding for the upgrade itself
- **Success Criteria**: full cold run completes rc=0 with all remaining timeouts individually exceeding their own deadlines; zero killed verdicts lost vs prior census; gate passes on a known-clean base commit
