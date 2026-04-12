<!-- markdownlint-disable-file -->

# Changes: Cache Metrics and Read-Through Wrapper Consolidation

## Overview

Tracking file for implementation of `shared/cache/operations.py` and per-operation OTel cache metrics.

---

## Added

- `shared/cache/operations.py` — New module with `CacheOperation` StrEnum (16 members) and `cache_get` coroutine with `cache.hits`, `cache.misses`, and `cache.duration` OTel metrics.
- `tests/unit/shared/cache/test_operations.py` — 8 unit tests covering `CacheOperation` membership and `cache_get` hit/miss counter and histogram behaviour.

## Modified

- `tests/unit/scripts/test_check_lint_suppressions.py` — Cleared `APPROVED_OVERRIDES` from the environment inside `_run_main_with_args` so tests are isolated from the parent commit environment (out-of-plan bug fix: test failed when commit was run with `APPROVED_OVERRIDES=1`).

## Removed
