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
- pyproject.toml - Python project configuration with all required dependencies for microservices
- src/shared/**init**.py - Shared package initialization for cross-service models and utilities
- src/bot/main.py - Discord bot service main module with placeholder implementation
- src/api/main.py - FastAPI web service with health check and root endpoints
- src/scheduler/celery_app.py - Celery application configuration with RabbitMQ and Redis
- src/scheduler/tasks.py - Celery tasks for notifications and background processing
- README.md - Project documentation with setup instructions and service information

### Modified

### Removed
