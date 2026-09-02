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

| run                                                         | version               | killed | survived | no-tests | timeouts   | notes                                                                                                                                                                                                                                                                                                                                                                            |
| ----------------------------------------------------------- | --------------------- | ------ | -------- | -------- | ---------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| coldrun5                                                    | 3.5.0 (buggy watcher) | 8792   | 5701     | 950      | 75         | snapshot `/tmp/mutmut-forensics-coldrun5-20260831-233009/`                                                                                                                                                                                                                                                                                                                       |
| smoke37 (scoped `shared.services.image_storage.*`)          | 3.7.0                 | -      | -        | -        | 11 in-file | machine suspended mid-run; all 11 = suspend-frozen children whose **own** ~72 s deadline elapsed during the freeze (`wall` recorded ~28,1xx s). Zero spurious kills among unfrozen children; `x_store_image`: 0 timeouts vs 11 false kills under #5. Snapshot `/tmp/mutmut-smoke37-20260901-075543/`                                                                             |
| coldrun6 (full)                                             | 3.7.0                 | 8880   | 5651     | 1601     | 37         | image_storage skipped by incremental cache (stale smoke values retained); remaining 26 fresh timeouts ALL exceed their own calibrated deadline (measured 15.2-16.0 s vs budgets 15.1-15.7 s) and were already timing out in #5 => no upgrade regression; phase-2 A/B reclassified them (see "Spurious Timeout Class Resolved"). Snapshot `/tmp/mutmut-coldrun6-20260901-080305/` |
| imgrepro37 (forced image_storage rerun) + final store audit | 3.7.0                 | 8844   | 5698     | 1601     | **26**     | all stale >1000 s entries flushed from the entire store (final audit: 0). image_storage.py final: 0 timeouts; `downscale_if_oversized` 70K/46S, other families all decided K/S. Snapshot `/tmp/mutmut-final-37-20260901-081821/`                                                                                                                                                 |

- Reclassifications on the 15,518 keys present in both coldrun5 and the live store: of #5's 75 timeouts, the overwhelming majority resolved to real verdicts (image_storage alone: 32 timeout->survived + 17 timeout->killed); **zero killed verdicts were ever lost** (`killed -> X = 0` repo-wide on that join; only small `survived -> killed` flips remain — order-dependent weak killers, conservative direction, flagged for logic-debt triage).
- Keyset delta vs 3.5.0 store: **+651 / -0 mutants**, exactly matching the no-tests delta (+651) => new mutator coverage shipped in 3.6+ concentrated in formatter modules (`services/bot/formatters/game_message.py` +439, `shared/message_formats.py` +110), most not yet unit-tested. The committed baseline ledger must be regenerated against this expanded key set before further ratchet comparisons.

### Spurious Timeout Class Resolved (measured A/B: constant 3.0 -> 4.0)

- Idle-vs-load measurement of representative victims: each runs its **entire** mapped workload (fresh interpreter + full import chain + collection + all mapped tests) in 0.8-2.6 s wall on an idle machine; under default 12-way load they died at ~15.1-16.0 s against near-zero-estimate budgets of ~15.06-15.71 s, i.e., startup/contention multiplies the real work ~6-19x and `(est+constant)*multiplier` cannot see that floor. All 26 victims mapped to only 3-47 tests with total calibrated test-time < 50 ms — none were slow-test families.
- No worker-count knob exists upstream (`max_children = os.cpu_count() or 4`, `__main__.py` L1375 @ tag 3.7.0); only `timeout_multiplier`/`timeout_constant` are configurable. The config fingerprint groups them as "only reclassifies timeouts" (`configuration.py` L202-208), so changing the constant invalidates only keys already verdicted timeout-class — verified surgically: the scoped c=3.0 run re-ran exactly the prior 26 entries with zero collateral verdict changes across all 16,169 joined keys (kills lost: 0).
- c=3.0 A/B (scoped 7 affected files): **24 of 26 resolved to KILLED** (walls 30.2-33.8 s vs new 45.08 s budget); two stragglers hit wall 45.3 s against the same 45.08 s deadline. Straggler root cause confirmed in source: `_projection_heartbeat`'s `while True` loop where N=1 mutates `heartbeat_interval = 30 -> None` and N=4 mutates `await asyncio.sleep(heartbeat_interval) -> sleep(None)`; the resulting `TypeError` is swallowed by the broad `except Exception: logger.error(...)` handler, and each failed iteration never yields back to the event loop, so the task hot-spins and starves every other coroutine in the child process (including pytest-asyncio teardown) => unbounded runtime. Sibling mutants in the same file completed in 0.2-4.6 s under identical load. Both stragglers were killed exactly at their deadline under both constants (c=3.0: 45.3 vs 45.08; c=4.0: 60.4/60.5 vs 60.08): they exceed any finite budget — these timeout verdicts are correct watchdog behavior, not tuning artifacts.
- Adopted setting: `[tool.mutmut] timeout_constant = 4.0` (near-zero-estimate floor budget ~60 s ≈ 78% margin over the measured healthy worst case of 33.8 s); cost is that genuine hangs are now reaped per-child within ≤60 s instead of ~45 s. The knob remains flagged "unstable" upstream; rationale + revisit condition documented in the `pyproject.toml` comment block. The knob-stage store snapshot `/tmp/mutmut-final-knob4-20260901-161010/`: {KILLED 8868, SURVIVED 5698, NO-TESTS 1601, TIMEOUT 2} — the two remaining timeouts were then resolved by a code fix rather than more tuning (see "Genuine Hang Mutants Fixed"). Full keyset join with the pre-knob state, zero kills lost.

### Genuine Hang Mutants Fixed (`_projection_heartbeat`)

- The final two timeout mutants (N=1/N=4) were fixed in production code instead of being accepted as permanent debt: pacing moved outside the exception guard so `await asyncio.sleep(heartbeat_interval)` now runs before the `try` block; any sleep failure terminates the task promptly (die + log semantics approved by user) instead of hot-spinning the event loop. TDD bug-fix cycle followed strictly: strict-xfail regression test verified xfailed on the unfixed code first, then the one-line restructure, then marker removal only. A second test asserts full-interval pacing persists when every write fails; its bounded poller also killed a third mutant revealed by the family re-judgment — N=15 (`logger.error("...", e)` -> `logger.error(None, e)`), whose unformattable record raised inside pytest's log-capture handler during child execution and ended the worker after one iteration while an initial unbounded polling wait spun to the deadline (wall 60.2 s vs budget 60.08 s). With the bounded poller it fails fast => KILLED.
- Validation (scoped rerun against pre-state snapshot `/tmp/mutmut-prehb-20260901-172648/`): heartbeat family fully re-judged with the new tests mapped onto them; N=1/N=4 KILLED at wall 0.2 s, N=15 KILLED, 11 kills gained from previously survived/timeout entries, zero kills lost. Final live store {KILLED 8879, SURVIVED 5689, NO-TESTS 1601} with **zero timeout verdicts repo-wide** — first timeout-free census for this project. Remaining survivors in that family are log-content mutants only (exception arg dropped / message edits), legitimately weak per unit-testing standards. Snapshot `/tmp/mutmut-final-zero-20260901-173257/`.

### Behavioral Changes Affecting Our Workflow (verified by observation)

1. Incremental cache with git change detection (default `use_git_change_detection=true`) preserves out-of-scope results across runs — scoped runs no longer clobber the whole store. Consequence: abnormal interruptions (machine suspend mid-run, crashes) leave stale per-key entries behind until a forced rerun of those keys/files; audit every run's durations for >1000 s outliers after any interruption (final-store check: 0 present today).
2. Timeout budget knobs exist but are marked unstable upstream; `timeout_constant = 4.0` is now configured after measured A/B validation (see "Spurious Timeout Class Resolved") — multiplier left at its 15.0 default.
3. Launcher wrapper `scripts/run-mutmut.py` remains valid and harmless; its original justification (unguarded import-time `set_start_method("fork")`) is fixed upstream (GH-466), so it is belt-and-braces only now.
4. The v2 ratchet helper's API surface changed under us: `scripts/mutmut-logic-survivors.py` imported `SourceFileMutationData`/`ensure_config_loaded` from `mutmut.__main__`; since >= 3.6 the class lives in `mutmut.mutation.data` and config loading is lazy via `Config.get()`. The module loads only when `gate` executes, so the breakage stayed hidden until a real gate run in the heartbeat-fix series — imports ported there and the obsolete init call dropped. Lesson: upgrade validation must include one genuine gate invocation, not just store-schema checks.
5. Ledger size grew with upstream store expansion (+488 tracked entries post-upgrade); regenerating baseline v8 required raising the large-file limit (user-approved per `.github/instructions/quality-check-overrides.instructions.md`: check-added-large-files --maxkb=1000 -> 2048; LEDGER_MAX_BYTES 950_000 -> 2_048_000). Regenerated ledger records zero timeout-class entries anywhere.
6. The ratchet's regression check had a latent scope bug, surfaced only by running the gate on function-scoped change sets: `kill_regressions` compared every baseline-killed family of any in-scope _file_ against live results without skipping families that run never re-judged, so all out-of-scope kills reported as "regressed" (49 phantom FAILs on this tree while the store itself was verified byte-for-byte consistent). Guard added to match the documented contract via the TDD bug-fix cycle (strict xfail RED -> fix -> marker removal), with unit tests now covering both comparison semantics; full gate reports new-logic=0 kill-regressions=0 stale=0 against v8.

## Recommended Approach

Upgrade path adopted and validated (monkeypatch-in-launcher alternative dropped as unnecessary): pin `"mutmut>=3.7.0,<4.0"`, migrate the two config keys, set `timeout_constant = 4.0` after measured A/B validation, fix `_projection_heartbeat`'s hot-spin risk in code, port the ratchet helper to the new import surface, keep launcher + ledger tooling otherwise unchanged (schema-compatible). Baseline ledger v8 is regenerated on the current 16,169-key zero-timeout store (committed with the approved cap raise). Remaining follow-ups: optionally run a full cold confirmation pass (~15 min) to validate the constant margin end-to-end and restamp the ledger cleanly, optionally post our measured repro data to boxed/mutmut#518.

## Implementation Guidance

- **Objectives**: keep mutation-gate numbers trustworthy (no false timeouts); track new mutator coverage into the baseline
- **Key Tasks**: baseline ledger v8 regenerated from the audited live store, gate E2E verified against it, and the `kill_regressions` out-of-scope comparison bug fixed with unit tests (all done); remaining: decide #518 comment; optional full-cold confirmation rerun (~15 min) that also restamps the ledger cleanly (`/tmp/mutmut-final-zero-20260901-173257/` holds the equivalent snapshot)
- **Dependencies**: none outstanding for the upgrade itself
- **Success Criteria (met)**: scoped + full runs on 3.7.0 complete rc=0 with zero spurious timeouts, and zero timeout verdicts repo-wide in total after the `_projection_heartbeat` code fix (final store {KILLED 8879, SURVIVED 5689, NO-TESTS 1601}); zero killed verdicts lost vs prior censuses on every join
