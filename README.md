# Game Scheduler

A Discord game scheduling system with microservices architecture, featuring Discord bot with button interactions, web dashboard with OAuth2 authentication, role-based authorization, multi-channel support, and automated notifications.

## Features

- Discord bot with button interactions for joining/leaving games
- Web dashboard for game creation and management
- Discord OAuth2 authentication with role-based authorization
- Multi-channel support with hierarchical settings inheritance
- Automated notifications before games start
- Display name resolution for guild-specific names
- Pre-populated participants with @mention validation

## Architecture

Microservices architecture with:

- **Discord Bot Service**: Handles Discord Gateway interactions and sends notifications to participants
- **Web API Service**: FastAPI REST API for web dashboard and game management
- **Notification Daemon**: Database-backed event-driven scheduler for game reminders
- **Scheduler Service**: Celery workers for periodic background jobs (game status updates)
- **PostgreSQL**: Primary data store with LISTEN/NOTIFY for real-time events
- **RabbitMQ**: Message broker for inter-service communication
- **Redis**: Caching and session storage

### Notification System

The notification system uses a database-backed event-driven architecture for reliable, scalable game reminders:

1. **Schedule Population**: When games are created or updated, notification schedules are stored in the `notification_schedule` table
2. **Event-Driven Wake-ups**: PostgreSQL LISTEN/NOTIFY triggers instant scheduler wake-ups when schedules change
3. **MIN() Query Pattern**: Daemon queries for the next due notification using an optimized O(1) query with partial index
4. **RabbitMQ Events**: When notifications are due, events are published to RabbitMQ for the bot service to process
5. **Persistence**: All scheduled notifications survive service restarts via database storage

**Key Features**:

- Unlimited notification windows (supports scheduling weeks/months in advance)
- Sub-10 second notification latency with event-driven wake-ups
- Zero data loss on restarts - all state persisted in database
- Self-healing - single MIN() query resumes processing after restart
- Scalable - O(1) query performance regardless of total scheduled games

## Development Setup

1. Copy environment template:

```bash
cp .env.example .env
```

2. Update `.env` with your Discord bot credentials

3. Start all services:

```bash
docker compose --env-file .env up
```

4. Access services:

- API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- RabbitMQ Management: http://localhost:15672

5. Monitor notification daemon:

```bash
# View notification daemon logs
docker compose logs -f notification-daemon

# Restart notification daemon
docker compose restart notification-daemon
```

## Running Services Individually

Start specific services for development:

```bash
# Start infrastructure only
docker compose up -d postgres rabbitmq redis

# Run database migrations
docker compose run --rm api alembic upgrade head

# Start notification daemon
docker compose up -d notification-daemon

# Start API service
docker compose up -d api

# Start Discord bot
docker compose up -d bot
```

## Building Multi-Architecture Images

The project supports building images for both ARM64 (Apple Silicon, AWS Graviton) and AMD64 (traditional x86) architectures using Docker Bake.

### Setup

Create a multi-platform builder (one-time setup):

```bash
# Check existing builders
docker buildx ls

# Create and use multi-platform builder
docker buildx create --use
```

### Building and Pushing Images

Build for multiple architectures and push to registry:

```bash
# Build all services for both architectures and push
docker buildx bake --push

# Build specific service(s)
docker buildx bake --push api bot

# Build with custom registry and tag
IMAGE_REGISTRY=myregistry.com/ IMAGE_TAG=v1.2.3 docker buildx bake --push

# Build without registry prefix (empty string)
IMAGE_REGISTRY= IMAGE_TAG=dev docker buildx bake --push
```

### Local Development Builds

For local development (single platform, no push):

```bash
# Regular docker compose build (single platform)
docker compose --env-file .env build

# Build for specific platform
docker compose --env-file .env build --build-arg BUILDPLATFORM=linux/amd64
```

### Environment Variables

Configure in `.env` file:

- `IMAGE_REGISTRY`: Docker registry URL prefix (include trailing slash)
  - Default: `172-16-1-24.xip.boneheads.us:5050/`
  - Examples: `docker.io/myorg/`, empty for local
- `IMAGE_TAG`: Image tag for built containers
  - Default: `latest`
  - Examples: `v1.0.0`, `dev`, `staging`

## Project Structure

```
.
├── services/
│   ├── bot/                    # Discord bot service
│   ├── api/                    # FastAPI web service
│   └── scheduler/              # Background jobs and notification daemon
│       ├── notification_daemon.py   # Event-driven notification scheduler
│       ├── postgres_listener.py     # PostgreSQL LISTEN/NOTIFY client
│       ├── schedule_queries.py      # Notification schedule queries
│       └── tasks/              # Celery periodic tasks
├── shared/                     # Shared models and utilities
│   └── models/
│       └── notification_schedule.py # Notification schedule model
├── docker/                     # Dockerfiles for each service
├── alembic/                    # Database migrations
├── docker-compose.base.yml     # Shared service definitions
├── docker-compose.yml          # Development environment
├── docker-compose.integration.yml  # Integration test environment
└── docker-compose.e2e.yml      # E2E test environment
```

## Docker Compose Architecture

The project uses a layered Docker Compose structure to minimize duplication:

- **`docker-compose.base.yml`**: Shared service definitions (images, healthchecks, dependencies)
- **`docker-compose.yml`**: Development environment overrides (persistent volumes, exposed ports)
- **`docker-compose.integration.yml`**: Integration test environment (postgres, rabbitmq, redis only)
- **`docker-compose.e2e.yml`**: E2E test environment (full stack with Discord bot)

This design ensures all environments stay in sync while allowing environment-specific configurations. See [TESTING_E2E.md](TESTING_E2E.md) for testing details.

## License

Copyright 2025 Bret McKee (bret.mckee@gmail.com)

Game Scheduler is available as open source software, see COPYING.txt for
information on the license. 

Please contact the author if you are interested in obtaining it under other
terms.
