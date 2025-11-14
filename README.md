# Discord Game Scheduling System

A microservices-based Discord game scheduling system with bot interactions, web dashboard, and automated notifications.

## Architecture

- **Discord Bot Service**: Handles Discord Gateway interactions, slash commands, and button interactions
- **Web API Service**: FastAPI REST API for web dashboard with Discord OAuth2 authentication
- **Scheduler Service**: Celery workers for background tasks and notifications
- **PostgreSQL**: Primary data store
- **RabbitMQ**: Message broker for inter-service communication
- **Redis**: Cache and Celery result backend

## Quick Start

1. **Clone and setup environment**:

   ```bash
   cp .env.example .env
   # Edit .env with your Discord application credentials
   ```

2. **Start all services**:

   ```bash
   docker-compose up -d
   ```

3. **Check service health**:
   ```bash
   docker-compose ps
   ```

## Service Endpoints

- **Web API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **RabbitMQ Management**: http://localhost:15672 (guest/guest)
- **PostgreSQL**: localhost:5432
- **Redis**: localhost:6379

## Development

### Requirements

- Docker Engine 24+
- Docker Compose v2+

### Services

- **bot**: Discord bot service (discord.py)
- **api**: Web API service (FastAPI)
- **scheduler**: Celery worker service
- **scheduler-beat**: Celery beat scheduler
- **postgres**: PostgreSQL database
- **rabbitmq**: RabbitMQ message broker
- **redis**: Redis cache

### Logs

```bash
# View all service logs
docker-compose logs -f

# View specific service logs
docker-compose logs -f bot
docker-compose logs -f api
docker-compose logs -f scheduler
```

### Stopping Services

```bash
# Stop all services
docker-compose down

# Stop and remove volumes
docker-compose down -v
```

## Configuration

All configuration is handled via environment variables. See `.env.example` for all available options.

### Required Discord Setup

1. Create a Discord Application at https://discord.com/developers/applications
2. Create a bot and copy the Bot Token
3. Copy the Application Client ID and Client Secret
4. Set the OAuth2 redirect URI to match your API configuration

## Health Checks

All services include health checks:

- **postgres**: `pg_isready`
- **rabbitmq**: `rabbitmq-diagnostics ping`
- **redis**: `redis-cli ping`
- **api**: HTTP GET `/health`
- **bot**: Discord Gateway connectivity check
- **scheduler**: Celery worker ping
