# Testing the OAuth2 Authentication Flow

This guide will help you test the Discord OAuth2 authentication implementation.

## Prerequisites

1. **Discord Application Setup**

   - Go to https://discord.com/developers/applications
   - Click "New Application" and give it a name
   - Navigate to "OAuth2" → "General"
   - Copy your **Client ID** and **Client Secret**
   - Under "Redirects", add: `http://localhost:8000/api/v1/auth/callback`
   - Save changes

2. **Environment Configuration**
   ```bash
   # Update your .env file with:
   DISCORD_CLIENT_ID=your_actual_client_id
   DISCORD_CLIENT_SECRET=your_actual_client_secret
   FRONTEND_URL=http://localhost:3000
   BACKEND_URL=http://localhost:8000
   ```

## Starting the Services

```bash
# 1. Start infrastructure services
docker compose up -d postgres redis rabbitmq

# 2. Start the API service
uv run python -m services.api.main
```

The API should start on http://localhost:8000

## Testing Methods

### Method 1: Automated Test Script (Recommended)

Run the test script that will open your browser:

```bash
uv run python test_oauth.py
```

This will:

1. Call the `/login` endpoint
2. Open Discord authorization in your browser
3. Display helpful information about the flow

### Method 2: Manual Testing with curl

```bash
# Step 1: Get the authorization URL
curl "http://localhost:8000/api/v1/auth/login?redirect_uri=http://localhost:8000/api/v1/auth/callback"

# Response will contain:
# {
#   "authorization_url": "https://discord.com/api/oauth2/authorize?...",
#   "state": "random_state_token"
# }

# Step 2: Copy the authorization_url and open it in your browser
# Authorize the application

# Step 3: After authorization, you'll be redirected to the callback
# The callback URL will show "success=true" if it worked
```

### Method 3: API Documentation (FastAPI Swagger UI)

1. Open http://localhost:8000/docs in your browser
2. Find the `/api/v1/auth/login` endpoint under "auth" tag
3. Click "Try it out"
4. Enter redirect_uri: `http://localhost:8000/api/v1/auth/callback`
5. Click "Execute"
6. Copy the `authorization_url` from the response
7. Open that URL in your browser

## Verifying the Login

### Check API Logs

Look for these log messages:

```
INFO - Successfully exchanged authorization code for tokens
INFO - Fetched user info for Discord ID: 123456789
INFO - Created new user with Discord ID: 123456789  # (if new user)
INFO - Stored tokens for user 123456789
```

### Check Valkey Session Storage

```bash
# Connect to Valkey (Redis-compatible cache)
docker exec -it gamebot-redis valkey-cli

# List all sessions (now stored with UUID keys)
KEYS session:*

# Check a specific session (replace with UUID from cookie, not Discord ID)
GET session:abc-123-def-456-uuid

# You should see encrypted token data including user_id
```

Note: Session keys are now stored as `session:{uuid4}` instead of `session:{discord_id}` for security.

### Check Database

```bash
# Connect to PostgreSQL
docker exec -it gamebot-postgres psql -U scheduler game_scheduler

# Check users table
SELECT * FROM users;

# You should see your Discord ID
```

## Testing Additional Endpoints

Once you've logged in and received the session cookie, you can test other endpoints.

**Important**: The new secure implementation uses HTTPOnly cookies for authentication.
You'll need to use a browser or tool that supports cookies (like curl with `-b` flag to save/send cookies).

### Save the Session Cookie

After completing the OAuth2 flow in your browser:

```bash
# The browser automatically receives the session_token cookie
# To test with curl, you need to capture it during the callback
```

### Testing with curl and Cookies

```bash
# Step 1: Complete OAuth flow and save cookies
curl -c cookies.txt -L "http://localhost:8000/api/v1/auth/callback?code=YOUR_CODE&state=YOUR_STATE"

# Step 2: Use saved cookies for authenticated requests
curl -b cookies.txt http://localhost:8000/api/v1/auth/user
```

### Get User Info

```bash
# With cookie file
curl -b cookies.txt http://localhost:8000/api/v1/auth/user
```

Expected response:

```json
{
  "id": "123456789",
  "username": "YourUsername",
  "avatar": "avatar_hash_or_null",
  "guilds": [
    {
      "id": "guild_id",
      "name": "Server Name",
      "icon": "icon_hash",
      "owner": false,
      "permissions": "123456"
    }
  ]
}
```

### Refresh Token

```bash
# The cookie is sent automatically
curl -b cookies.txt -X POST http://localhost:8000/api/v1/auth/refresh
```

### Logout

```bash
# Clears the session and cookie
curl -b cookies.txt -c cookies.txt -X POST http://localhost:8000/api/v1/auth/logout
```

### Testing Security

The old X-User-Id header authentication has been removed for security:

```bash
# This will FAIL (returns 401 validation error for missing cookie)
curl -H "X-User-Id: 123456789" http://localhost:8000/api/v1/auth/user

# Response: {"error":"validation_error","field":"cookie.session_token"}
```

Only requests with valid session cookies are accepted.

## Troubleshooting

### "Invalid or expired state" Error

- State tokens expire after 10 minutes
- Start the flow again from the `/login` endpoint

### "Authentication failed" Error

- Check your Discord Client ID and Secret in `.env`
- Ensure the redirect URI matches exactly in Discord settings
- Check API logs for more details

### "Session not found" Error

- The user needs to login first via the OAuth2 flow
- Tokens may have expired (Redis TTL is 24 hours)

### Connection Errors

- Ensure Redis is running: `docker compose ps`
- Ensure PostgreSQL is running
- Check API service is running on port 8000

## Complete Flow Diagram

```
1. User → GET /api/v1/auth/login
   ↓
2. API returns authorization_url with state token
   ↓
3. User opens URL in browser → Discord authorization page
   ↓
4. User clicks "Authorize"
   ↓
5. Discord → GET /api/v1/auth/callback?code=XXX&state=YYY
   ↓
6. API validates state token (Redis)
   ↓
7. API exchanges code for access_token & refresh_token
   ↓
8. API fetches user info from Discord
   ↓
9. API creates/finds user in database
   ↓
10. API encrypts and stores tokens in Redis
    ↓
11. User redirected with success=true
```

## Security Notes

- State tokens are stored in Redis with 10-minute expiry (CSRF protection)
- Access and refresh tokens are encrypted with Fernet before storage
- Sessions expire after 24 hours (configurable via cache TTL)
- All communication with Discord uses HTTPS
- Tokens are never logged or exposed in responses

## Next Steps

After successful testing, you can:

1. Integrate with a frontend application
2. Test the role-based authorization (Task 3.3)
3. Create guild/channel configuration endpoints (Task 3.4)
4. Build the game management system (Task 3.5)
