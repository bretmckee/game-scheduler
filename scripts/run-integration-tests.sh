#!/bin/bash
# Run integration tests in isolated Docker environment
# These tests verify notification daemon and PostgreSQL LISTEN/NOTIFY

set -e

cleanup() {
  echo "Cleaning up integration test environment..."
  docker compose -f docker-compose.integration.yml --env-file .env.integration down -v
}

trap cleanup EXIT

echo "Running integration tests..."
docker compose -f docker-compose.integration.yml --env-file .env.integration run --rm integration-tests

echo "Integration tests passed!"
