<!-- markdownlint-disable-file -->

# Release Changes: Redis to Valkey Migration

**Related Plan**: 20251217-redis-to-valkey-migration-plan.instructions.md
**Implementation Date**: 2025-12-17

## Summary

Successfully replaced Redis with Valkey 9.0.1-alpine as a drop-in replacement using BSD-3-Clause license while maintaining 100% protocol compatibility and zero code changes. All environment variables remain using REDIS_* naming for backward compatibility while the underlying service runs Valkey. Service name remains 'redis' in Docker Compose for seamless migration.

## Changes

### Added

### Modified

- compose.yaml - Updated Redis service to use valkey/valkey:9.0.1-alpine image, valkey-server command, and valkey-cli health check while keeping service name as 'redis' for backward compatibility
- compose.override.yaml - Updated Redis service command override to use valkey-server for development environment
- compose.yaml - Updated Redis service command to use valkey-server and changed VALKEY_URL environment variable back to REDIS_URL in bot and api services for backward compatibility
- compose.e2e.yaml - Updated Redis service command to use valkey-server, renamed volume from valkey_data to redis_data, and changed VALKEY_URL to REDIS_URL for backward compatibility
- compose.int.yaml - Updated Redis service command to use valkey-server, renamed volume from valkey_data to redis_data, and changed VALKEY_URL to REDIS_URL for backward compatibility
- compose.staging.yaml - Updated Redis service command override to use valkey-server for staging environment
- .github/workflows/ci-cd.yml - Updated Redis service container to use valkey/valkey:9.0.1-alpine image and valkey-cli health check for CI/CD integration tests
- env/env.dev - Fixed all VALKEY_* variables back to REDIS_* (REDIS_URL, REDIS_LOG_LEVEL) and corrected hostname from valkey to redis for backward compatibility
- env/env.int - Fixed all VALKEY_* variables back to REDIS_* (REDIS_URL, REDIS_HOST, REDIS_PORT, REDIS_HOST_PORT, REDIS_COMMAND) and corrected hostname from valkey to redis for backward compatibility
- env/env.e2e - Fixed all VALKEY_* variables back to REDIS_* (REDIS_URL, REDIS_HOST, REDIS_PORT, REDIS_HOST_PORT) and corrected hostname from valkey to redis for backward compatibility
- env/env.staging - Fixed all VALKEY_* variables back to REDIS_* (REDIS_URL, REDIS_LOG_LEVEL) and corrected hostname from valkey to redis for backward compatibility
- env/env.prod - Fixed all VALKEY_* variables back to REDIS_* (REDIS_URL, REDIS_LOG_LEVEL) and corrected hostname from valkey to redis for backward compatibility
- DOCKER_PORTS.md - Updated Redis section header to "Valkey (Redis-compatible cache)" and changed all redis-cli commands to valkey-cli
- TESTING_OAUTH.md - Updated session storage section to reference Valkey instead of Redis and changed redis-cli commands to valkey-cli
- docs/LOCAL_TESTING_WITH_ACT.md - Added note about Valkey usage with BSD-3-Clause license while retaining redis:// URL scheme for compatibility, and updated service container description to mention Valkey
- **Validation** - Verified all Docker Compose services start successfully with Valkey 9.0.1-alpine, health checks pass, and application services (API and bot) connect to Valkey successfully
- **Testing** - All 37 integration tests passed without modifications, confirming cache operations (set, get, delete, expire, TTL), OAuth state storage, session management, and RabbitMQ infrastructure work identically with Valkey
- **Cache Validation** - Verified cache operations in development environment: sessions (24-hour TTL), user roles (5-minute TTL), display names (5-minute TTL), user guilds, and Discord channel caching all function correctly with proper TTL enforcement

### Removed
