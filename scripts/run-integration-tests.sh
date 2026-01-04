#!/bin/bash
# Run integration tests in isolated Docker environment
# These tests verify notification daemon and PostgreSQL LISTEN/NOTIFY

set -e

# Environment file location
ENV_FILE="config/env.int"

cleanup() {
  if [ -n "$SKIP_CLEANUP" ]; then
    echo "Skipping integration test environment cleanup (SKIP_CLEANUP is set)"
    return
  fi
  echo "Cleaning up integration test environment..."
  docker compose --env-file "$ENV_FILE" down -v
}

trap cleanup EXIT

echo "Running integration tests..."
# Ensure full stack (including init) is healthy before running tests
docker compose --env-file "$ENV_FILE" up -d --build system-ready

# Build if needed, then run tests without restarting dependencies
# When $@ is empty, compose uses command field; when present, it overrides
docker compose --env-file "$ENV_FILE" run --build --no-deps --rm integration-tests "$@"

echo "Integration tests passed!"
