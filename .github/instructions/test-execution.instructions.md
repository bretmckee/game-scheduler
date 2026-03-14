---
description: 'Rules for running integration and e2e test scripts'
applyTo: '**'
---

# Test Script Execution Rules

These rules apply whenever running `scripts/run-integration-tests.sh` or `scripts/run-e2e-tests.sh`.

## Runtime Expectations

These scripts spin up Docker environments and run real service infrastructure — they are not fast:

- **Integration tests** (`run-integration-tests.sh`): take **more than 5 minutes** to complete
- **E2E tests** (`run-e2e-tests.sh`): take **more than 10 minutes** to complete

Always use a terminal timeout large enough to cover the full run:

- Integration tests: at least **600000ms** (10 minutes)
- E2E tests: at least **900000ms** (15 minutes)

## Output Collection — Critical Rules

**ALWAYS** capture full output with `tee` before any filtering:

```bash
# Correct: full output saved first, then inspect as needed
scripts/run-integration-tests.sh |& tee output-integration.txt
scripts/run-e2e-tests.sh |& tee output-e2e.txt
```

**NEVER** pipe directly to `grep`, `tail`, `head`, or any filter without first routing through `tee`:

```bash
# WRONG: if any test fails, all failure details are permanently lost
scripts/run-integration-tests.sh | grep -E "PASSED|FAILED|ERROR"
```

When reading the captured output file after the run, use at least **200 lines**. If that is not enough to see all failures, read more — do not re-run the suite. A full rerun wastes 5–10+ minutes just to retrieve information that was already produced.

## Why This Matters

If a test fails and output was filtered, there is no way to diagnose the failure without running the entire suite again from scratch. Given the runtimes above, every unnecessary rerun is expensive. Capture everything first, filter afterward.

## Passing Options to pytest

Both scripts use `pytest` as the container entrypoint. Any arguments passed to the script are forwarded directly to pytest, so all standard pytest options work — including running a specific test file or test by node ID:

```bash
# Run a specific test file
scripts/run-integration-tests.sh tests/integration/test_signup.py

# Run a single test by node ID
scripts/run-integration-tests.sh tests/integration/test_signup.py::test_player_can_signup

# Run tests matching a keyword
scripts/run-integration-tests.sh -k "signup"

# Same patterns work for e2e tests
scripts/run-e2e-tests.sh tests/e2e/test_game_flow.py
```

This is particularly useful when debugging a specific failure — narrow the run to the relevant test(s) to cut cycle time, while still capturing output via `tee`.
