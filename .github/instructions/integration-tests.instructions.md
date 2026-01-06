---
description: "Game Scheduler Integration and E2E tests"
applyTo: "**/tests/integration**.py, **/tests/e2e**.py, scripts/run-integration-tests.sh, scripts/run-e2e-tests.sh"
---

## General Instructions

- Integration and e2e tests run inside of docker compose with wrapper scripts:
  - `scripts/run-integration-tests.sh` for integration tests
  - `scripts/run-e2e-tests.sh` for e2e tests
- These scripts start with clean environments and are best used for full runs to verify changes

## Output Collection Best Practices

- Integration and e2e tests take a relatively long time to run
- When collecting output, use a minimum of 75 lines to avoid needing to rerun tests
- Always send raw results to `tee` so additional output is available without rerunning if needed
- While reducing output with tools like `tail` is acceptable, removing too much adds significant time if tests must be rerun

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
