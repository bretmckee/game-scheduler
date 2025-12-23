"""
Test that keeps E2E environment running for debugging.

Run with: ./scripts/run-e2e-tests.sh -k test_keep_alive_for_debugging

To exit: touch /tmp/e2e_exit_signal

While running, you can:
- docker compose --env-file env/env.e2e exec api bash
- docker compose --env-file env/env.e2e logs -f api
- Run manual API calls with curl/httpx
"""

import asyncio
from pathlib import Path

import pytest


@pytest.mark.skip(reason="Manual debugging test - run explicitly with -k test_keep_alive")
@pytest.mark.asyncio
async def test_keep_alive_for_debugging(authenticated_admin_client, discord_guild_id, api_base_url):
    """Keep E2E environment alive for manual testing."""
    exit_file = Path("/tmp/e2e_exit_signal")

    # Remove exit file if it exists from previous run
    exit_file.unlink(missing_ok=True)

    print("\n" + "=" * 70)
    print("E2E ENVIRONMENT IS RUNNING")
    print("=" * 70)
    print(f"\nAPI URL: {api_base_url}")
    print(f"Guild ID: {discord_guild_id}")
    print(f"Session token: {authenticated_admin_client.cookies.get('session_token')}")
    print("\nCommands you can run:")
    print("  - View logs:")
    print("    docker compose --env-file env/env.e2e logs -f api")
    print("\n  - Execute in API container:")
    print("    docker compose --env-file env/env.e2e exec api bash")
    print("\n  - Test sync endpoint:")
    print("    docker compose --env-file env/env.e2e exec api curl \\")
    print("      -X POST http://localhost:8000/api/v1/guilds/sync \\")
    print("      -H 'Cookie: session_token=<token>'")
    print(f"\nTo exit this test: touch {exit_file}")
    print("=" * 70 + "\n")

    iteration = 0
    while not exit_file.exists():
        iteration += 1
        if iteration % 6 == 1:  # Print every minute
            print(f"[{iteration * 10}s] Waiting for exit signal at {exit_file}")
        await asyncio.sleep(10)

    print(f"\n✓ Exit signal detected at {exit_file}")
    print("Cleaning up...")
    exit_file.unlink(missing_ok=True)
