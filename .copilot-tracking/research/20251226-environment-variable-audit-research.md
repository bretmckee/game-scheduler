# Task Research Notes: Environment Variable Configuration Audit

## Research Executed

### File Analysis
- config/env/env.example - Master template with full comments
- config/env/env.dev - Development configuration
- config/env/env.e2e - End-to-end test configuration
- config/env/env.int - Integration test configuration
- config/env/env.prod - Production configuration
- config/env/env.staging - Staging configuration
- compose.yaml - Base compose configuration
- compose.override.yaml - Development overrides
- compose.prod.yaml - Production overrides
- compose.staging.yaml - Staging overrides
- compose.int.yaml - Integration test overrides
- compose.e2e.yaml - E2E test overrides

### Code Search Results
- `JWT_SECRET` - Used in compose.yaml API service and services/api/config.py
- `CONTAINER_PREFIX` - Used in all compose files for service naming
- `COMPOSE_FILE` - Controls which compose files are loaded
- `COMPOSE_PROFILES` - Controls conditional service activation
- `RETRY_DAEMON_LOG_LEVEL` - Used in compose.yaml retry-daemon service
- `HOST_WORKSPACE_FOLDER` - Used in compose files for volume mounting

## Key Discoveries

### Critical Findings

**Variable Inconsistencies Found:**

1. **Missing Variables:**
   - `env.example` MISSING: `COMPOSE_FILE`, `COMPOSE_PROFILES`, `JWT_SECRET`, `RETRY_DAEMON_LOG_LEVEL`, `CONTAINER_PREFIX`, `RESTART_POLICY`, `DISCORD_REDIRECT_URI`, `HOST_WORKSPACE_FOLDER`
   - `env.prod` MISSING: `COMPOSE_FILE`, `COMPOSE_PROFILES`, `JWT_SECRET`, `RETRY_DAEMON_LOG_LEVEL`, `CONTAINER_PREFIX`, `RESTART_POLICY`, `DISCORD_REDIRECT_URI`, `API_HOST_PORT`, `FRONTEND_HOST_PORT`, `RABBITMQ_MGMT_HOST_PORT`
   - `env.staging` MISSING: `COMPOSE_PROFILES`, `JWT_SECRET`, `RETRY_DAEMON_LOG_LEVEL`, `RESTART_POLICY`, `API_HOST_PORT`, `FRONTEND_HOST_PORT`, `RABBITMQ_MGMT_HOST_PORT`
   - Test configs (`env.e2e`, `env.int`) have minimal variables focused on test requirements

2. **Unused Variables:**
   - `env.example` has `API_SECRET_KEY` (replaced by `JWT_SECRET`)
   - `env.dev` has duplicate/conflicting `API_HOST_PORT` definitions
   - `env.dev` has commented out Discord invite URL
   - `env.dev` has override at bottom for `API_BASE_URL` that contradicts earlier value
   - Several env files have `API_HOST`, `API_PORT` which are not used in compose files (hardcoded in compose.yaml as 8000)

3. **Variable Ordering Issues:**
   - Each file has different ordering
   - `env.dev` has Cloudflare section at end, out of order
   - Test files have completely different organization
   - No consistent grouping strategy

4. **Comment Inconsistencies:**
   - `env.dev` lacks proper section headers
   - `env.prod` and `env.staging` have minimal comments
   - Test configs have sparse comments
   - `DISCORD_REDIRECT_URI` in staging has comment but not in example

5. **Value Inconsistencies:**
   - `env.dev` contains actual secrets (this is correct - live credentials must be preserved)
   - Port variables in test configs don't match deployment configs
   - Some configs use relative URLs, others use absolute

### Environment-Specific Variable Usage

**Development Only (compose.override.yaml):**
- `POSTGRES_HOST_PORT`, `RABBITMQ_DATA_HOST_PORT`, `RABBITMQ_MGMT_HOST_PORT`, `REDIS_HOST_PORT`, `ALLOY_HOST_PORT`
- `HOST_WORKSPACE_FOLDER` (for volume mounts)
- `PYTHONUNBUFFERED` (set by compose file, not env)

**Test-Specific (e2e/int):**
- `CONTAINER_PREFIX` with test-specific defaults
- `RESTART_POLICY` set to "no"
- `TEST_ENVIRONMENT` flag
- Discord test bot credentials for e2e
- `POSTGRES_HOST`, `POSTGRES_PORT` separate variables (not just URL)
- `RABBITMQ_HOST`, `RABBITMQ_PORT` separate variables
- `REDIS_HOST`, `REDIS_PORT` separate variables
- `REDIS_COMMAND` for disabling persistence in tests
- `PYTEST_RUNNING` flag (set by compose, not env)

**Production/Staging:**
- External network configuration in staging
- No port mappings (handled by reverse proxy)

### Variable Categories

**1. Docker Configuration:**
- `COMPOSE_FILE` - Which compose files to load
- `COMPOSE_PROFILES` - Conditional service activation (e.g., cloudflare)
- `IMAGE_REGISTRY` - Docker registry prefix
- `IMAGE_TAG` - Image version tag
- `CONTAINER_PREFIX` - Container name prefix for isolation
- `RESTART_POLICY` - Container restart behavior
- `HOST_WORKSPACE_FOLDER` - Development volume mount source

**2. Discord Configuration:**
- `DISCORD_BOT_TOKEN` - Bot authentication token
- `DISCORD_CLIENT_ID` - OAuth application ID
- `DISCORD_CLIENT_SECRET` - OAuth application secret
- `DISCORD_REDIRECT_URI` - OAuth callback URL (staging only)
- `BOT_LOG_LEVEL` - Bot service log verbosity

**3. Database Configuration:**
- `POSTGRES_USER` - Database username
- `POSTGRES_PASSWORD` - Database password
- `POSTGRES_DB` - Database name
- `DATABASE_URL` - Full connection URL
- `POSTGRES_LOG_LEVEL` - PostgreSQL log verbosity
- `POSTGRES_HOST` - Database host (test configs only)
- `POSTGRES_PORT` - Database port (test configs only)
- `POSTGRES_HOST_PORT` - Host port mapping (dev/test only)

**4. RabbitMQ Configuration:**
- `RABBITMQ_DEFAULT_USER` - RabbitMQ username
- `RABBITMQ_DEFAULT_PASS` - RabbitMQ password
- `RABBITMQ_URL` - Full connection URL
- `RABBITMQ_LOG_LEVEL` - RabbitMQ log verbosity
- `RABBITMQ_HOST` - RabbitMQ host (test configs only)
- `RABBITMQ_PORT` - RabbitMQ port (test configs only)
- `RABBITMQ_HOST_PORT` - RabbitMQ port mapping (test only)
- `RABBITMQ_DATA_HOST_PORT` - Data port mapping (dev only)
- `RABBITMQ_MGMT_HOST_PORT` - Management UI port (dev/test)

**5. Redis Configuration:**
- `REDIS_URL` - Full connection URL
- `REDIS_LOG_LEVEL` - Redis log verbosity
- `REDIS_HOST` - Redis host (test configs only)
- `REDIS_PORT` - Redis port (test configs only)
- `REDIS_HOST_PORT` - Host port mapping (dev/test only)
- `REDIS_COMMAND` - Custom command (test configs for no-persistence)

**6. API Configuration:**
- `API_HOST` - API bind address (unused in compose, hardcoded)
- `API_PORT` - API listen port (unused in compose, hardcoded)
- `API_SECRET_KEY` - DEPRECATED, replaced by JWT_SECRET
- `JWT_SECRET` - JWT signing key (MISSING from env files)
- `API_LOG_LEVEL` - API service log verbosity
- `API_URL` - Frontend API endpoint configuration
- `API_BASE_URL` - External API URL for Discord embeds
- `API_HOST_PORT` - Host port mapping (dev/test only)

**7. Frontend Configuration:**
- `FRONTEND_URL` - Frontend URL for bot redirects
- `NGINX_LOG_LEVEL` - Nginx log verbosity
- `FRONTEND_HOST_PORT` - Host port mapping (dev/test only)

**8. Environment:**
- `ENVIRONMENT` - Environment identifier (development/staging/production)
- `TEST_ENVIRONMENT` - Test mode flag (test configs only)
- `PYTEST_RUNNING` - Pytest detection flag (set by compose)

**9. Daemon Service Configuration:**
- `NOTIFICATION_DAEMON_LOG_LEVEL` - Notification daemon log verbosity
- `STATUS_TRANSITION_DAEMON_LOG_LEVEL` - Status daemon log verbosity
- `RETRY_DAEMON_LOG_LEVEL` - Retry daemon log verbosity (MISSING)
- `RETRY_INTERVAL_SECONDS` - Retry daemon poll interval (test only)

**10. OpenTelemetry / Grafana Cloud:**
- `GRAFANA_CLOUD_API_KEY` - Grafana authentication
- `GRAFANA_CLOUD_OTLP_INSTANCE_ID` - OTLP gateway instance
- `GRAFANA_CLOUD_OTLP_ENDPOINT` - OTLP gateway URL
- `GRAFANA_CLOUD_PROMETHEUS_INSTANCE_ID` - Prometheus instance
- `GRAFANA_CLOUD_PROMETHEUS_ENDPOINT` - Prometheus remote write URL
- `GRAFANA_CLOUD_LOKI_INSTANCE_ID` - Loki instance
- `GRAFANA_CLOUD_LOKI_ENDPOINT` - Loki push URL
- `ALLOY_OTLP_GRPC_PORT` - Alloy OTLP gRPC port (optional)
- `ALLOY_OTLP_HTTP_PORT` - Alloy OTLP HTTP port (optional)
- `ALLOY_LOG_LEVEL` - Alloy log verbosity
- `ALLOY_HOST_PORT` - Alloy UI host mapping (dev only)

**11. Cloudflare Tunnel:**
- `CLOUDFLARE_TUNNEL_TOKEN` - Cloudflare tunnel authentication

**12. Test-Specific Discord Bots:**
- `DISCORD_TOKEN` - E2E test bot token
- `DISCORD_ADMIN_BOT_TOKEN` - E2E admin bot token
- `DISCORD_ADMIN_BOT_CLIENT_ID` - E2E admin bot client ID
- `DISCORD_ADMIN_BOT_CLIENT_SECRET` - E2E admin bot secret
- `DISCORD_ADMIN_BOT_INVITE_URL` - E2E admin bot invite
- `DISCORD_GUILD_ID` - E2E test guild
- `DISCORD_CHANNEL_ID` - E2E test channel
- `DISCORD_USER_ID` - E2E test user

## Recommended Approach

### Standardized Variable Set

Create consistent variable ordering across all files:

```
# ==========================================
# Docker Configuration
# ==========================================
COMPOSE_FILE
COMPOSE_PROFILES
IMAGE_REGISTRY
IMAGE_TAG
CONTAINER_PREFIX
RESTART_POLICY
HOST_WORKSPACE_FOLDER

# ==========================================
# Discord Bot Configuration
# ==========================================
DISCORD_BOT_TOKEN
DISCORD_CLIENT_ID
DISCORD_CLIENT_SECRET
DISCORD_REDIRECT_URI
BOT_LOG_LEVEL

# ==========================================
# Database Configuration
# ==========================================
POSTGRES_USER
POSTGRES_PASSWORD
POSTGRES_DB
POSTGRES_HOST
POSTGRES_PORT
POSTGRES_HOST_PORT
DATABASE_URL
POSTGRES_LOG_LEVEL

# ==========================================
# RabbitMQ Configuration
# ==========================================
RABBITMQ_DEFAULT_USER
RABBITMQ_DEFAULT_PASS
RABBITMQ_HOST
RABBITMQ_PORT
RABBITMQ_HOST_PORT
RABBITMQ_DATA_HOST_PORT
RABBITMQ_MGMT_HOST_PORT
RABBITMQ_URL
RABBITMQ_LOG_LEVEL

# ==========================================
# Redis Configuration
# ==========================================
REDIS_HOST
REDIS_PORT
REDIS_HOST_PORT
REDIS_URL
REDIS_LOG_LEVEL
REDIS_COMMAND

# ==========================================
# API Configuration
# ==========================================
API_HOST
API_PORT
API_HOST_PORT
JWT_SECRET
API_LOG_LEVEL
API_URL
API_BASE_URL

# ==========================================
# Frontend Configuration
# ==========================================
FRONTEND_HOST_PORT
FRONTEND_URL
NGINX_LOG_LEVEL

# ==========================================
# Environment
# ==========================================
ENVIRONMENT
TEST_ENVIRONMENT

# ==========================================
# Daemon Service Configuration
# ==========================================
NOTIFICATION_DAEMON_LOG_LEVEL
STATUS_TRANSITION_DAEMON_LOG_LEVEL
RETRY_DAEMON_LOG_LEVEL
RETRY_INTERVAL_SECONDS

# ==========================================
# OpenTelemetry / Grafana Cloud Configuration
# ==========================================
GRAFANA_CLOUD_API_KEY
GRAFANA_CLOUD_OTLP_INSTANCE_ID
GRAFANA_CLOUD_OTLP_ENDPOINT
GRAFANA_CLOUD_PROMETHEUS_INSTANCE_ID
GRAFANA_CLOUD_PROMETHEUS_ENDPOINT
GRAFANA_CLOUD_LOKI_INSTANCE_ID
GRAFANA_CLOUD_LOKI_ENDPOINT
ALLOY_OTLP_GRPC_PORT
ALLOY_OTLP_HTTP_PORT
ALLOY_HOST_PORT
ALLOY_LOG_LEVEL

# ==========================================
# Cloudflare Tunnel Configuration
# ==========================================
CLOUDFLARE_TUNNEL_TOKEN

# ==========================================
# Test-Specific Configuration (e2e only)
# ==========================================
DISCORD_TOKEN
DISCORD_ADMIN_BOT_TOKEN
DISCORD_ADMIN_BOT_CLIENT_ID
DISCORD_ADMIN_BOT_CLIENT_SECRET
DISCORD_ADMIN_BOT_INVITE_URL
DISCORD_GUILD_ID
DISCORD_CHANNEL_ID
DISCORD_USER_ID
```

### Environment-Specific Variable Inclusion

**env.example (Master Template):**
- Include ALL variables with placeholder values
- Comprehensive comments for every variable
- Mark optional/environment-specific variables clearly

**env.dev:**
- Include Docker config (COMPOSE_FILE, COMPOSE_PROFILES)
- Include all core service variables
- Include all port mappings for development
- Include Cloudflare tunnel config
- Set all secrets to placeholder values (remove actual credentials)

**env.prod:**
- Include Docker config (COMPOSE_FILE=compose.yaml)
- Include all core service variables
- EXCLUDE port mapping variables (not used)
- EXCLUDE HOST_WORKSPACE_FOLDER (not used)
- Include minimal comments (reference env.example)

**env.staging:**
- Same as prod, plus:
- Include CONTAINER_PREFIX for isolation
- Include external network configuration

**env.e2e:**
- Test-specific minimal set
- Include all test bot credentials
- Include port mappings with test-specific ports
- Include test infrastructure variables

**env.int:**
- Test-specific minimal set
- NO Discord bot variables (not used)
- Include port mappings with test-specific ports
- Include test infrastructure variables

### Variables to Add

**All deployment files need:**
- `JWT_SECRET` - Currently used in compose.yaml but missing from all env files
- `RETRY_DAEMON_LOG_LEVEL` - Used in compose.yaml but missing

**env.example needs:**
- `COMPOSE_FILE` - Controls compose file loading
- `COMPOSE_PROFILES` - Controls optional services
- `JWT_SECRET` - JWT signing secret
- `RETRY_DAEMON_LOG_LEVEL` - Retry daemon logging
- `CONTAINER_PREFIX` - Container naming prefix
- `RESTART_POLICY` - Restart behavior
- `HOST_WORKSPACE_FOLDER` - Development volume source

**env.dev needs:**
- Section reorganization (move Cloudflare to proper location)
- Remove duplicate API_HOST_PORT definitions
- Remove commented Discord URL
- **PRESERVE all actual credential values** (live working credentials)

**env.prod needs:**
- `JWT_SECRET` with placeholder
- `RETRY_DAEMON_LOG_LEVEL` with default
- `COMPOSE_FILE` specifying compose.yaml

**env.staging needs:**
- `JWT_SECRET` with placeholder
- `RETRY_DAEMON_LOG_LEVEL` with default
- `COMPOSE_PROFILES` (empty or not needed)

### Variables to Remove

**From env.example:**
- `API_SECRET_KEY` - Deprecated, replaced by JWT_SECRET
- `API_HOST` - Not used in compose files (hardcoded)
- `API_PORT` - Not used in compose files (hardcoded)

**From env.dev:**
- Duplicate `API_HOST_PORT` definition
- Commented Discord invite URL
- **NOTE**: Actual credential values MUST be preserved (live working credentials)

**From env.prod:**
- `API_HOST` - Not used in compose
- `API_PORT` - Not used in compose

**From env.staging:**
- `API_HOST` - Not used in compose
- `API_PORT` - Not used in compose

### Comment Standardization

**Required Comments (from env.example):**
- Every variable must have clear purpose description
- Include example values where helpful
- Mark optional variables clearly
- Note environment-specific usage
- Cross-reference related documentation

**Deployment File Comments:**
- Minimal inline comments
- Reference env.example for details
- Only document values that differ from standard

## Implementation Guidance

**Objectives:**
- Ensure all necessary variables are present in all env files
- Remove unused/deprecated variables
- Standardize variable ordering across all files
- Ensure comprehensive comments in env.example
- Ensure consistent comments in deployment files

**Key Tasks:**

1. **Update env.example:**
   - Add missing variables (COMPOSE_FILE, COMPOSE_PROFILES, JWT_SECRET, etc.)
   - Remove deprecated variables (API_SECRET_KEY, unused API_HOST/PORT)
   - Add comprehensive comments for all new variables
   - Reorganize to match standard ordering
   - Mark optional/environment-specific variables

2. **Update env.dev:**
   - Add missing variables
   - Remove duplicate definitions and actual credentials
   - Reorganize to match standard ordering
   - Move Cloudflare section to proper location
   - Clean up comments to match env.example

3. **Update env.prod:**
   - Add missing variables (JWT_SECRET, RETRY_DAEMON_LOG_LEVEL, COMPOSE_FILE)
   - Remove unused variables (API_HOST, API_PORT)
   - Add minimal comments referencing env.example
   - Reorganize to match standard ordering

4. **Update env.staging:**
   - Add missing variables (JWT_SECRET, RETRY_DAEMON_LOG_LEVEL, COMPOSE_PROFILES)
   - Remove unused variables (API_HOST, API_PORT)
   - Add minimal comments referencing env.example
   - Reorganize to match standard ordering

5. **Update env.e2e and env.int:**
   - Keep minimal test-specific focus
   - Ensure ordering matches standard where applicable
   - Add brief comments for test-specific variables

**Dependencies:**
- None - this is purely a configuration update

**Success Criteria:**
- All env files have consistent variable ordering
- No duplicate variables in any file
- No unused variables in any file
- All variables used in compose files are present in relevant env files
- env.example has comprehensive comments for every variable
- Deployment files have consistent minimal comments
- Files can be compared side-by-side with vimdiff for easy verification
