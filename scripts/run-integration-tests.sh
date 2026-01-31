#!/bin/bash
# Run integration tests in isolated Docker environment
# These tests verify notification daemon and PostgreSQL LISTEN/NOTIFY

set -e

# Environment file location
ENV_FILE="config/env.int"

if [ -z "$ASSUME_SYSTEM_READY" ]; then
  cleanup() {
    echo "Cleaning up integration test environment..."
    docker compose --env-file "$ENV_FILE" down -v
  }
  trap cleanup EXIT
fi

echo "Running integration tests..."

if [ -z "$ASSUME_SYSTEM_READY" ]; then
  # Ensure full stack (including init) is healthy before running tests
  docker compose --env-file "$ENV_FILE" up -d --build system-ready
else
  echo "Skipping system-ready startup and cleanup (ASSUME_SYSTEM_READY is set)"
fi

# Build if needed, then run tests without restarting dependencies
# When $@ is empty, compose uses command field; when present, it overrides
docker compose --env-file "$ENV_FILE" run --build --no-deps --rm integration-tests "$@"

echo "Integration tests passed!"
