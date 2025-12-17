<!-- markdownlint-disable-file -->
# Task Research Notes: Redis to Valkey Migration

## Research Executed

### Current Redis Usage Analysis
- **Docker Compose Configuration** (`compose.yaml`):
  - Redis service using `redis:7.4-alpine` image
  - Standard configuration with appendonly persistence
  - Health check using `redis-cli ping`
  - Single service definition replicated across all environment files

- **Python Dependencies** (`pyproject.toml`):
  - `redis>=5.0.0` - Primary Python client library
  - `opentelemetry-instrumentation-redis>=0.41b0` - Observability instrumentation

- **Redis Client Implementation** (`shared/cache/client.py`):
  - Async connection pooling using `redis.asyncio`
  - Two client classes: `RedisClient` (async) and `SyncRedisClient` (sync)
  - Connection URL format: `redis://host:port/db`
  - Operations: get, set, delete, exists, expire, ttl, JSON helpers

- **Current Usage Patterns**:
  - OAuth state tokens (10-minute TTL)
  - Session storage (24-hour TTL)
  - User role caching (5-minute TTL)
  - Display name caching (5-minute TTL)
  - Game details caching (60-second TTL)
  - Rate limiting for message updates

- **Environment Configuration**:
  - `REDIS_URL` environment variable used throughout
  - Default: `redis://localhost:6379/0`
  - Referenced in: API, Bot, and test configurations

### #fetch:https://valkey.io/
- **Valkey Overview**:
  - Linux Foundation project, BSD-3-Clause license
  - Fork of Redis 7.2.4 (last true open-source Redis version)
  - Current versions: 9.0.1 (latest), 8.1.5, 7.2.11
  - 100% Redis protocol compatible
  - Backed by AWS, Google Cloud, Oracle, Alibaba, and others

- **Available Docker Images**:
  - `valkey/valkey:9.0.1` / `valkey/valkey:9.0.1-alpine`
  - `valkey/valkey:8.1.5` / `valkey/valkey:8.1.5-alpine`
  - `valkey/valkey:7.2.11` / `valkey/valkey:7.2.11-alpine`
  - Compatible naming: supports `redis://` and `rediss://` URI schemes

### #githubRepo:"valkey-io/valkey" Python client compatibility docker migration
- **Protocol Compatibility**:
  - Valkey maintains 100% Redis protocol compatibility
  - Existing `redis-py` client works without modification
  - Same connection URL format accepted (`redis://host:port/db`)
  - Same commands and response formats
  - All RESP2 and RESP3 features supported

- **Migration Path**:
  - Drop-in replacement at Docker image level
  - No Python code changes required
  - No configuration changes needed beyond image name
  - Existing health checks work as-is (`ping` command)

- **Version Mapping**:
  - Valkey 7.2.x ≈ Redis 7.2.x (pre-license-change compatibility)
  - Valkey 8.x and 9.x add new features while maintaining compatibility

### Recommended Version

**Software**: Valkey
**Recommended Version**: 9.0.1
**Type**: Latest Stable Release
**Support Until**: Active development with regular security and bug fix updates
**Reasoning**: Valkey 9.0.1 is the latest stable release (December 2025) and Valkey has no formal LTS program. Per version selection guidelines, when no LTS exists, recommend the latest stable release. Version 9.0 has been production-ready since October 21, 2025, with 9.0.1 providing bug fixes and improvements. It includes atomic slot migration, hash field expiration, performance improvements, and maintains 100% Redis protocol compatibility.
**Source**: https://github.com/valkey-io/valkey/releases

**Alternatives Considered**:
- 8.1.5 (Released December 2025, stable but lacks 9.x features like atomic slot migration)
- 7.2.11 (Most direct Redis 7.2.4 replacement, lacks performance improvements and new features from 8.x and 9.x)

## Key Discoveries

### Drop-In Replacement Strategy
Valkey can be migrated with **zero code changes** - only Docker image updates required:

1. **Docker Compose Changes Only**:
   - Change image from `redis:7.4-alpine` to `valkey/valkey:8.1.5-alpine` or `valkey/valkey:9.0.1-alpine`
   - No configuration changes needed
   - Health checks continue to work (`redis-cli` still available as `valkey-cli`)

2. **Python Client Compatibility**:
   - `redis>=5.0.0` library works unchanged
   - `opentelemetry-instrumentation-redis` works unchanged
   - Connection URL format identical
   - All Redis commands supported

3. **Zero Application Changes**:
   - No code modifications in `shared/cache/client.py`
   - No changes to cache keys or TTL patterns
   - No changes to environment variables
   - No changes to application logic

### Complete Migration Example

#### Docker Compose Change
```yaml
# Before (Redis)
redis:
  image: redis:7.4-alpine
  command: ${REDIS_COMMAND:-redis-server --appendonly yes --loglevel ${REDIS_LOG_LEVEL:-notice}}
  healthcheck:
    test: ["CMD", "redis-cli", "ping"]

# After (Valkey)
redis:  # Keep service name for compatibility
  image: valkey/valkey:9.0.1-alpine
  command: ${REDIS_COMMAND:-valkey-server --appendonly yes --loglevel ${REDIS_LOG_LEVEL:-notice}}
  healthcheck:
    test: ["CMD", "valkey-cli", "ping"]
```

#### Version Selection Rationale
- **Valkey 9.0.1**: Recommended - latest stable release with atomic slot migration, hash field expiration, and performance improvements
- **Valkey 8.1.5**: Stable alternative if 9.x features not needed, but lacks latest capabilities
- **Valkey 7.2.11**: Most conservative, direct mapping from Redis 7.2.4 but lacks 8.x and 9.x improvements

### Testing and Validation Approach

**Integration Tests** (already in place):
- No test changes required
- Tests use `REDIS_URL` environment variable
- Works with Valkey through protocol compatibility

**Manual Validation Steps**:
1. Update Docker image in `compose.yaml`
2. Start services: `docker compose up -d`
3. Verify health: `docker compose ps` (should show healthy)
4. Run integration tests: `./scripts/run-integration-tests.sh`
5. Verify OAuth flow and caching in running application

**Rollback Strategy**:
- Simple image revert in `compose.yaml`
- Data compatible in both directions (same RDB format through v8)
- No migration scripts needed

## Recommended Approach

### Migration Strategy: Drop-In Docker Image Replacement

**Scope**: Update Docker images from Redis to Valkey across all environments with zero code changes.

**Implementation Steps**:

1. **Update Docker Compose Files** (5 files):
   - `compose.yaml` (production base)
   - `compose.override.yaml` (development)
   - `compose.e2e.yaml` (E2E tests)
   - `compose.int.yaml` (integration tests)
   - `compose.staging.yaml` (staging)

2. **Update CI/CD Configuration**:
   - `.github/workflows/ci-cd.yml` - Update test container image

3. **Update Documentation**:
   - `DOCKER_PORTS.md` - Note Valkey instead of Redis
   - `TESTING_OAUTH.md` - Update CLI commands from `redis-cli` to `valkey-cli`
   - `docs/LOCAL_TESTING_WITH_ACT.md` - Update references

4. **Version Selection**: Use **Valkey 9.0.1-alpine** (see Recommended Version section above)
   - Latest stable release with all current features and bug fixes
   - Production-ready since October 2025 (9.0.0 GA)
   - Maintains 100% compatibility with Redis protocol and data formats
   - Includes atomic slot migration, hash field expiration, and performance improvements

5. **Testing Approach**:
   - Run existing integration test suite (no modifications needed)
   - Verify OAuth flows in development environment
   - Monitor cache operations in staging before production

6. **Zero Code Changes Required**:
   - `pyproject.toml` dependencies unchanged
   - `shared/cache/client.py` unchanged
   - All application code unchanged
   - Environment variables unchanged

## Implementation Guidance

- **Objectives**: Replace Redis with Valkey to use permissive BSD-3-Clause license while maintaining 100% compatibility
- **Key Tasks**:
  1. Update Docker images in all compose files
  2. Update CLI command references in documentation
  3. Validate with existing integration tests
- **Dependencies**: None - drop-in replacement
- **Success Criteria**:
  - All services start successfully
  - Health checks pass
  - Integration tests pass
  - OAuth and caching functionality works identically
- **Risk Level**: Very Low - protocol-compatible drop-in replacement
- **Rollback Plan**: Revert Docker image changes (data format compatible)
