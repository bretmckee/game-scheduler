#!/bin/bash
# Run integration tests in isolated Docker environment
# These tests verify notification daemon and PostgreSQL LISTEN/NOTIFY

set -e

# Environment file location
ENV_FILE="config/env.int"

echo "Building integration test container..."
docker compose --env-file "$ENV_FILE" build integration-tests init

cleanup() {
  echo "Cleaning up integration test environment..."
  docker compose --env-file "$ENV_FILE" down -v
}

trap cleanup EXIT

echo "Running integration tests..."
if [ $# -eq 0 ]; then
  # Use marker-based selection (command from compose.int.yaml: -m integration -v --tb=short)
  docker compose --env-file "$ENV_FILE" run --rm integration-tests
else
  # User specified args - pass them through
  docker compose --env-file "$ENV_FILE" run --rm integration-tests "$@"
fi

echo "Integration tests passed!"
