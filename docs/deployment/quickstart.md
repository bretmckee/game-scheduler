# Deployment Quick Start

## Setting Up on a New Server

### 1. Configure Your Environment

Copy the appropriate environment template from `config/env/` directory. For production, use `env.prod`:

```bash
# Copy production environment template
cp config/env/env.prod config/env/env.prod.local
```

Edit `config/env/env.prod.local` and set:

```bash
# Leave BACKEND_URL set to your actual domain/IP
# Both bot and frontend use this URL
BACKEND_URL=https://your-domain.com

# Set to your actual frontend URL
FRONTEND_URL=http://your-server-ip:3000

# Set your Discord credentials
DISCORD_BOT_TOKEN=your_bot_token
DISCORD_CLIENT_SECRET=your_client_secret

# Change default passwords!
POSTGRES_PASSWORD=change_me
```

### 2. Build and Start

**Important:** For production, use the production environment file with `--env-file`:

```bash
# Build production images (targets production stage)
docker compose --env-file config/env/env.prod.local build

# Start production services
docker compose --env-file config/env/env.prod.local up -d
```

**How Environment Files Control Configuration:**

Each environment file (in `config/env/` directory) contains a `COMPOSE_FILE` variable that specifies which compose files to load:

- **Production** (`config/env/env.prod`):
  - `COMPOSE_FILE=compose.yaml` (base configuration only)
  - Uses `production` stage from Dockerfiles
  - Source code baked into images
  - INFO logging level
  - No port mappings (use reverse proxy)
  - Includes restart policies

- **Staging** (`config/env/env.staging`):
  - `COMPOSE_FILE=compose.yaml:compose.staging.yaml`
  - Production builds with DEBUG logging
  - Exposes frontend and API ports
  - Restart policies enabled

- **Development** (`config/env/env.dev`, auto-loaded via `.env` symlink):
  - `COMPOSE_FILE=compose.yaml:compose.override.yaml`
  - Uses `development` stage from Dockerfiles
  - Source code mounted as volumes
  - DEBUG logging level
  - All ports exposed including management UIs
  - Hot-reload enabled
  - No restart policies

The init container will:

1. Run database migrations
2. Complete before application services start

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
docker compose --env-file config/env/env.prod.local build
docker compose --env-file config/env/env.prod.local up -d
```

### Viewing Logs

```bash
# View all service logs
docker compose --env-file config/env/env.prod.local logs -f

# View specific service logs
docker compose --env-file config/env/env.prod.local logs -f api
docker compose --env-file config/env/env.prod.local logs -f bot
```

### Restarting Services

```bash
# Restart all services
docker compose --env-file config/env/env.prod.local restart

# Restart specific service
docker compose --env-file config/env/env.prod.local restart api
```

## Changing the API URL Later

No rebuild needed! Just update your environment file and restart the frontend:

```bash
# Edit your environment file and change BACKEND_URL
nano config/env/env.prod.local

# Restart only the frontend container
docker compose --env-file config/env/env.prod.local restart frontend
```

See [configuration.md](configuration.md) for more details.

## Using Different Hostnames/IPs

The configuration now requires `BACKEND_URL` to be set to your actual domain:

- Access via `http://localhost:3000` → `BACKEND_URL=http://localhost:8000`
- Access via `http://192.168.1.100:3000` → `BACKEND_URL=http://192.168.1.100:8000`
- Access via `https://your-domain.com` → `BACKEND_URL=https://your-domain.com`

The BACKEND_URL must match how you access the server.

**How it works:**

1. User accesses: `https://your-server`
2. Frontend makes requests to: `https://your-server/api/v1/...` (same origin)
3. Nginx proxies internally to: `http://api:8000/api/v1/...` (Docker network)
4. Bot generates image URLs: `https://your-server/api/v1/games/{id}/image`

Both frontend and bot use the same `BACKEND_URL` value.

## Configuration Notes

**Standard deployment (everything on one server):**

```bash
# Frontend and API accessed via same domain
FRONTEND_URL=https://example.com
BACKEND_URL=https://example.com
```

**Split deployment (API on different domain):**

```bash
# Frontend at one domain, API at another
FRONTEND_URL=https://game.example.com
BACKEND_URL=https://api.example.com
```

## Infrastructure Initialization

The init container automatically sets up:

- **Database:** Runs all Alembic migrations to create/update schema

This happens automatically on first startup.

## Credentials and Security

**Important:** Change all default passwords in your environment file before deployment:

```bash
# Edit your production environment file
nano config/env/env.prod.local

# Update these critical values:
# Database password
POSTGRES_PASSWORD=use_a_strong_random_password

# Discord credentials
DISCORD_CLIENT_SECRET=from_discord_developer_portal
```

**Note:** These variables control runtime configuration without requiring image rebuilds.
