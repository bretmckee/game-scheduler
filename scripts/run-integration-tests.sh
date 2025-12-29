#!/bin/bash
# Run integration tests in isolated Docker environment
# These tests verify notification daemon and PostgreSQL LISTEN/NOTIFY

set -e

# Environment file location
ENV_FILE="config/env.int"

cleanup() {
  echo "Cleaning up integration test environment..."
  docker compose --env-file "$ENV_FILE" down -v
}

trap cleanup EXIT

echo "Running integration tests..."
# Build if needed, then run tests
# When $@ is empty, compose uses command field; when present, it overrides
docker compose --env-file "$ENV_FILE" run --build --rm integration-tests "$@"

echo "Integration tests passed!"
