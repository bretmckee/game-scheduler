---
description: 'Game Scheduler Integration and E2E tests'
applyTo: '**/tests/integration**.py, **/tests/e2e**.py, scripts/run-integration-tests.sh, scripts/run-e2e-tests.sh'
---

## General Instructions

- Integration and e2e tests run inside of docker compose with wrapper scripts:
  - `scripts/run-integration-tests.sh` for integration tests
  - `scripts/run-e2e-tests.sh` for e2e tests
- These scripts start with clean environments and are best used for full runs to verify changes

## Output Collection Best Practices

These test suites are expensive to rerun — capture everything before filtering:

- **Integration tests take more than 5 minutes; e2e tests take more than 10 minutes**
- **Always** pipe through `tee` before any filtering so the full log is preserved:
  ```bash
  scripts/run-integration-tests.sh |& tee output-integration.txt
  scripts/run-e2e-tests.sh |& tee output-e2e.txt
  ```
- **Never** pipe directly to `grep`, `tail`, or `head` without first routing through `tee` — if a test fails, all failure details are permanently lost and require a full rerun to recover
- When reading captured output, use at least **200 lines**; if that is insufficient to see failures, read more rather than rerunning
- Use a terminal timeout of at least **600000ms** for integration tests and **900000ms** for e2e tests

## Reducing Test Cycle Time for Debugging

When debugging individual tests, you can reduce cycle time by skipping the automatic cleanup:

```bash
# For integration tests - skip cleanup to keep infrastructure running
SKIP_CLEANUP=1 scripts/run-integration-tests.sh [pytest-options]

# For e2e tests - skip cleanup to keep infrastructure running
SKIP_CLEANUP=1 scripts/run-e2e-tests.sh [pytest-options]
```

After the first run, infrastructure remains running and subsequent test runs are faster. When done debugging:

```bash
# Clean up integration test environment
docker compose --env-file config/env.int down -v

# Clean up e2e test environment
docker compose --env-file config/env.e2e down -v
```

**Important notes:**

- The container entrypoint is `pytest`, so you can pass any pytest options or specific test paths
- The `SKIP_CLEANUP` variable prevents automatic teardown of the test environment to allow the service logs to be inspected
- The `--build` flag in the scripts rebuilds the test container to pick up test code changes
- To pick up changes in services (API, bot, daemon, etc.), rebuild them separately:

  ```bash
  # For integration tests
  docker compose --env-file config/env.int build

  # For e2e tests
  docker compose --env-file config/env.e2e build
  ```
