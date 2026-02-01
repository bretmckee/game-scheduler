# Docker Deployment Guide

Comprehensive guide for deploying Game Scheduler with Docker and Docker Compose.

## Overview

Game Scheduler uses Docker containers orchestrated by Docker Compose for consistent, reproducible deployments across all environments (development, test, staging, production).

## Requirements

- **Docker**: 24.0+ with BuildKit enabled
- **Docker Compose**: 2.20+
- **Git**: For repository checkout and version management

## Port Exposure Strategy

Services communicate via internal Docker network (`app-network`) by default. Port exposure to host is environment-specific and follows principle of least privilege.

### Port Exposure by Environment

#### Base Configuration (`compose.yaml`)

**NO ports exposed to host**

- Infrastructure services (postgres, rabbitmq, valkey) expose no ports
- Observability services (grafana-alloy) expose no ports
- All services communicate via internal Docker network

#### Development (`compose.override.yaml`)

**Application ports + management UI**

- Frontend: `localhost:3000` (configurable via `FRONTEND_HOST_PORT`)
- API: `localhost:8000` (configurable via `API_HOST_PORT`)
- RabbitMQ Management UI: `localhost:15672` (configurable via `RABBITMQ_MGMT_HOST_PORT`)

#### Test (`compose.e2e.yaml`, `compose.int.yaml`)

**Application ports only**

- Frontend: `localhost:3000` (configurable via `FRONTEND_HOST_PORT`)
- API: `localhost:8000` (configurable via `API_HOST_PORT`)

#### Production (`compose.prod.yaml`)

**NO ports exposed to host**

- Reverse proxy handles external routing
- Maximum security with minimal attack surface

### Configuration Variables

Define these in your `.env` file to customize port mappings:

| Variable | Default | Environments | Description |
|----------|---------|--------------|-------------|
| `API_HOST_PORT` | `8000` | dev, test | API port on host |
| `FRONTEND_HOST_PORT` | `3000` | dev, test | Frontend port on host |
| `RABBITMQ_MGMT_HOST_PORT` | `15672` | dev only | RabbitMQ management UI port |

### Benefits

**Security:**
- Minimized attack surface (infrastructure services not accessible from host)
- Production environment has zero exposed ports
- Reduced risk of unauthorized access

**Port Conflicts:**
- Multiple environments (dev, test, production) can run simultaneously
- No conflicts between environments
- Each environment exposes only the ports it needs

**Debugging:**
- `docker exec` provides secure, direct access to infrastructure services
- No need to expose ports for debugging
- Management UIs available in development when needed

## Debugging Infrastructure Services

Infrastructure service ports (postgres, valkey, rabbitmq data) are NOT exposed to host in any environment.

### PostgreSQL

```bash
# Access psql CLI
docker compose exec postgres psql -U gamebot -d game_scheduler

# Run SQL query
docker compose exec postgres psql -U gamebot -d game_scheduler -c "SELECT * FROM games LIMIT 5;"

# Database backup
docker compose exec postgres pg_dump -U gamebot game_scheduler > backup.sql

# Database restore
docker compose exec -T postgres psql -U gamebot -d game_scheduler < backup.sql
```

### Valkey (Redis-compatible cache)

```bash
# Access valkey-cli
docker compose exec redis valkey-cli

# Check specific key
docker compose exec redis valkey-cli GET some_key

# Monitor commands
docker compose exec redis valkey-cli MONITOR

# Flush all keys (development only!)
docker compose exec redis valkey-cli FLUSHALL
```

### RabbitMQ

#### CLI Management

```bash
# Check status
docker compose exec rabbitmq rabbitmqctl status

# List queues
docker compose exec rabbitmq rabbitmqctl list_queues

# List exchanges
docker compose exec rabbitmq rabbitmqctl list_exchanges

# List connections
docker compose exec rabbitmq rabbitmqctl list_connections

# Purge specific queue (caution: data loss!)
docker compose exec rabbitmq rabbitmqctl purge_queue bot_events.dlq
```

#### Management UI (Development Only)

Access http://localhost:15672 in browser

- **Username**: Value of `RABBITMQ_DEFAULT_USER` (default: `gamebot`)
- **Password**: Value of `RABBITMQ_DEFAULT_PASS` (default: `dev_password_change_in_prod`)

## Build Cache Optimization

BuildKit cache mounts eliminate duplicate package downloads across services and dramatically reduce build times.

### How It Works

**Cache Mount Behavior:**
- **Persistent**: Cache survives across builds and rebuilds
- **Configurable Sharing**: Choose between `private` (parallel) or `locked` (serialized) modes
- **Automatic**: BuildKit manages cache size and eviction

**Cache Locations:**
- `/var/cache/apt` - Downloaded .deb files
- `/var/lib/apt` - Package metadata
- `/root/.cache/pip` - pip cache
- `/root/.cache/uv` - uv cache

### Cache Sharing Modes

Control cache sharing via environment variable:

```bash
# Default: private mode (parallel builds, more disk space)
docker compose build

# Override: locked mode (serialized builds, less disk space, better for limited bandwidth)
CACHE_SHARING_MODE=locked docker compose build
```

**Private Mode (default):**
- ✅ Parallel builds work without waiting
- ✅ Best for good network bandwidth
- ⚠️ Uses more disk space (separate cache per service)

**Locked Mode:**
- ✅ Minimal disk usage (shared cache)
- ✅ Best for limited network bandwidth
- ⚠️ Services wait for cache access (serialized builds)

### Expected Benefits

**Before cache mounts:**
- Each service independently downloads packages (~11.4s per service)
- Total ~45+ seconds wasted across services in parallel builds
- No cache sharing between services
- Python packages downloaded separately for each service

**After cache mounts:**
- First build: Downloads packages once, stores in persistent cache
- Subsequent builds: Reuses cached packages across ALL services
- Only downloads new or changed packages
- Expected build time reduction: **50-70%** for incremental builds

### Testing Cache Optimization

Verify the optimization:

```bash
# Clean all Docker build cache
docker builder prune -af

# First build (will populate cache)
time docker compose build

# Second build (should be much faster)
time docker compose build

# Or build a single service
time docker compose build api
```

### Cache Maintenance

**Clearing cache mounts:**
```bash
docker builder prune --filter type=exec.cachemount
```

**Monitoring cache size:**
```bash
docker system df -v
```

## Version Management

Game Scheduler uses `setuptools-scm` for automatic versioning from git tags.

### How It Works

1. Docker mounts `.git` directory during build (read-only, not copied into image)
2. setuptools-scm reads git metadata during `pip install`
3. Version is embedded in installed package
4. Python code reads it via `importlib.metadata.version()`

No manual steps, no environment variables, no version files to maintain!

### Building with Automatic Versioning

```bash
# Version is automatically extracted from git
docker compose build api
docker compose up
```

setuptools-scm automatically:
- Reads git tags
- Counts commits since last tag
- Adds commit hash
- Handles dirty working directory

### Accessing Version Information

**API endpoints:**
- Version endpoint: `/api/v1/version`
- Health endpoint: `/health`

**Example response:**
```json
{
  "service": "api",
  "git_version": "0.0.1.dev478+gd128f6a",
  "api_version": "1.0.0",
  "api_prefix": "/api/v1"
}
```

**Web interface:**
- Navigate to About page in top navigation
- Displays version, copyright, and license information

### Git Tagging Strategy

setuptools-scm works with standard semantic versioning tags:

```bash
# Create release tag
git tag v1.0.0
git push origin v1.0.0

# Development versions are automatically numbered
# After v1.0.0, commits automatically become:
# v1.0.0-1-gABCDEF (1 commit after v1.0.0)
# v1.0.0-2-gXYZ123 (2 commits after v1.0.0)
```

**Version format:**
- Clean tag: `1.0.0`
- Development: `1.0.1.dev5+gd128f6a` (5 commits after v1.0.0)
- Dirty: `1.0.1.dev5+gd128f6a.d20251227` (with uncommitted changes)

### Troubleshooting Version Management

**Version shows "0.0.0+unknown":**
- **Cause**: No git tags in repository
- **Solution**: Create first tag: `git tag v0.1.0`

**Version shows "dev-unknown":**
- **Cause**: Package not installed (running without Docker)
- **Solution**: Expected in development. Build with Docker for proper version.

**Git mount fails in Docker:**
- **Cause**: .git directory not accessible or BuildKit not enabled
- **Solution**: Ensure Docker BuildKit is enabled: `export DOCKER_BUILDKIT=1`

## Observability Architecture

### Grafana Alloy (OpenTelemetry Collector)

Services send telemetry to Grafana Alloy via internal Docker network:

- **OTLP gRPC**: `grafana-alloy:4317`
- **OTLP HTTP**: `grafana-alloy:4318`

Alloy forwards telemetry to Grafana Cloud. No external port exposure needed.

### RabbitMQ Prometheus Metrics

Alloy scrapes RabbitMQ Prometheus metrics internally from `rabbitmq:15692`. Metrics port not exposed to host.

## Common Docker Operations

### Building Images

```bash
# Build all services
docker compose build

# Build specific service
docker compose build api

# Force rebuild without cache
docker compose build --no-cache api

# Build with specific environment file
docker compose --env-file config/env/env.prod.local build
```

### Starting Services

```bash
# Start all services in foreground
docker compose up

# Start all services in background
docker compose up -d

# Start with specific environment file
docker compose --env-file config/env/env.prod.local up -d

# Start specific service
docker compose up -d api
```

### Viewing Logs

```bash
# View all service logs
docker compose logs -f

# View specific service logs
docker compose logs -f api bot

# View last 100 lines
docker compose logs --tail=100 -f api
```

### Stopping Services

```bash
# Stop all services (keep containers)
docker compose stop

# Stop and remove containers
docker compose down

# Stop and remove containers, volumes, and networks
docker compose down -v

# Stop with specific environment file
docker compose --env-file config/env/env.prod.local down
```

### Restarting Services

```bash
# Restart all services
docker compose restart

# Restart specific service
docker compose restart api

# Restart with specific environment file
docker compose --env-file config/env/env.prod.local restart frontend
```

### Service Health

```bash
# Check service status
docker compose ps

# Check container health
docker compose ps -a

# View resource usage
docker stats
```

## Migration Notes

If you previously accessed infrastructure services directly via localhost:

- **PostgreSQL** (`localhost:5432`) → Use `docker compose exec postgres psql -U gamebot -d game_scheduler`
- **Valkey** (`localhost:6379`) → Use `docker compose exec redis valkey-cli`
- **RabbitMQ** (`localhost:5672`) → Services use `rabbitmq:5672` internally
- **RabbitMQ Management** (`localhost:15672`) → Available in development mode only

## See Also

- [Deployment Quick Start](quickstart.md) - Step-by-step deployment guide
- [Configuration Guide](configuration.md) - Runtime configuration options
- [Gateway README](README.md) - Deployment overview and security considerations
