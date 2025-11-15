<!-- markdownlint-disable-file -->

# Release Changes: Discord Game Scheduling System

**Related Plan**: 20251114-discord-game-scheduling-system-plan.instructions.md
**Implementation Date**: 2025-11-15

## Summary

Implementation of a complete Discord game scheduling system with microservices architecture, featuring Discord bot with button interactions, web dashboard with OAuth2 authentication, role-based authorization, multi-channel support with settings inheritance, and automated notifications.

## Changes

### Added

- docker-compose.yml - Multi-service orchestration with postgres, rabbitmq, redis, bot, api, scheduler services
- .env.example - Environment variable template with Discord, database, and service configuration
- docker/bot.Dockerfile - Multi-stage Docker image for Discord bot service
- docker/api.Dockerfile - Multi-stage Docker image for FastAPI web service
- docker/scheduler.Dockerfile - Multi-stage Docker image for Celery scheduler service
- pyproject.toml - Project configuration with Python dependencies and tooling setup
- requirements.txt - Python package requirements for all services
- README.md - Project documentation with architecture overview and setup instructions
- .gitignore - Git ignore patterns for Python, Docker, and development files
- services/bot/ - Directory structure for Discord bot service
- services/api/ - Directory structure for FastAPI web service
- services/scheduler/ - Directory structure for Celery scheduler service
- shared/ - Directory structure for shared models and utilities

### Modified

### Removed
