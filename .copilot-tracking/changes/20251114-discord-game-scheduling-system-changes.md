<!-- markdownlint-disable-file -->

# Release Changes: Discord Game Scheduling System

**Related Plan**: 20251114-discord-game-scheduling-system-plan.instructions.md
**Implementation Date**: 2025-11-14

## Summary

Implementation of a complete Discord game scheduling system with microservices architecture, featuring Discord bot with button interactions, web dashboard with OAuth2 authentication, role-based authorization, multi-channel support with settings inheritance, and automated notifications.

## Changes

### Added

- docker-compose.yml - Multi-service orchestration with PostgreSQL, RabbitMQ, Redis, bot, api, and scheduler services
- .env.example - Environment variable template with Discord, database, and service configurations
- docker/bot.Dockerfile - Multi-stage Docker image for Discord bot service with security best practices
- docker/api.Dockerfile - Multi-stage Docker image for FastAPI web service with health checks
- docker/scheduler.Dockerfile - Multi-stage Docker image for Celery worker and beat services
- docker/postgres/init.sql - PostgreSQL initialization script with UUID extension
- pyproject.toml - Python project configuration with all required dependencies for microservices including psycopg2-binary
- src/shared/**init**.py - Shared package initialization with schemas and utils exports
- src/shared/models/**init**.py - SQLAlchemy models export with Base class
- src/shared/models/base.py - SQLAlchemy declarative base class for all models
- src/shared/models/user.py - User model with Discord ID and UTC timestamps
- src/shared/models/guild.py - GuildConfiguration model with inheritance settings
- src/shared/models/channel.py - ChannelConfiguration model with channel-specific overrides
- src/shared/models/game.py - GameSession model with status tracking and relationships
- src/shared/models/participant.py - GameParticipant model with nullable user_id for placeholders
- alembic.ini - Alembic configuration for database migrations with PostgreSQL connection
- alembic/env.py - Alembic environment setup with model imports and Base metadata
- alembic/versions/bfa73f1adefc_initial_schema.py - Initial database migration with all tables and constraints
- src/bot/main.py - Discord bot service main module with placeholder implementation
- src/api/main.py - FastAPI web service with health check and root endpoints
- src/scheduler/celery_app.py - Celery application configuration with RabbitMQ and Redis
- src/scheduler/tasks.py - Celery tasks for notifications and background processing
- README.md - Project documentation with setup instructions and service information
- src/shared/messaging/**init**.py - Messaging package initialization with all exports
- src/shared/messaging/config.py - RabbitMQ connection management with health checks and auto-reconnect
- src/shared/messaging/events.py - Event schema definitions with Pydantic models and factory functions
- src/shared/messaging/publisher.py - Event publishing client with persistent messaging and correlation IDs
- src/shared/messaging/consumer.py - Event consumption framework with handlers and auto-registration
- rabbitmq/definitions.json - RabbitMQ queue and exchange definitions with dead letter queues
- src/shared/cache/**init**.py - Cache package initialization with client, keys, and TTL exports
- src/shared/cache/client.py - Async Redis client wrapper with connection pooling and error handling
- src/shared/cache/keys.py - Centralized cache key patterns for consistent naming across services
- src/shared/cache/ttl.py - TTL configuration constants with cache tier classification
- src/shared/schemas/**init**.py - Pydantic schemas package initialization with all schema exports
- src/shared/schemas/auth.py - Authentication schemas for OAuth2 login, user info, and guild information
- src/shared/schemas/game.py - Game management schemas for create, update, response, and join operations
- src/shared/schemas/guild_config.py - Guild and channel configuration schemas with inheritance support
- src/shared/schemas/participant.py - Participant schemas for validation errors and suggestions
- src/shared/utils/**init**.py - Utility modules package initialization
- src/shared/utils/timezone.py - UTC timezone handling utilities with Discord timestamp formatting
- src/shared/utils/discord.py - Discord API helpers for user resolution and permission checking

**Fixes Applied:**

- Fixed Docker build issues by removing uv.lock dependency and adding README.md to build context
- Fixed PYTHONPATH configuration in all Dockerfiles for proper module resolution
- Fixed file permissions on source directories (755) for Docker container access
- Removed Docker Compose version field (obsolete in v2)
- Disabled uvicorn --reload to avoid permission issues with file watchers
- Fixed PostgreSQL init script permissions

**Verification Results:**

- ✅ All infrastructure services healthy (PostgreSQL, RabbitMQ, Redis)
- ✅ API service healthy and accessible at http://localhost:8000
- ✅ API documentation available at http://localhost:8000/docs
- ✅ RabbitMQ management UI accessible at http://localhost:15672
- ✅ Celery worker and beat scheduler services healthy
- ✅ All services can communicate via internal network
- ✅ Database connections working properly
- .python-version - Python 3.11 version specification for uv package manager
- tests/**init**.py - Test configuration package initialization
- tests/test_basic.py - Basic pytest functionality and Python version validation tests

### Modified

- pyproject.toml - Updated Python tooling configuration replacing black/isort/flake8 with ruff for linting and formatting, added proper pytest configuration with coverage, updated dependency groups for uv compatibility

### Removed
