---
applyTo: '.copilot-tracking/changes/20251217-redis-to-valkey-migration-changes.md'
---

<!-- markdownlint-disable-file -->

# Task Checklist: Redis to Valkey Migration

## Overview

Replace Redis with Valkey 9.0.1-alpine as a drop-in replacement using BSD-3-Clause license while maintaining 100% protocol compatibility and zero code changes.

## Objectives

- Replace Redis Docker images with Valkey across all environments
- Maintain 100% compatibility with existing cache operations
- Update CLI command references in documentation
- Validate functionality through existing integration tests
- Preserve all data formats and connection configurations

## Research Summary

### Project Files

- [compose.yaml](../../compose.yaml) - Production Docker Compose with Redis 7.4-alpine
- [compose.override.yaml](../../compose.override.yaml) - Development environment configuration
- [compose.e2e.yaml](../../compose.e2e.yaml) - E2E test environment
- [compose.int.yaml](../../compose.int.yaml) - Integration test environment
- [compose.staging.yaml](../../compose.staging.yaml) - Staging environment
- [shared/cache/client.py](../../shared/cache/client.py) - Redis client implementation (no changes needed)
- [pyproject.toml](../../pyproject.toml) - Python dependencies (no changes needed)

### External References

- #file:../research/20251217-redis-to-valkey-migration-research.md - Complete migration research with protocol compatibility analysis
- #fetch:https://valkey.io/ - Valkey project overview and version information
- #githubRepo:"valkey-io/valkey docker migration" - Protocol compatibility and migration patterns

### Standards References

- #file:../../.github/instructions/containerization-docker-best-practices.instructions.md - Docker image selection and configuration
- #file:../../.github/instructions/coding-best-practices.instructions.md - Testing and validation requirements

## Implementation Checklist

### [x] Phase 1: Docker Compose Updates

- [x] Task 1.1: Update production base Docker Compose configuration
  - Details: [.copilot-tracking/details/20251217-redis-to-valkey-migration-details.md](../details/20251217-redis-to-valkey-migration-details.md) (Lines 12-25)

- [x] Task 1.2: Update development override configuration
  - Details: [.copilot-tracking/details/20251217-redis-to-valkey-migration-details.md](../details/20251217-redis-to-valkey-migration-details.md) (Lines 27-37)

- [x] Task 1.3: Update E2E test environment configuration
  - Details: [.copilot-tracking/details/20251217-redis-to-valkey-migration-details.md](../details/20251217-redis-to-valkey-migration-details.md) (Lines 39-49)

- [x] Task 1.4: Update integration test environment configuration
  - Details: [.copilot-tracking/details/20251217-redis-to-valkey-migration-details.md](../details/20251217-redis-to-valkey-migration-details.md) (Lines 51-61)

- [x] Task 1.5: Update staging environment configuration
  - Details: [.copilot-tracking/details/20251217-redis-to-valkey-migration-details.md](../details/20251217-redis-to-valkey-migration-details.md) (Lines 63-73)

### [x] Phase 2: CI/CD Configuration Updates

- [x] Task 2.1: Update GitHub Actions workflow test container image
  - Details: [.copilot-tracking/details/20251217-redis-to-valkey-migration-details.md](../details/20251217-redis-to-valkey-migration-details.md) (Lines 77-88)

### [x] Phase 3: Documentation Updates

- [x] Task 3.1: Update Docker ports documentation
  - Details: [.copilot-tracking/details/20251217-redis-to-valkey-migration-details.md](../details/20251217-redis-to-valkey-migration-details.md) (Lines 92-100)

- [x] Task 3.2: Update OAuth testing documentation CLI commands
  - Details: [.copilot-tracking/details/20251217-redis-to-valkey-migration-details.md](../details/20251217-redis-to-valkey-migration-details.md) (Lines 102-111)

- [x] Task 3.3: Update local testing with ACT documentation
  - Details: [.copilot-tracking/details/20251217-redis-to-valkey-migration-details.md](../details/20251217-redis-to-valkey-migration-details.md) (Lines 113-121)

### [x] Phase 4: Validation and Testing

- [x] Task 4.1: Verify Docker Compose services start successfully
  - Details: [.copilot-tracking/details/20251217-redis-to-valkey-migration-details.md](../details/20251217-redis-to-valkey-migration-details.md) (Lines 125-134)

- [x] Task 4.2: Run integration test suite
  - Details: [.copilot-tracking/details/20251217-redis-to-valkey-migration-details.md](../details/20251217-redis-to-valkey-migration-details.md) (Lines 136-145)

- [x] Task 4.3: Validate OAuth flow and cache operations
  - Details: [.copilot-tracking/details/20251217-redis-to-valkey-migration-details.md](../details/20251217-redis-to-valkey-migration-details.md) (Lines 147-157)

## Dependencies

- Valkey 9.0.1-alpine Docker image (publicly available)
- Existing `redis>=5.0.0` Python library (no changes required)
- Docker Compose 2.x

## Success Criteria

- All Docker Compose files use `valkey/valkey:9.0.1-alpine` image
- All services start successfully with healthy status
- Integration test suite passes without modifications
- OAuth flows work identically to Redis implementation
- Cache operations (set, get, expire, TTL) function correctly
- Documentation accurately reflects Valkey usage
- No application code changes required
