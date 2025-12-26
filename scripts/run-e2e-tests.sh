#!/bin/bash
# Run end-to-end tests in isolated Docker environment
# These tests verify the complete notification flow including Discord bot interactions
#
# REQUIRED: Set up test Discord bot and guild first (see TESTING_E2E.md)

set -e

# Check for config/env/env.e2e file
if [ ! -f config/env/env.e2e ]; then
  echo "ERROR: config/env/env.e2e file not found"
  echo "Create config/env/env.e2e with test Discord credentials"
  echo "See TESTING_E2E.md for setup instructions"
  exit 1
fi

# Source config/env/env.e2e to check required variables
source config/env/env.e2e

# Check for required test Discord credentials
if [ -z "$DISCORD_TOKEN" ]; then
  echo "ERROR: DISCORD_TOKEN environment variable is required in config/env/env.e2e"
  echo "See TESTING_E2E.md for setup instructions"
  exit 1
fi

if [ -z "$DISCORD_GUILD_ID" ] || [ -z "$DISCORD_CHANNEL_ID" ]; then
  echo "WARNING: DISCORD_GUILD_ID and DISCORD_CHANNEL_ID should be set in config/env/env.e2e"
  echo "Tests may fail without these. See TESTING_E2E.md for setup instructions"
fi

echo "Building end-to-end test container..."
docker compose --env-file config/env/env.e2e build e2e-tests init

cleanup() {
  echo "Cleaning up end-to-end test environment..."
  docker compose --env-file config/env/env.e2e down -v
}

trap cleanup EXIT

echo "Running end-to-end tests..."
if [ $# -eq 0 ]; then
  # Use marker-based selection (command from compose.e2e.yaml: -m e2e -v --tb=short)
  docker compose --env-file config/env/env.e2e run --rm e2e-tests
else
  # User specified args - pass them through
  docker compose --env-file config/env/env.e2e run --rm e2e-tests "$@"
fi

echo "End-to-end tests passed!"
