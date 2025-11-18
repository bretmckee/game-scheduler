#!/usr/bin/env python3
"""
Simple script to test Discord OAuth2 authentication flow.

This script will:
1. Call the /login endpoint to get an authorization URL
2. Open the URL in your browser for Discord authentication
3. Display instructions for completing the flow

Make sure the API service is running at http://localhost:8000
"""

import webbrowser

import httpx


def test_oauth_flow():
    """Test the OAuth2 authentication flow."""
    api_base = "http://localhost:8000"
    redirect_uri = "http://localhost:8000/api/v1/auth/callback"

    print("🔐 Testing Discord OAuth2 Authentication Flow\n")
    print("=" * 60)

    # Step 1: Get authorization URL
    print("\n1️⃣  Calling /api/v1/auth/login endpoint...")
    try:
        response = httpx.get(
            f"{api_base}/api/v1/auth/login",
            params={"redirect_uri": redirect_uri},
        )
        response.raise_for_status()
        data = response.json()

        auth_url = data["authorization_url"]
        state = data["state"]

        print("   ✅ Success! Received authorization URL")
        print(f"   State token: {state[:20]}...")

    except httpx.HTTPError as e:
        print(f"   ❌ Error calling login endpoint: {e}")
        print("\n   Make sure the API is running: uv run python -m services.api.main")
        return

    # Step 2: Open browser
    print("\n2️⃣  Opening Discord authorization page in your browser...")
    print(f"   URL: {auth_url[:80]}...")
    webbrowser.open(auth_url)

    # Step 3: Instructions
    print("\n3️⃣  Complete the Discord authorization in your browser")
    print("   - Click 'Authorize' on the Discord page")
    print("   - You'll be redirected back to the callback URL")
    print("   - The callback will create a user record and store tokens")

    print("\n" + "=" * 60)
    print("\n📋 What happens next:")
    print("   1. Discord redirects to: http://localhost:8000/api/v1/auth/callback")
    print("   2. The callback endpoint exchanges the code for tokens")
    print("   3. User record created in database (if new user)")
    print("   4. Tokens encrypted and stored in Redis")
    print("   5. You'll see a redirect confirmation")

    print("\n🔍 To verify the login worked:")
    print("   - Check API logs for 'Created new user' or token storage messages")
    print("   - Check Redis: docker exec -it gamebot-redis redis-cli")
    print("   - Run: KEYS session:*")

    print("\n💡 To test the /user endpoint (after login):")
    print("   - You need to add X-User-Id header with your Discord user ID")
    print(
        "   - Example: curl -H 'X-User-Id: YOUR_DISCORD_ID' http://localhost:8000/api/v1/auth/user"
    )

    print("\n" + "=" * 60)


if __name__ == "__main__":
    test_oauth_flow()
