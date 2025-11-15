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

- **Discord Bot Service**: Handles Discord Gateway interactions
- **Web API Service**: FastAPI REST API for web dashboard
- **Scheduler Service**: Celery workers for background jobs and notifications
- **PostgreSQL**: Primary data store
- **RabbitMQ**: Message broker for inter-service communication
- **Redis**: Caching and session storage

## Development Setup

1. Copy environment template:

```bash
cp .env.example .env
```

2. Update `.env` with your Discord bot credentials

3. Start all services:

```bash
docker-compose up
```

4. Access services:

- API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- RabbitMQ Management: http://localhost:15672

## Project Structure

```
.
├── services/
│   ├── bot/          # Discord bot service
│   ├── api/          # FastAPI web service
│   └── scheduler/    # Celery scheduler service
├── shared/           # Shared models and utilities
├── docker/           # Dockerfiles for each service
└── docker-compose.yml
```

## License

Copyright 2025 Bret McKee (bret.mckee@gmail.com)

Game Scheduler is available as open source software, see COPYING.txt for
information on the license. 

Please contact the author if you are interested in obtaining it under other
terms.
