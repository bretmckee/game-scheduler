# Deployment Quick Start

## Setting Up on a New Server

### 1. Configure Your Environment

Copy `.env.example` to `.env` and configure it for your server:

```bash
cp .env.example .env
```

Edit `.env` and set:

```bash
# Leave API_URL empty to use nginx proxy (works with any hostname)
API_URL=

# Set to your actual frontend URL
FRONTEND_URL=http://your-server-ip:3000

# Configure Discord OAuth callback
DISCORD_REDIRECT_URI=http://your-server-ip:8000/api/v1/auth/callback

# Set your Discord credentials
DISCORD_BOT_TOKEN=your_bot_token
DISCORD_CLIENT_ID=your_client_id
DISCORD_CLIENT_SECRET=your_client_secret

# Change default passwords!
POSTGRES_PASSWORD=change_me
RABBITMQ_DEFAULT_PASS=change_me
RABBITMQ_URL=amqp://gamebot:change_me@rabbitmq:5672/
```

### 2. Build and Start

**Important:** For production, use the production compose configuration:

```bash
# Build production images (targets production stage)
docker compose -f compose.yml -f compose.production.yaml build

# Start production services
docker compose -f compose.yml -f compose.production.yaml up -d
```

**Production vs Development:**

- **Production** (`compose.production.yaml`):

  - Uses `production` stage from Dockerfiles
  - Source code baked into images
  - Optimized production commands
  - Includes restart policies
  - No volume mounts for code

- **Development** (`compose.override.yaml` - auto-loaded):
  - Uses `development` stage from Dockerfiles
  - Source code mounted as volumes
  - Hot-reload enabled
  - No restart policies
  - Instant code changes without rebuilds

The init container will:

1. Run database migrations
2. Initialize RabbitMQ infrastructure (exchanges, queues, bindings)
3. Complete before application services start

### 3. Verify

Check that all services are running:

```bash
docker compose ps
```

Access the frontend at `http://your-server-ip:3000`

## Managing Production Deployment

### Updating Code

For production deployments, rebuild images after code changes:

```bash
# Pull latest code
git pull

# Rebuild and restart services
docker compose -f compose.yml -f compose.production.yaml build
docker compose -f compose.yml -f compose.production.yaml up -d
```

### Viewing Logs

```bash
# View all service logs
docker compose logs -f

# View specific service logs
docker compose logs -f api
docker compose logs -f bot
```

### Restarting Services

```bash
# Restart all services
docker compose restart

# Restart specific service
docker compose restart api
```

## Changing the API URL Later

No rebuild needed! Just update `.env` and restart the frontend:

```bash
# Edit .env and change API_URL
nano .env

# Restart only the frontend container (works for both dev and production)
docker compose restart frontend
```

See [RUNTIME_CONFIG.md](RUNTIME_CONFIG.md) for more details.

## Using Different Hostnames/IPs

The default configuration (with `API_URL=` empty) uses nginx proxy mode, which
means:

- Access via `http://localhost:3000` - works ✓
- Access via `http://192.168.1.100:3000` - works ✓
- Access via `http://your-domain.com:3000` - works ✓

No configuration changes needed when accessing from different hostnames!

**How proxy mode works:**

1. User accesses: `http://your-server:3000`
2. Frontend makes requests to: `/api/v1/auth/user` (relative URL)
3. Nginx proxies internally to: `http://api:8000/api/v1/auth/user` (Docker
   network)

This is why `API_URL` can remain empty - the nginx proxy handles routing.

## When to Set API_URL

Only set `API_URL` if your API is on a **completely different server/domain**
than your frontend:

```bash
# Example: Frontend at https://game.example.com, API at https://api.example.com
API_URL=https://api.example.com
```

For the standard docker-compose deployment where both services run on the same
server, **leave API_URL empty**.

## Infrastructure Initialization

The init container automatically sets up:

- **Database:** Runs all Alembic migrations to create/update schema
- **RabbitMQ:** Creates exchanges, queues, and routing bindings

This happens automatically on first startup and ensures all services find
infrastructure ready.

## Credentials and Security

**Important:** Change all default passwords in `.env` before deployment:

```bash
# Database password
POSTGRES_PASSWORD=use_a_strong_random_password

# RabbitMQ password
RABBITMQ_DEFAULT_PASS=use_a_different_strong_password
RABBITMQ_URL=amqp://gamebot:use_a_different_strong_password@rabbitmq:5672/

# Discord credentials
DISCORD_CLIENT_SECRET=from_discord_developer_portal
```

**Note:** RabbitMQ credentials are set at runtime via environment variables. The
same container image works across all environments (dev, test, prod) with
different credentials.

## Migrating from Shared DLQ Architecture

**For existing deployments upgrading to the new per-queue DLQ architecture:**

### Overview of Changes

The new architecture replaces the shared "DLQ" queue with per-queue DLQs:

- **Old:** Single `DLQ` queue processed by multiple daemons (caused exponential growth)
- **New:** `bot_events.dlq` and `notification_queue.dlq` processed by dedicated retry-daemon

**Benefits:**
- Fixes DLQ exponential growth bug
- Clear ownership of retry logic
- Improved observability per queue type
- Eliminates duplicate message processing

### Pre-Migration Steps

1. **Check current DLQ depth:**
   ```bash
   docker compose exec rabbitmq rabbitmqctl list_queues name messages | grep DLQ
   ```

2. **Document any messages in DLQ:**
   - Access RabbitMQ Management UI at `http://localhost:15672`
   - Navigate to "Queues" → "DLQ"
   - Record message count and review message content if needed

3. **Optional - Drain old DLQ:**
   ```bash
   # Only if you want to discard current DLQ messages
   docker compose exec rabbitmq rabbitmqctl purge_queue DLQ
   ```

### Migration Procedure

1. **Pull latest code:**
   ```bash
   git pull
   ```

2. **Update environment variables in `.env`:**
   ```bash
   # Add retry service interval (optional, defaults to 900 seconds)
   RETRY_INTERVAL_SECONDS=900
   ```

3. **Rebuild services:**
   ```bash
   # For production
   docker compose -f compose.yml -f compose.production.yaml build

   # For development
   docker compose build
   ```

4. **Stop all services:**
   ```bash
   docker compose down
   ```

5. **Start services with new architecture:**
   ```bash
   # For production
   docker compose -f compose.yml -f compose.production.yaml up -d

   # For development
   docker compose up -d
   ```

6. **Verify new infrastructure created:**
   ```bash
   # Should show bot_events.dlq and notification_queue.dlq
   docker compose exec rabbitmq rabbitmqctl list_queues name messages | grep dlq
   ```

7. **Monitor retry-daemon logs:**
   ```bash
   docker compose logs -f retry-daemon
   ```

### Post-Migration Verification

1. **Check service health:**
   ```bash
   docker compose ps
   # All services should be "Up" and healthy
   ```

2. **Verify RabbitMQ queues:**
   - Access RabbitMQ Management UI
   - Confirm `bot_events.dlq` and `notification_queue.dlq` exist
   - Old "DLQ" queue should be gone or empty

3. **Monitor DLQ depth over time:**
   ```bash
   # Check periodically (every 15-30 minutes)
   docker compose exec rabbitmq rabbitmqctl list_queues name messages | grep dlq
   ```

4. **Confirm no exponential growth:**
   - DLQ message count should stay stable or decrease
   - If messages enter DLQ, they should be processed within 15 minutes

### Troubleshooting Migration

**Old DLQ queue still exists:**
```bash
# Manually delete if empty
docker compose exec rabbitmq rabbitmqctl delete_queue DLQ
```

**Retry-daemon not starting:**
```bash
# Check logs for errors
docker compose logs retry-daemon

# Common issues:
# - Missing RABBITMQ_URL environment variable
# - RabbitMQ not ready (wait 30 seconds and retry)
# - Port conflicts (check RETRY_INTERVAL_SECONDS is valid number)
```

**DLQ messages not being processed:**
```bash
# Verify retry-daemon is running
docker compose ps retry-daemon

# Check RabbitMQ connectivity
docker compose logs retry-daemon | grep -i "connection"

# Manually trigger processing by restarting
docker compose restart retry-daemon
```

### Rollback Procedure

If you need to rollback to the old architecture:

1. **Stop retry-daemon:**
   ```bash
   docker compose stop retry-daemon
   ```

2. **Checkout previous code version:**
   ```bash
   git checkout <previous-commit-hash>
   ```

3. **Rebuild and restart:**
   ```bash
   docker compose -f compose.yml -f compose.production.yaml build
   docker compose -f compose.yml -f compose.production.yaml up -d
   ```

4. **Verify old architecture restored:**
   - notification-daemon processes DLQ again
   - status-transition-daemon processes DLQ again
   - Shared "DLQ" queue exists

**Note:** After successful migration and verification, rollback should not be necessary.

### Additional Resources

For detailed information on DLQ monitoring and troubleshooting, see:
- [RUNTIME_CONFIG.md](RUNTIME_CONFIG.md#retry-service-dlq-processing) - Retry service configuration
- `grafana-alloy/dashboards/README.md` - DLQ monitoring dashboard

