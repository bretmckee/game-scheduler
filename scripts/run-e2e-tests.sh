#!/bin/bash
# Run end-to-end tests in isolated Docker environment
# These tests verify the complete notification flow including Discord bot interactions
#
# REQUIRED: Set up test Discord bot and guild first (see TESTING_E2E.md)

set -e

# Environment file location
ENV_FILE="config/env.e2e"

# Check for env file
if [ ! -f "$ENV_FILE" ]; then
  echo "ERROR: $ENV_FILE file not found"
  echo "Create $ENV_FILE with test Discord credentials"
  echo "See TESTING_E2E.md for setup instructions"
  exit 1
fi

# Source env file to check required variables
source "$ENV_FILE"

# Check for required test Discord credentials
if [ -z "$DISCORD_TOKEN" ]; then
  echo "ERROR: DISCORD_TOKEN environment variable is required in $ENV_FILE"
  echo "See TESTING_E2E.md for setup instructions"
  exit 1
fi

if [ -z "$DISCORD_GUILD_ID" ] || [ -z "$DISCORD_CHANNEL_ID" ]; then
  echo "WARNING: DISCORD_GUILD_ID and DISCORD_CHANNEL_ID should be set in $ENV_FILE"
  echo "Tests may fail without these. See TESTING_E2E.md for setup instructions"
fi

echo "Building end-to-end test container..."
docker compose --env-file "$ENV_FILE" build e2e-tests init

cleanup() {
  echo "Cleaning up e2e test environment..."
  docker compose --env-file "$ENV_FILE" down -v
}

trap cleanup EXIT

echo "Running e2e tests..."
if [ $# -eq 0 ]; then
  # Use marker-based selection (command from compose.e2e.yaml: -m e2e -v --tb=short)
  docker compose --env-file "$ENV_FILE" run --rm e2e-tests
else
  # User specified args - pass them through
  docker compose --env-file "$ENV_FILE" run --rm e2e-tests "$@"
fi

echo "End-to-end tests passed!"
