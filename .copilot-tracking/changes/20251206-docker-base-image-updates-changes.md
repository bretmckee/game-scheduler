<!-- markdownlint-disable-file -->

# Release Changes: Docker Base Image Version Updates

**Related Plan**: 20251206-docker-base-image-updates-plan.instructions.md
**Implementation Date**: 2025-12-06

## Summary

Updating all Docker base images to their most recent stable LTS versions to
ensure long-term support, security patches, and maintain best practices for
containerization. This includes Python 3.11→3.13, Nginx 1.25→1.28, Redis 7→7.4,
PostgreSQL 15→17, and optionally Node.js 20→22.

## Changes

### Added

- scripts/migrate_postgres_15_to_17.sh - Migration script for safely upgrading
  PostgreSQL from version 15 to 17 using pg_dump/pg_restore with automatic
  backup and rollback support

### Modified

- docker/api.Dockerfile - Updated Python base image from 3.11-slim to 3.13-slim
  in both base and production stages
- docker/bot.Dockerfile - Updated Python base image from 3.11-slim to 3.13-slim
  in both base and production stages
- docker/init.Dockerfile - Updated Python base image from 3.11-slim to 3.13-slim
- docker/notification-daemon.Dockerfile - Updated Python base image from
  3.11-slim to 3.13-slim in both base and production stages
- docker/status-transition-daemon.Dockerfile - Updated Python base image from
  3.11-slim to 3.13-slim in both base and production stages
- docker/test.Dockerfile - Updated Python base image from 3.11-slim to 3.13-slim
- docker/frontend.Dockerfile - Updated Node.js base image from 20-alpine to
  22-alpine in builder stage for longer LTS support
- docker/frontend.Dockerfile - Updated Nginx base image from 1.25-alpine to
  1.28-alpine in production stage for current stable branch
- docker-compose.base.yml - Updated Redis image from redis:7-alpine to
  redis:7.4-alpine for latest patches in 7.x line
- docker-compose.base.yml - Updated PostgreSQL image from postgres:15-alpine to
  postgres:17-alpine for latest stable version with extended support

### Removed
