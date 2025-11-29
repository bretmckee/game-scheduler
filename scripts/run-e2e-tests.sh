#!/bin/bash
# Run end-to-end tests in isolated Docker environment
# These tests verify the complete notification flow including Discord bot interactions
#
# REQUIRED: Set up test Discord bot and guild first (see TESTING_E2E.md)

set -e

# Check for .env.e2e file
if [ ! -f .env.e2e ]; then
  echo "ERROR: .env.e2e file not found"
  echo "Create .env.e2e with test Discord credentials"
  echo "See TESTING_E2E.md for setup instructions"
  exit 1
fi

# Source .env.e2e to check required variables
source .env.e2e

# Check for required test Discord credentials
if [ -z "$TEST_DISCORD_TOKEN" ]; then
  echo "ERROR: TEST_DISCORD_TOKEN environment variable is required in .env.e2e"
  echo "See TESTING_E2E.md for setup instructions"
  exit 1
fi

if [ -z "$TEST_DISCORD_GUILD_ID" ] || [ -z "$TEST_DISCORD_CHANNEL_ID" ]; then
  echo "WARNING: TEST_DISCORD_GUILD_ID and TEST_DISCORD_CHANNEL_ID should be set in .env.e2e"
  echo "Tests may fail without these. See TESTING_E2E.md for setup instructions"
fi

cleanup() {
  echo "Cleaning up end-to-end test environment..."
  docker compose -f docker-compose.e2e.yml --env-file .env.e2e down -v
}

trap cleanup EXIT

echo "Running end-to-end tests..."
docker compose -f docker-compose.e2e.yml --env-file .env.e2e run --rm e2e-tests

echo "End-to-end tests passed!"
