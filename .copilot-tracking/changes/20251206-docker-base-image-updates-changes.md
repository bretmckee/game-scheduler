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

### Removed
