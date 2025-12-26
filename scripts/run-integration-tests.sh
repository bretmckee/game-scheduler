#!/bin/bash
# Run integration tests in isolated Docker environment
# These tests verify notification daemon and PostgreSQL LISTEN/NOTIFY

set -e

echo "Building integration test container..."
docker compose --env-file config/env/env.int build integration-tests init

cleanup() {
  echo "Cleaning up integration test environment..."
  docker compose --env-file config/env/env.int down -v
}

trap cleanup EXIT

echo "Running integration tests..."
if [ $# -eq 0 ]; then
  # Use marker-based selection (command from compose.int.yaml: -m integration -v --tb=short)
  docker compose --env-file config/env/env.int run --rm integration-tests
else
  # User specified args - pass them through
  docker compose --env-file config/env/env.int run --rm integration-tests "$@"
fi

echo "Integration tests passed!"
