<!-- markdownlint-disable-file -->

# Task Details: Redis to Valkey Migration

## Research Reference

**Source Research**: #file:../research/20251217-redis-to-valkey-migration-research.md

## Phase 1: Docker Compose Updates

### Task 1.1: Update production base Docker Compose configuration

Update the Redis service definition in the main Docker Compose file to use Valkey 9.0.1-alpine image.

- **Files**:
  - [compose.yaml](../../compose.yaml) - Main production Docker Compose configuration
- **Success**:
  - Redis service uses `valkey/valkey:9.0.1-alpine` image
  - Command updated to use `valkey-server` instead of `redis-server`
  - Health check updated to use `valkey-cli` instead of `redis-cli`
  - Service name remains `redis` for backward compatibility
- **Research References**:
  - #file:../research/20251217-redis-to-valkey-migration-research.md (Lines 72-105) - Drop-in replacement strategy with complete migration example
- **Dependencies**:
  - None - independent change

### Task 1.2: Update development override configuration

Update Redis service overrides in the development environment configuration.

- **Files**:
  - [compose.override.yaml](../../compose.override.yaml) - Development environment overrides
- **Success**:
  - Any Redis-specific overrides updated to Valkey equivalents
  - Image reference uses Valkey if specified
  - CLI commands updated in any exec or healthcheck overrides
- **Research References**:
  - #file:../research/20251217-redis-to-valkey-migration-research.md (Lines 72-105) - Migration example applies to all compose files
- **Dependencies**:
  - Task 1.1 completion recommended for consistency

### Task 1.3: Update E2E test environment configuration

Update Redis configuration in the end-to-end test environment.

- **Files**:
  - [compose.e2e.yaml](../../compose.e2e.yaml) - E2E test environment configuration
- **Success**:
  - Redis service uses Valkey 9.0.1-alpine image
  - CLI commands updated in test-specific overrides
  - Health checks updated to use `valkey-cli`
- **Research References**:
  - #file:../research/20251217-redis-to-valkey-migration-research.md (Lines 120-140) - Testing and validation approach
- **Dependencies**:
  - Task 1.1 completion for consistent patterns

### Task 1.4: Update integration test environment configuration

Update Redis configuration in the integration test environment.

- **Files**:
  - [compose.int.yaml](../../compose.int.yaml) - Integration test environment configuration
- **Success**:
  - Redis service uses Valkey 9.0.1-alpine image
  - CLI commands updated in test-specific configuration
  - Health checks use `valkey-cli ping`
- **Research References**:
  - #file:../research/20251217-redis-to-valkey-migration-research.md (Lines 120-140) - Integration tests compatibility confirmed
- **Dependencies**:
  - Task 1.1 completion for consistent patterns

### Task 1.5: Update staging environment configuration

Update Redis configuration in the staging environment.

- **Files**:
  - [compose.staging.yaml](../../compose.staging.yaml) - Staging environment configuration
- **Success**:
  - Redis service uses Valkey 9.0.1-alpine image
  - Command uses `valkey-server` with appropriate flags
  - Health check uses `valkey-cli`
- **Research References**:
  - #file:../research/20251217-redis-to-valkey-migration-research.md (Lines 107-119) - Version selection rationale for production-like environments
- **Dependencies**:
  - Task 1.1 completion for consistent patterns

## Phase 2: CI/CD Configuration Updates

### Task 2.1: Update GitHub Actions workflow test container image

Update CI/CD pipeline to use Valkey service container for testing.

- **Files**:
  - [.github/workflows/ci-cd.yml](../../.github/workflows/ci-cd.yml) - CI/CD workflow configuration
- **Success**:
  - Service container uses `valkey/valkey:9.0.1-alpine` image
  - Health check command uses `valkey-cli ping`
  - Tests pass with Valkey service container
- **Research References**:
  - #file:../research/20251217-redis-to-valkey-migration-research.md (Lines 142-166) - CI/CD configuration update requirement
- **Dependencies**:
  - Phase 1 completion to ensure consistent configuration

## Phase 3: Documentation Updates

### Task 3.1: Update Docker ports documentation

Update service documentation to reflect Valkey instead of Redis.

- **Files**:
  - [DOCKER_PORTS.md](../../DOCKER_PORTS.md) - Docker service ports and descriptions
- **Success**:
  - References to Redis service updated to mention Valkey
  - Port 6379 description notes Valkey compatibility
  - License information updated to BSD-3-Clause
- **Research References**:
  - #file:../research/20251217-redis-to-valkey-migration-research.md (Lines 17-20) - Valkey overview and licensing
- **Dependencies**:
  - None - documentation update independent of implementation

### Task 3.2: Update OAuth testing documentation CLI commands

Update CLI command examples from redis-cli to valkey-cli.

- **Files**:
  - [TESTING_OAUTH.md](../../TESTING_OAUTH.md) - OAuth flow testing documentation
- **Success**:
  - All `redis-cli` commands replaced with `valkey-cli`
  - Connection examples updated
  - Verification commands work with Valkey
- **Research References**:
  - #file:../research/20251217-redis-to-valkey-migration-research.md (Lines 142-166) - Documentation update requirements
- **Dependencies**:
  - None - documentation can be updated independently

### Task 3.3: Update local testing with ACT documentation

Update local GitHub Actions testing documentation with Valkey references.

- **Files**:
  - [docs/LOCAL_TESTING_WITH_ACT.md](../../docs/LOCAL_TESTING_WITH_ACT.md) - Local CI/CD testing guide
- **Success**:
  - Service container references updated to Valkey
  - CLI command examples use `valkey-cli`
  - Version information reflects Valkey 9.0.1
- **Research References**:
  - #file:../research/20251217-redis-to-valkey-migration-research.md (Lines 142-166) - Testing documentation updates
- **Dependencies**:
  - Task 2.1 completion for accurate CI/CD references

## Phase 4: Validation and Testing

### Task 4.1: Verify Docker Compose services start successfully

Start all services and verify Valkey service health and connectivity.

- **Files**:
  - All Docker Compose configurations from Phase 1
- **Success**:
  - `docker compose up -d` starts all services
  - Valkey service shows healthy status
  - Valkey responds to `valkey-cli ping` with PONG
  - Application services connect to Valkey successfully
- **Research References**:
  - #file:../research/20251217-redis-to-valkey-migration-research.md (Lines 142-158) - Manual validation steps
- **Dependencies**:
  - Phase 1 completion required

### Task 4.2: Run integration test suite

Execute existing integration tests to verify cache operations work with Valkey.

- **Files**:
  - [scripts/run-integration-tests.sh](../../scripts/run-integration-tests.sh) - Integration test runner
  - [tests/integration/](../../tests/integration/) - Integration test suite
- **Success**:
  - All integration tests pass without modifications
  - Cache operations (set, get, delete, expire, TTL) function correctly
  - OAuth state storage and retrieval works
  - Session management operates identically
- **Research References**:
  - #file:../research/20251217-redis-to-valkey-migration-research.md (Lines 120-140) - Integration test compatibility and zero-change validation
- **Dependencies**:
  - Task 4.1 completion - services must be running

### Task 4.3: Validate OAuth flow and cache operations

Manually test OAuth authentication flow and cache operations in development environment.

- **Files**:
  - Development environment with Valkey running
- **Success**:
  - OAuth state tokens stored and retrieved correctly (10-minute TTL)
  - User sessions persist and expire properly (24-hour TTL)
  - Role caching works with 5-minute TTL
  - Display name caching functions correctly
  - Game details caching operates as expected (60-second TTL)
  - Rate limiting for message updates works
- **Research References**:
  - #file:../research/20251217-redis-to-valkey-migration-research.md (Lines 35-42) - Current usage patterns that must continue working
- **Dependencies**:
  - Task 4.2 completion recommended
  - Phase 1 and 2 completion required

## Dependencies

- Valkey 9.0.1-alpine Docker image (publicly available at valkey/valkey:9.0.1-alpine)
- Existing `redis>=5.0.0` Python library (no version changes needed)
- Docker Compose 2.x for all environments

## Success Criteria

- All five Docker Compose files updated with Valkey image
- CI/CD workflow uses Valkey service container
- All documentation references updated from Redis to Valkey
- Integration test suite passes without any test modifications
- OAuth flows function identically to Redis implementation
- All cache operations work with same performance characteristics
- Zero application code changes required
- Health checks pass across all environments
